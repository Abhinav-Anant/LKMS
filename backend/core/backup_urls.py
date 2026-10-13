from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core import backup
from core.permissions import Can


class BackupFileSerializer(serializers.Serializer):
    name = serializers.CharField()
    size = serializers.IntegerField()
    taken_at = serializers.DateTimeField()


class BackupStatusSerializer(serializers.Serializer):
    directory = serializers.CharField()
    latest_at = serializers.DateTimeField(allow_null=True)
    healthy = serializers.BooleanField()
    max_age_hours = serializers.IntegerField()
    offsite_copy = serializers.BooleanField()
    retention = serializers.DictField(child=serializers.IntegerField())
    backups = BackupFileSerializer(many=True)


@extend_schema(responses=BackupStatusSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated, Can("backups.view")])
def backup_status(request):
    """Whether nightly backups are running. Backups are made and restored on the server, not through the app."""
    return Response(BackupStatusSerializer(backup.status()).data)


urlpatterns = [path("", backup_status, name="backup-status")]
