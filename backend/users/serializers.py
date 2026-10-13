import re

from django.contrib.auth import password_validation
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from core.permissions import CAPABILITIES, has_capability

from .models import User


class MeSerializer(serializers.ModelSerializer):
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "phone", "role", "must_change_password", "capabilities"]
        read_only_fields = ["id", "username", "role", "must_change_password", "capabilities"]

    def get_capabilities(self, user) -> list[str]:
        return sorted(c for c in CAPABILITIES if has_capability(user, c))


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = MeSerializer(self.user).data
        return data


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        password_validation.validate_password(value, self.context["request"].user)
        return value


def _mobile(value):
    from students.validators import normalise_mobile

    digits = normalise_mobile(value)
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise serializers.ValidationError("Enter a 10-digit mobile number.")
    return digits


class ParentCodeRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        return _mobile(value)


class ParentCodeVerifySerializer(ParentCodeRequestSerializer):
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "Enter the 6-digit code."})


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = MeSerializer()


class IssuedCodeSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()
    expires_at = serializers.DateTimeField()
    children = serializers.ListField(child=serializers.CharField())


STAFF_ROLES = [User.Role.ADMIN, User.Role.PRINCIPAL, User.Role.OFFICE, User.Role.ACCOUNTANT, User.Role.TEACHER]


class StaffUserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=[(r.value, r.label) for r in STAFF_ROLES])
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    full_name = serializers.SerializerMethodField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "full_name", "email", "phone", "role", "role_label",
            "is_active", "must_change_password", "last_login", "date_joined",
        ]
        read_only_fields = ["must_change_password", "last_login", "date_joined"]

    def get_full_name(self, obj) -> str:
        return obj.get_full_name() or obj.username

    def validate_username(self, value):
        if not re.fullmatch(r"[a-zA-Z0-9._-]{3,30}", value):
            raise serializers.ValidationError("Use 3 to 30 letters, digits, dots, dashes or underscores.")
        if value.lower().startswith("parent-"):
            raise serializers.ValidationError("Usernames starting with parent- are kept for parent accounts.")
        return value

    def validate_phone(self, value):
        return _mobile(value) if value else ""

    def validate(self, attrs):
        actor = self.context["request"].user
        target_role = attrs.get("role", getattr(self.instance, "role", None))
        # Only an administrator may create or change administrator accounts.
        touches_admin = target_role == User.Role.ADMIN or (self.instance and self.instance.role == User.Role.ADMIN)
        if touches_admin and not (actor.is_superuser or actor.role == User.Role.ADMIN):
            raise serializers.ValidationError("Only an administrator can manage administrator accounts.")
        if self.instance and self.instance.pk == actor.pk:
            if "role" in attrs and attrs["role"] != actor.role:
                raise serializers.ValidationError({"role": "You cannot change your own role."})
            if attrs.get("is_active") is False:
                raise serializers.ValidationError({"is_active": "You cannot deactivate your own account."})
        return attrs


class TemporaryPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()
    temporary_password = serializers.CharField()


class PermissionMatrixSerializer(serializers.Serializer):
    roles = serializers.ListField(child=serializers.DictField())
    capabilities = serializers.ListField(child=serializers.DictField())
