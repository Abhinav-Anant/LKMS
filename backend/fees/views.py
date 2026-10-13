from django.db.models import Count, Sum
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from core import audit
from core.errors import as_api_errors
from core.permissions import Can, ReadOrManage

from . import cashfree, online, services
from .models import Concession, FeeAmount, FeeHead, Installment, Invoice, OnlineOrder, Payment, PaymentIssue
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
    InvoiceListSerializer,
    OnlineOrderSerializer,
    PaymentIssueSerializer,
    PaymentSerializer,
    PublicInvoiceSerializer,
    ReasonSerializer,
    RecordPaymentSerializer,
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
            qs = qs.prefetch_related("lines__fee_head", "payments__received_by", "online_orders")
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
        """A link parents can open to pay this invoice online."""
        invoice = self.get_object()
        audit.record(request, "fees.pay_link_created", invoice)
        return Response({"url": online.pay_link(invoice)})

    @extend_schema(request=None, responses=OnlineOrderSerializer)
    @action(detail=True, methods=["post"], url_path=r"orders/(?P<order_id>[\w-]+)/check", permission_classes=[Can("fees.view")])
    def check_order(self, request, pk=None, order_id=None):
        """Ask Cashfree for the latest state of an online payment."""
        order = OnlineOrder.objects.filter(invoice_id=pk, order_id=order_id).first()
        if order is None:
            raise NotFound
        try:
            order = online.sync_order(order)
        except cashfree.CashfreeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(OnlineOrderSerializer(order).data)


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


class PaymentIssueViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Online payments that need a person to look at them."""

    permission_classes = [ReadOrManage]
    view_capability = "fees.view"
    manage_capability = "fees.approve"
    serializer_class = PaymentIssueSerializer
    queryset = PaymentIssue.objects.select_related("order")
    filterset_fields = ["resolved", "kind"]
    http_method_names = ["get", "patch", "head", "options"]

    def perform_update(self, serializer):
        issue = serializer.save()
        audit.record(self.request, "fees.payment_issue_updated", issue, resolved=issue.resolved)


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
        invoice = online.invoice_from_token(token)
        if invoice is None:
            raise NotFound("This payment link is not valid or has expired. Please ask the school for a new one.")
        return invoice


class PublicInvoiceView(_PublicPay):
    serializer_class = PublicInvoiceSerializer

    @extend_schema(responses=inline_serializer("PublicPayPage", {
        "invoice": PublicInvoiceSerializer(), "online_payments_enabled": serializers.BooleanField(),
        "school_name": serializers.CharField(),
    }))
    def get(self, request, token):
        from core.models import SchoolProfile

        invoice = self.invoice(token)
        return Response({
            "invoice": PublicInvoiceSerializer(invoice).data,
            "online_payments_enabled": cashfree.is_configured(),
            "school_name": SchoolProfile.get().name,
        })


class PublicStartPaymentView(_PublicPay):
    @extend_schema(request=None, responses=inline_serializer("StartPayment", {
        "order_id": serializers.CharField(), "payment_session_id": serializers.CharField(),
        "mode": serializers.CharField(), "amount": serializers.DecimalField(max_digits=10, decimal_places=2),
    }))
    def post(self, request, token):
        from django.conf import settings

        invoice = self.invoice(token)
        try:
            with as_api_errors():
                order = online.start_payment(request, invoice, token)
        except cashfree.CashfreeError as exc:
            return Response({"detail": f"Online payment could not be started. {exc}"}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({
            "order_id": order.order_id, "payment_session_id": order.payment_session_id,
            "mode": settings.CASHFREE_ENV, "amount": order.amount,
        })


class PublicOrderStatusView(_PublicPay):
    @extend_schema(request=None, responses=inline_serializer("PublicOrderStatus", {
        "status": serializers.CharField(), "receipt_number": serializers.CharField(allow_null=True),
        "invoice": PublicInvoiceSerializer(),
    }))
    def get(self, request, token, order_id):
        """Called when Cashfree sends the parent back. Checks with Cashfree; never trusts the redirect."""
        invoice = self.invoice(token)
        order = OnlineOrder.objects.filter(invoice=invoice, order_id=order_id).first()
        if order is None:
            raise NotFound
        try:
            order = online.sync_order(order)
        except cashfree.CashfreeError:
            pass  # show the stored state; the webhook or reconciliation will catch up
        invoice.refresh_from_db()
        payment = getattr(order, "payment", None) if order.status == OnlineOrder.Status.PAID else None
        return Response({
            "status": order.status,
            "receipt_number": payment.receipt_number if payment else None,
            "invoice": PublicInvoiceSerializer(invoice).data,
        })


class PublicReceiptView(_PublicPay):
    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    def get(self, request, token, receipt_number):
        invoice = self.invoice(token)
        payment = invoice.payments.filter(receipt_number=receipt_number).first()
        if payment is None:
            raise NotFound
        return pdf_response(payment)


class CashfreeWebhookView(APIView):
    """Cashfree calls this after each payment attempt. Configure it in the Cashfree dashboard."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT})
    def post(self, request):
        code, message = online.handle_webhook(
            request.body,
            request.headers.get("x-webhook-timestamp", ""),
            request.headers.get("x-webhook-signature", ""),
        )
        return Response({"detail": message}, status=code)

