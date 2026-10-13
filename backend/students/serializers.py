from rest_framework import serializers

from academics.serializers import EnrollmentSerializer
from core.permissions import has_capability

from .models import Guardian, Student, StudentGuardian


def mask_aadhaar(value):
    return f"XXXX-XXXX-{value[-4:]}" if value else ""


class GuardianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = ["id", "full_name", "phone", "alternate_phone", "email", "occupation", "qualification", "annual_income", "address"]


class StudentGuardianSerializer(serializers.ModelSerializer):
    guardian = GuardianSerializer(read_only=True)

    class Meta:
        model = StudentGuardian
        fields = ["id", "guardian", "relationship", "relationship_detail", "is_primary_contact"]


class StudentListSerializer(serializers.ModelSerializer):
    class_name = serializers.SerializerMethodField()
    section_name = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ["id", "admission_number", "first_name", "last_name", "date_of_birth", "gender", "status", "class_name", "section_name"]

    def _enrollment(self, obj):
        enrollments = getattr(obj, "current_enrollments", None)
        if enrollments is not None:
            return enrollments[0] if enrollments else None
        return obj.current_enrollment()

    def get_class_name(self, obj) -> str | None:
        e = self._enrollment(obj)
        return e.section.school_class.name if e else None

    def get_section_name(self, obj) -> str | None:
        e = self._enrollment(obj)
        return e.section.name if e else None


class StudentDetailSerializer(serializers.ModelSerializer):
    guardians = StudentGuardianSerializer(source="guardian_links", many=True, read_only=True)
    enrollments = EnrollmentSerializer(many=True, read_only=True)
    admitted_in_class_name = serializers.CharField(source="admitted_in_class.name", read_only=True)
    has_photo = serializers.SerializerMethodField()

    class Meta:
        model = Student
        exclude = ["photo"]
        read_only_fields = ["admission_number", "application", "admitted_in_class", "admission_date", "created_at", "updated_at"]

    def get_has_photo(self, obj) -> bool:
        return bool(obj.photo)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if not (request and has_capability(request.user, "students.view_sensitive")):
            data["aadhaar_number"] = mask_aadhaar(instance.aadhaar_number)
        return data
