from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework import generics, mixins, viewsets
from rest_framework.decorators import api_view, permission_classes
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


class SchoolProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = SchoolProfileSerializer
    permission_classes = [Can("school.manage")]

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
