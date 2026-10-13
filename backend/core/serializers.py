from rest_framework import serializers

from .models import AuditLog, SchoolProfile


class PublicSchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolProfile
        fields = ["name", "address", "district", "state", "pincode", "phone", "email", "website", "board"]


class SchoolProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolProfile
        exclude = ["id"]
        read_only_fields = ["updated_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.StringRelatedField()

    class Meta:
        model = AuditLog
        fields = "__all__"
