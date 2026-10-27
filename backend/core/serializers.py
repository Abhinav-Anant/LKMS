import io

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from rest_framework import serializers

from .models import AuditLog, GalleryPhoto, SchoolProfile
from .storage import validate_upload

# Phone photos are often bigger than documents; they are made smaller on upload. Matches nginx's 10 MB body limit.
GALLERY_MAX_MB = 9


class PublicSchoolSerializer(serializers.ModelSerializer):
    board_label = serializers.CharField(read_only=True)
    has_logo = serializers.SerializerMethodField()

    class Meta:
        model = SchoolProfile
        fields = ["name", "short_code", "address", "district", "state", "pincode", "phone", "email", "website",
                  "board", "board_label", "brand_colour", "has_logo", "map_latitude", "map_longitude",
                  "facebook_url", "instagram_url", "youtube_url", "x_url"]

    def get_has_logo(self, obj) -> bool:
        return bool(obj.logo)


class GalleryPhotoSerializer(serializers.ModelSerializer):
    """Photos are re-saved as JPEG, at most 1600 px wide, without the camera's details (such as GPS)."""

    image = serializers.FileField(write_only=True)

    class Meta:
        model = GalleryPhoto
        fields = ["id", "image", "caption", "uploaded_at"]

    def validate_image(self, value):
        from PIL import Image, ImageOps

        try:
            validate_upload(value, allowed=("jpg", "png"), max_mb=GALLERY_MAX_MB)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error
        with Image.open(value) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((1600, 1600))
            out = io.BytesIO()
            img.save(out, "JPEG", quality=85)
        return ContentFile(out.getvalue(), name="photo.jpg")


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
