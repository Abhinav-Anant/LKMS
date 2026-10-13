from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from core import audit
from core.audit import client_ip
from core.errors import as_api_errors
from core.models import SchoolProfile
from core.permissions import Can, ReadOrManage
from core.storage import private_file_response, validate_upload

from . import services, upi
from .models import Concession, FeeAmount, FeeHead, Installment, Invoice, Payment, UpiSubmission
from .receipts import receipt_pdf
from .serializers import (
    ConcessionSerializer,
    DecisionSerializer,
    FeeAmountBulkSerializer,
    FeeAmountSerializer,
    FeeHeadSerializer,
    GenerateInvoicesSerializer,
    InstallmentSerializer,
    InvoiceDetailSerializer,
    ApproveUpiSerializer,
    InvoiceListSerializer,
    PaymentSerializer,
    PublicInvoiceSerializer,
    PublicSubmissionSerializer,
    ReasonSerializer,
    RecordPaymentSerializer,
    UpiSubmissionSerializer,
    UpiSubmitSerializer,
)


def pdf_response(payment):
    response = HttpResponse(receipt_pdf(payment), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="receipt-{payment.receipt_number}.pdf"'
    response["Cache-Control"] = "private, no-store"
    return response


class _Setup(viewsets.ModelViewSet):
    permission_classes = [ReadOrManage]
    view_capability = "fees.view"
    manage_capability = "fees.manage"
    pagination_class = None


class FeeHeadViewSet(_Setup):
    queryset = FeeHead.objects.all()
    serializer_class = FeeHeadSerializer


class InstallmentViewSet(_Setup):
    queryset = Installment.objects.select_related("session")
    serializer_class = InstallmentSerializer
    filterset_fields = ["session"]


class FeeAmountViewSet(_Setup):
    queryset = FeeAmount.objects.select_related("fee_head", "school_class")
    serializer_class = FeeAmountSerializer
    filterset_fields = ["installment", "school_class"]

    @extend_schema(request=FeeAmountBulkSerializer, responses=FeeAmountSerializer(many=True))
    @action(detail=False, methods=["post"])
    def bulk(self, request):
        """Save the fee structure grid for one installment."""
        serializer = FeeAmountBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        installment = serializer.validated_data["installment"]
        if installment.invoices.exclude(status=Invoice.Status.CANCELLED).exists():
            raise PermissionDenied("Invoices already exist for this installment. Cancel them before changing its fees.")
        for row in serializer.validated_data["amounts"]:
            key = {"installment": installment, "school_class": row["school_class"], "fee_head": row["fee_head"]}
            if row["amount"] > 0:
                FeeAmount.objects.update_or_create(**key, defaults={"amount": row["amount"]})
            else:
                FeeAmount.objects.filter(**key).delete()
        audit.record(request, "fees.structure_saved", installment, rows=len(serializer.validated_data["amounts"]))
        return Response(FeeAmountSerializer(self.get_queryset().filter(installment=installment), many=True).data)


class InvoiceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [Can("fees.view")]
    filterset_fields = {
        "status": ["exact", "in"],
        "session": ["exact"],
        "installment": ["exact"],
        "school_class": ["exact"],
        "student": ["exact"],
        "due_date": ["lte", "gte"],
    }
    search_fields = ["number", "student__first_name", "student__last_name", "student__admission_number"]
    ordering_fields = ["due_date", "number", "student__first_name"]

    def get_queryset(self):
        qs = Invoice.objects.select_related("student", "school_class", "installment", "session")
        if self.action == "retrieve":
            qs = qs.prefetch_related("lines__fee_head", "payments__received_by", "upi_submissions__reviewed_by", "upi_submissions__payment")
        if self.request.query_params.get("overdue") == "1":
            qs = qs.filter(due_date__lt=timezone.localdate(), status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTLY_PAID])
        return qs

    def get_serializer_class(self):
        return InvoiceDetailSerializer if self.action == "retrieve" else InvoiceListSerializer

    @extend_schema(request=GenerateInvoicesSerializer, responses=inline_serializer("GenerateResult", {
        "created": serializers.IntegerField(), "skipped_existing": serializers.IntegerField(),
        "skipped_no_fees": serializers.IntegerField(),
    }))
    @action(detail=False, methods=["post"], permission_classes=[Can("fees.manage")])
    def generate(self, request):
        serializer = GenerateInvoicesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.generate_invoices(
            request, serializer.validated_data["installment"], serializer.validated_data.get("classes") or None
        )
        return Response(result, status=status.HTTP_201_CREATED)

    @extend_schema(request=RecordPaymentSerializer, responses=PaymentSerializer)
    @action(detail=True, methods=["post"], permission_classes=[Can("fees.collect")])
    def pay(self, request, pk=None):
        """Record a payment taken at the school office (cash, cheque, transfer, UPI to the school)."""
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with as_api_errors():
            payment = services.record_payment(request, self.get_object(), **serializer.validated_data)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=ReasonSerializer, responses=InvoiceDetailSerializer)
    @action(detail=True, methods=["post"], permission_classes=[Can("fees.manage")])
    def cancel(self, request, pk=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with as_api_errors():
            services.cancel_invoice(request, self.get_object(), serializer.validated_data["reason"])
        return Response(InvoiceDetailSerializer(self.get_queryset().get(pk=pk)).data)

    @extend_schema(request=None, responses=inline_serializer("PayLink", {"url": serializers.URLField()}))
    @action(detail=True, methods=["post"], url_path="pay-link", permission_classes=[Can("fees.view")])
    def pay_link(self, request, pk=None):
        """A link parents can open to pay this invoice by UPI and send their receipt."""
        invoice = self.get_object()
        audit.record(request, "fees.pay_link_created", invoice)
        return Response({"url": upi.pay_link(invoice)})


class PaymentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [Can("fees.view")]
    serializer_class = PaymentSerializer
    filterset_fields = {"paid_on": ["exact", "gte", "lte"], "mode": ["exact"], "status": ["exact"], "invoice": ["exact"]}
    search_fields = ["receipt_number", "reference", "invoice__number", "invoice__student__first_name", "invoice__student__admission_number"]

    def get_queryset(self):
        return Payment.objects.select_related("invoice__student", "received_by")

    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"])
    def receipt(self, request, pk=None):
        payment = self.get_object()
        return pdf_response(payment)

    @extend_schema(request=ReasonSerializer, responses=PaymentSerializer)
    @action(detail=True, methods=["post"], permission_classes=[Can("fees.approve")])
    def reverse(self, request, pk=None):
        """Undo a payment entered by mistake or a bounced cheque."""
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with as_api_errors():
            payment = services.reverse_payment(request, self.get_object(), serializer.validated_data["reason"])
        return Response(PaymentSerializer(payment).data)


class ConcessionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ConcessionSerializer
    filterset_fields = ["status", "session", "student"]
    search_fields = ["student__first_name", "student__last_name", "student__admission_number", "reason"]

    def get_permissions(self):
        if self.action == "create":
            return [Can("fees.request_concession")()]
        if self.action in ("decide", "cancel"):
            return [Can("fees.approve")()]
        return [Can("fees.view")()]

    def get_queryset(self):
        return Concession.objects.select_related("student", "session", "fee_head", "requested_by", "decided_by")

    def perform_create(self, serializer):
        data = dict(serializer.validated_data)
        serializer.instance = services.request_concession(self.request, **data)

    @extend_schema(request=DecisionSerializer, responses=ConcessionSerializer)
    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with as_api_errors():
            concession = services.decide_concession(
                request, self.get_object(), serializer.validated_data["approve"], serializer.validated_data["note"]
            )
        return Response(ConcessionSerializer(concession).data)

    @extend_schema(request=ReasonSerializer, responses=ConcessionSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        concession = self.get_object()
        with as_api_errors():
            services.cancel_concession(request, concession, serializer.validated_data["reason"])
        concession.refresh_from_db()
        return Response(ConcessionSerializer(concession).data)


class UpiSubmissionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """UPI payments parents say they made. Staff check each against the bank statement."""

    serializer_class = UpiSubmissionSerializer
    filterset_fields = ["status", "invoice"]
    search_fields = ["utr", "invoice__number", "invoice__student__first_name", "invoice__student__admission_number"]

    def get_permissions(self):
        if self.action in ("approve", "reject"):
            return [Can("fees.collect")()]
        return [Can("fees.view")()]

    def get_queryset(self):
        return UpiSubmission.objects.select_related(
            "invoice__student", "invoice__school_class", "reviewed_by", "payment"
        ).order_by("status", "submitted_at")

    @extend_schema(responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"])
    def screenshot(self, request, pk=None):
        submission = self.get_object()
        audit.record(request, "fees.upi_screenshot_viewed", submission)
        return private_file_response(submission.screenshot, submission.screenshot_type, f"upi-{submission.utr}")

    @extend_schema(request=ApproveUpiSerializer, responses=UpiSubmissionSerializer)
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """The money is in the school's bank account: record it and issue the receipt."""
        serializer = ApproveUpiSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with as_api_errors():
            submission = upi.approve(request, self.get_object(), serializer.validated_data.get("amount"))
        return Response(UpiSubmissionSerializer(self.get_queryset().get(pk=submission.pk)).data)

    @extend_schema(request=ReasonSerializer, responses=UpiSubmissionSerializer)
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with as_api_errors():
            submission = upi.reject(request, self.get_object(), serializer.validated_data["reason"])
        return Response(UpiSubmissionSerializer(self.get_queryset().get(pk=submission.pk)).data)


# ----- reports -----

class DailyCollectionView(APIView):
    permission_classes = [Can("fees.view")]

    @extend_schema(
        parameters=[OpenApiParameter("date", OpenApiTypes.DATE, required=False)],
        responses=inline_serializer("DailyCollection", {
            "date": serializers.DateField(),
            "total": serializers.DecimalField(max_digits=12, decimal_places=2),
            "by_mode": serializers.ListField(child=serializers.DictField()),
            "payments": PaymentSerializer(many=True),
        }),
    )
    def get(self, request):
        day = parse_date(request.query_params.get("date") or "") or timezone.localdate()
        payments = Payment.objects.filter(paid_on=day, status=Payment.Status.COMPLETED).select_related("invoice__student", "received_by")
        by_mode = [
            {"mode": row["mode"], "label": Payment.Mode(row["mode"]).label, "count": row["count"], "total": row["total"]}
            for row in payments.values("mode").annotate(count=Count("id"), total=Sum("amount")).order_by("mode")
        ]
        return Response({
            "date": day,
            "total": payments.aggregate(total=Sum("amount"))["total"] or 0,
            "by_mode": by_mode,
            "payments": PaymentSerializer(payments.order_by("created_at"), many=True).data,
        })


class DefaultersView(APIView):
    """Students with fees past their due date."""

    permission_classes = [Can("fees.view")]

    @extend_schema(
        parameters=[
            OpenApiParameter("session", OpenApiTypes.INT, required=False),
            OpenApiParameter("school_class", OpenApiTypes.INT, required=False),
        ],
        responses=InvoiceListSerializer(many=True),
    )
    def get(self, request):
        qs = Invoice.objects.filter(
            due_date__lt=timezone.localdate(), status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTLY_PAID]
        ).select_related("student", "school_class", "installment")
        for param in ("session", "school_class"):
            value = request.query_params.get(param)
            if value and value.isdigit():
                qs = qs.filter(**{param: value})
        qs = qs.order_by("school_class__order", "student__first_name", "due_date")
        return Response(InvoiceListSerializer(qs, many=True).data)


# ----- parents (pay link, no login) -----

class _PublicPay(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_payment"

    def invoice(self, token):
        invoice = upi.invoice_from_token(token)
        if invoice is None:
            raise NotFound("This payment link is not valid or has expired. Please ask the school for a new one.")
        return invoice


def _pay_page(invoice):
    receipts = invoice.payments.filter(status=Payment.Status.COMPLETED).order_by("paid_on")
    return {
        "invoice": PublicInvoiceSerializer(invoice).data,
        "school_name": SchoolProfile.get().name,
        **upi.upi_details(),
        "pending_amount": upi.pending_amount(invoice),
        "submissions": PublicSubmissionSerializer(invoice.upi_submissions.select_related("payment"), many=True).data,
        "receipts": [{"receipt_number": p.receipt_number, "amount": p.amount, "paid_on": p.paid_on} for p in receipts],
    }


PAY_PAGE = inline_serializer("PublicPayPage", {
    "invoice": PublicInvoiceSerializer(),
    "school_name": serializers.CharField(),
    "upi_id": serializers.CharField(),
    "payee_name": serializers.CharField(),
    "pending_amount": serializers.DecimalField(max_digits=10, decimal_places=2),
    "submissions": PublicSubmissionSerializer(many=True),
    "receipts": serializers.ListField(child=serializers.DictField()),
})


class PublicInvoiceView(_PublicPay):
    @extend_schema(responses=PAY_PAGE)
    def get(self, request, token):
        return Response(_pay_page(self.invoice(token)))


class PublicUpiSubmitView(_PublicPay):
    """The parent paid to the school's UPI QR code and sends the transaction ID and receipt screenshot."""

    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=UpiSubmitSerializer, responses={201: PAY_PAGE})
    def post(self, request, token):
        invoice = self.invoice(token)
        serializer = UpiSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with as_api_errors():
            try:
                _, mime, _ = validate_upload(data["screenshot"], ("jpg", "png", "pdf"))
            except DjangoValidationError as exc:
                raise DjangoValidationError({"screenshot": exc.messages}) from exc
            upi.submit(
                request, invoice, amount=data["amount"], utr=data["utr"], paid_on=data["paid_on"],
                payer_name=data["payer_name"], screenshot=data["screenshot"], screenshot_type=mime, ip=client_ip(request),
            )
        invoice.refresh_from_db()
        return Response(_pay_page(invoice), status=status.HTTP_201_CREATED)


class PublicReceiptView(_PublicPay):
    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    def get(self, request, token, receipt_number):
        invoice = self.invoice(token)
        payment = invoice.payments.filter(receipt_number=receipt_number).first()
        if payment is None:
            raise NotFound
        return pdf_response(payment)
