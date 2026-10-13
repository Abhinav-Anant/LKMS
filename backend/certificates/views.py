from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core import audit
from core.notify import notify
from core.permissions import ReadOrManage, has_capability
from exams.views import PDF, pdf_download

from . import services
from .models import TransferCertificate
from .pdf import tc_pdf
from .serializers import CancelSerializer, IssueSerializer, TransferCertificateSerializer


class TransferCertificateViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                                 mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Transfer certificates. The office records the request; the principal issues it."""

    serializer_class = TransferCertificateSerializer
    permission_classes = [IsAuthenticated, ReadOrManage]
    view_capability = "tc.view"
    manage_capability = "tc.request"
    filterset_fields = ["status", "student"]
    queryset = TransferCertificate.objects.none()

    def get_queryset(self):
        qs = TransferCertificate.objects.select_related("student", "issued_by")
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(student__first_name__icontains=search) | Q(student__last_name__icontains=search)
                           | Q(student__admission_number__icontains=search) | Q(number__icontains=search))
        return qs

    def perform_create(self, serializer):
        tc = serializer.save(requested_by=self.request.user)
        audit.record(self.request, "tc.requested", tc)

    def perform_update(self, serializer):
        audit.record(self.request, "tc.updated", serializer.save())

    def _require_issue(self):
        if not has_capability(self.request.user, "tc.issue"):
            raise PermissionDenied("Only the principal can issue or cancel a TC.")

    @extend_schema(request=IssueSerializer, responses=TransferCertificateSerializer)
    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        self._require_issue()
        data = IssueSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            tc = services.issue(self.get_object(), request.user, data.validated_data["dues_waived_reason"])
        except services.DuesOutstanding as e:
            raise ValidationError({"dues_waived_reason": f"{e} Collect them first, or give a reason to issue anyway.",
                                   "fees_due": str(e.amount)})
        except ValueError as e:
            raise ValidationError(str(e))
        audit.record(request, "tc.issued", tc, number=tc.number, fees_due=str(tc.fees_due),
                     dues_waived_reason=tc.dues_waived_reason)
        notify("tc.issued", tc=tc)
        return Response(self.get_serializer(tc).data)

    @extend_schema(request=CancelSerializer, responses=TransferCertificateSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        tc = self.get_object()
        if tc.status == TransferCertificate.Status.ISSUED:
            self._require_issue()
        data = CancelSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            tc = services.cancel(tc, request.user, data.validated_data["reason"])
        except ValueError as e:
            raise ValidationError(str(e))
        audit.record(request, "tc.cancelled", tc, reason=tc.cancel_reason)
        return Response(self.get_serializer(tc).data)

    @extend_schema(responses=PDF)
    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        tc = self.get_object()
        if not tc.number:
            raise ValidationError("The TC has not been issued yet.")
        audit.record(request, "tc.printed", tc)
        return pdf_download(tc_pdf(tc), f"{tc.number.replace('/', '-')}.pdf")
