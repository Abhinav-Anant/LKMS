import io
import mimetypes
from urllib.parse import quote, urlencode

import segno
from django.db import connection
from django.http import FileResponse, Http404, HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, mixins, viewsets
from rest_framework import serializers as drf_serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import audit
from .models import AuditLog, SchoolProfile
from .permissions import Can
from .serializers import AuditLogSerializer, PublicSchoolSerializer, SchoolProfileSerializer


@extend_schema(responses=inline_serializer("Health", {"status": drf_serializers.CharField()}))
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return Response({"status": "ok"})


@extend_schema(responses=PublicSchoolSerializer)
@api_view(["GET"])
@permission_classes([AllowAny])
def public_school(request):
    return Response(PublicSchoolSerializer(SchoolProfile.get()).data)


def _picture_response(field_file):
    response = FileResponse(field_file.open("rb"), content_type=mimetypes.guess_type(field_file.name)[0])
    response["Cache-Control"] = "public, max-age=300"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@extend_schema(responses={(200, "image/png"): OpenApiTypes.BINARY})
@api_view(["GET"])
@permission_classes([AllowAny])
def school_logo(request):
    school = SchoolProfile.get()
    if not school.logo:
        raise Http404("No logo")
    return _picture_response(school.logo)


@extend_schema(responses={(200, "image/svg+xml"): OpenApiTypes.BINARY})
@api_view(["GET"])
@permission_classes([AllowAny])
def school_upi_qr(request):
    """The school's UPI QR code: the picture it uploaded, or one made from its UPI ID."""
    school = SchoolProfile.get()
    if school.upi_qr:
        return _picture_response(school.upi_qr)
    if not school.payment_upi_id:
        raise Http404("No UPI ID")
    link = "upi://pay?" + urlencode({"pa": school.payment_upi_id, "pn": school.payment_upi_name, "cu": "INR"},
                                    quote_via=quote)
    out = io.BytesIO()
    segno.make(link, error="m").save(out, kind="svg", scale=8, border=2, xmldecl=False)
    response = HttpResponse(out.getvalue(), content_type="image/svg+xml")
    response["Cache-Control"] = "public, max-age=300"
    return response


class SchoolProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = SchoolProfileSerializer
    permission_classes = [Can("school.manage")]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        return SchoolProfile.get()

    def perform_update(self, serializer):
        before = SchoolProfileSerializer(serializer.instance).data
        obj = serializer.save()
        after = SchoolProfileSerializer(obj).data
        changed = {k: [before[k], after[k]] for k in after if before.get(k) != after[k] and k != "updated_at"}
        audit.record(self.request, "school.updated", obj, changed=changed)


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AuditLog.objects.select_related("actor")
    serializer_class = AuditLogSerializer
    permission_classes = [Can("audit.view")]
    filterset_fields = ["action", "object_type", "object_id", "actor"]
