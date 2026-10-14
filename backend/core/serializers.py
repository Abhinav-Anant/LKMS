from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import AuditLog, SchoolProfile
from .storage import validate_upload


class PublicSchoolSerializer(serializers.ModelSerializer):
    board_label = serializers.CharField(read_only=True)
    has_logo = serializers.SerializerMethodField()

    class Meta:
        model = SchoolProfile
        fields = ["name", "short_code", "address", "district", "state", "pincode", "phone", "email", "website",
                  "board", "board_label", "brand_colour", "has_logo"]

    def get_has_logo(self, obj) -> bool:
        return bool(obj.logo)


class SchoolProfileSerializer(serializers.ModelSerializer):
    """The school's settings. Pictures are sent as files; `remove_logo` / `remove_upi_qr` clear them."""

    logo = serializers.FileField(write_only=True, required=False)
    upi_qr = serializers.FileField(write_only=True, required=False)
    remove_logo = serializers.BooleanField(write_only=True, required=False)
    remove_upi_qr = serializers.BooleanField(write_only=True, required=False)
    has_logo = serializers.SerializerMethodField()
    has_upi_qr = serializers.SerializerMethodField()
    board_label = serializers.CharField(read_only=True)

    class Meta:
        model = SchoolProfile
        exclude = ["id"]
        read_only_fields = ["updated_at"]

    def get_has_logo(self, obj) -> bool:
        return bool(obj.logo)

    def get_has_upi_qr(self, obj) -> bool:
        return bool(obj.upi_qr)

    def _picture(self, value):
        try:
            validate_upload(value, allowed=("jpg", "png"))
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error
        return value

    def validate_logo(self, value):
        return self._picture(value)

    def validate_upi_qr(self, value):
        return self._picture(value)

    def update(self, instance, validated_data):
        for field in ("logo", "upi_qr"):
            if validated_data.pop(f"remove_{field}", False) and getattr(instance, field):
                getattr(instance, field).delete(save=False)
            if field in validated_data and getattr(instance, field):
                getattr(instance, field).delete(save=False)
        return super().update(instance, validated_data)


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.StringRelatedField()

    class Meta:
        model = AuditLog
        fields = "__all__"
