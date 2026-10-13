from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core import audit
from core.permissions import Can, ReadOrManage

from . import outbox, whatsapp
from .models import OptOut, OutgoingMessage
from .serializers import OptOutSerializer, OutgoingMessageSerializer, QrSerializer, WhatsAppStatusSerializer


@extend_schema(responses=WhatsAppStatusSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated, Can("messaging.view")])
def status_view(request):
    """Is the school's WhatsApp number connected, and how is the queue doing."""
    state, phone, error, reachable = "off", None, "", False
    if settings.WHATSAPP_ENABLED:
        try:
            info = whatsapp.status()
            state, phone, reachable = info["state"], info["phone"], True
        except whatsapp.WhatsAppError as err:
            state, error = "unreachable", str(err)
    start, end = settings.WHATSAPP_QUIET_HOURS
    return Response(WhatsAppStatusSerializer({
        "enabled": settings.WHATSAPP_ENABLED, "reachable": reachable, "state": state, "phone": phone, "error": error,
        **outbox.summary(), "quiet_hours": f"{start}:00 to {end}:00" if start != end else "", "rate_per_minute": settings.WHATSAPP_RATE_PER_MINUTE,
    }).data)


@extend_schema(responses=QrSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated, Can("messaging.manage")])
def qr_view(request):
    """QR code to link the school's phone (WhatsApp > Linked devices)."""
    if not settings.WHATSAPP_ENABLED:
        raise ValidationError("WhatsApp is switched off (WHATSAPP_ENABLED).")
    try:
        return Response({"qr": whatsapp.qr_code()})
    except whatsapp.WhatsAppError as err:
        raise ValidationError(str(err)) from err


@extend_schema(request=None, responses={204: None})
@api_view(["POST"])
@permission_classes([IsAuthenticated, Can("messaging.manage")])
def reconnect_view(request):
    try:
        whatsapp.reconnect()
    except whatsapp.WhatsAppError as err:
        raise ValidationError(str(err)) from err
    return Response(status=status.HTTP_204_NO_CONTENT)


class OutgoingMessageViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """The send log."""

    serializer_class = OutgoingMessageSerializer
    permission_classes = [IsAuthenticated, Can("messaging.view")]
    filterset_fields = ["status", "event", "kind"]
    search_fields = ["phone", "student__first_name", "student__last_name"]
    queryset = OutgoingMessage.objects.select_related("student")

    @extend_schema(request=None, responses=OutgoingMessageSerializer)
    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        row = self.get_object()
        if row.status != OutgoingMessage.Status.FAILED or row.kind == OutgoingMessage.Kind.LOGIN:
            raise ValidationError("Only failed alerts can be sent again.")
        outbox.retry(row)
        row.refresh_from_db()
        return Response(OutgoingMessageSerializer(row).data)


class OptOutViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Numbers that do not get WhatsApp alerts."""

    serializer_class = OptOutSerializer
    permission_classes = [IsAuthenticated, ReadOrManage]
    view_capability = "messaging.view"
    manage_capability = "messaging.view"
    queryset = OptOut.objects.select_related("created_by")
    search_fields = ["phone", "note"]
    pagination_class = None

    def perform_create(self, serializer):
        opt_out = serializer.save(created_by=self.request.user)
        audit.record(self.request, "whatsapp.opted_out", opt_out)

    def perform_destroy(self, instance):
        audit.record(self.request, "whatsapp.opted_in", instance)
        instance.delete()
