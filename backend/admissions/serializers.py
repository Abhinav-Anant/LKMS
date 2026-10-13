from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from academics.models import AcademicSession, SchoolClass, Section
from students.serializers import mask_aadhaar
from students.validators import normalise_mobile

from .models import AdmissionApplication, ApplicationDocument, ApplicationStatusChange, DocumentType

PHONE_FIELDS = ["father_phone", "mother_phone", "guardian_phone"]
WORKFLOW_FIELDS = [
    "application_number", "access_token_hash", "status", "status_message", "internal_notes", "reviewed_by",
    "submitted_at", "updated_at", "decided_at", "consent_given_at",
]


class DocumentTypeSerializer(serializers.ModelSerializer):
    allowed_formats = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = DocumentType
        fields = ["id", "code", "name", "description", "is_required", "allowed_formats"]


class ApplicationFormSerializer(serializers.ModelSerializer):
    """The fields a parent fills in. Also used by staff to correct an open application."""

    session = serializers.PrimaryKeyRelatedField(queryset=AcademicSession.objects.all())
    class_applied = serializers.PrimaryKeyRelatedField(queryset=SchoolClass.objects.all())

    class Meta:
        model = AdmissionApplication
        exclude = ["id"] + WORKFLOW_FIELDS

    def to_internal_value(self, data):
        data = data.copy()
        for field in PHONE_FIELDS:
            if data.get(field):
                data[field] = normalise_mobile(data[field])
        return super().to_internal_value(data)

    def validate(self, attrs):
        if not any(attrs.get(f"{p}_name", getattr(self.instance, f"{p}_name", "")) for p in ("father", "mother", "guardian")):
            raise serializers.ValidationError("Give at least one parent or guardian.")
        return attrs


class DocumentSerializer(serializers.ModelSerializer):
    document_type_name = serializers.CharField(source="document_type.name", read_only=True)
    verified_by = serializers.StringRelatedField()

    class Meta:
        model = ApplicationDocument
        fields = ["id", "document_type", "document_type_name", "content_type", "size", "is_current",
                  "verification", "verification_note", "verified_by", "verified_at", "uploaded_at"]


class PublicDocumentSerializer(serializers.ModelSerializer):
    document_type_name = serializers.CharField(source="document_type.name", read_only=True)

    class Meta:
        model = ApplicationDocument
        fields = ["document_type", "document_type_name", "verification", "verification_note", "uploaded_at"]


class DocumentUploadSerializer(serializers.Serializer):
    document_type = serializers.PrimaryKeyRelatedField(queryset=DocumentType.objects.filter(is_active=True))
    file = serializers.FileField()


class StatusChangeSerializer(serializers.ModelSerializer):
    changed_by = serializers.StringRelatedField()

    class Meta:
        model = ApplicationStatusChange
        fields = ["from_status", "to_status", "changed_by", "message", "created_at"]


class ApplicationListSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="class_applied.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    child_name = serializers.CharField(read_only=True)
    primary_phone = serializers.CharField(read_only=True)

    class Meta:
        model = AdmissionApplication
        fields = ["id", "application_number", "child_name", "date_of_birth", "class_name", "session_name",
                  "primary_phone", "status", "submitted_at"]


class ApplicationDetailSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="class_applied.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    documents = serializers.SerializerMethodField()
    required_documents = DocumentTypeSerializer(source="required_document_types", many=True, read_only=True)
    missing_documents = serializers.SerializerMethodField()
    history = StatusChangeSerializer(many=True, read_only=True)
    reviewed_by = serializers.StringRelatedField()
    student_id = serializers.SerializerMethodField()

    class Meta:
        model = AdmissionApplication
        exclude = ["access_token_hash"]

    @extend_schema_field(DocumentSerializer(many=True))
    def get_documents(self, obj):
        return DocumentSerializer(obj.documents.select_related("document_type", "verified_by"), many=True).data

    def get_missing_documents(self, obj) -> list[str]:
        from .services import missing_or_unverified

        return missing_or_unverified(obj)

    def get_student_id(self, obj) -> int | None:
        student = getattr(obj, "student", None)
        return student.pk if student else None

    def to_representation(self, instance):
        from core.permissions import has_capability

        data = super().to_representation(instance)
        request = self.context.get("request")
        if not (request and has_capability(request.user, "students.view_sensitive")):
            data["aadhaar_number"] = mask_aadhaar(instance.aadhaar_number)
        return data


class TransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=AdmissionApplication.Status.choices)
    message = serializers.CharField(required=False, allow_blank=True, default="")
    internal_notes = serializers.CharField(required=False, allow_blank=True)


class ApproveSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True, default="")


class AdmitSerializer(serializers.Serializer):
    section = serializers.PrimaryKeyRelatedField(queryset=Section.objects.all())
    admission_date = serializers.DateField(required=False)
    roll_number = serializers.IntegerField(required=False, min_value=1)


class VerifySerializer(serializers.Serializer):
    verification = serializers.ChoiceField(choices=[
        ApplicationDocument.Verification.VERIFIED, ApplicationDocument.Verification.REJECTED,
    ])
    note = serializers.CharField(required=False, allow_blank=True, default="")


class TrackSerializer(serializers.Serializer):
    application_number = serializers.CharField()
    date_of_birth = serializers.DateField()
    phone = serializers.CharField()
