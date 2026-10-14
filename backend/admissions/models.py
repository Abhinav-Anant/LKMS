import hashlib
import secrets

from django.conf import settings
from django.db import models, transaction

from core.storage import RandomPath, get_private_storage
from students.choices import BLOOD_GROUPS, Category, Gender, Relationship
from students.validators import validate_aadhaar, validate_indian_mobile, validate_pincode


class DocumentType(models.Model):
    """A document the school asks for, e.g. birth certificate. Configured in admin."""

    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=300, blank=True, help_text="Shown to parents on the form")
    is_required = models.BooleanField(default=True)
    classes = models.ManyToManyField(
        "academics.SchoolClass", blank=True, related_name="+", help_text="Leave empty to ask for it in every class"
    )
    allow_pdf = models.BooleanField(default=True)
    allow_image = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def allowed_formats(self):
        return (("pdf",) if self.allow_pdf else ()) + (("jpg", "png") if self.allow_image else ())

    @classmethod
    def for_class(cls, school_class):
        return cls.objects.filter(is_active=True).filter(
            models.Q(classes__isnull=True) | models.Q(classes=school_class)
        ).distinct()


class AdmissionApplication(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under review"
        DOCUMENTS_REQUESTED = "documents_requested", "Documents requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        ADMITTED = "admitted", "Admitted"

    OPEN_STATUSES = {Status.SUBMITTED, Status.UNDER_REVIEW, Status.DOCUMENTS_REQUESTED}

    application_number = models.CharField(max_length=30, unique=True, editable=False)
    access_token_hash = models.CharField(max_length=64, editable=False)

    session = models.ForeignKey("academics.AcademicSession", on_delete=models.PROTECT, related_name="applications")
    class_applied = models.ForeignKey("academics.SchoolClass", on_delete=models.PROTECT, related_name="applications")

    # Child
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices)
    category = models.CharField(max_length=10, choices=Category.choices, default=Category.GENERAL)
    religion = models.CharField(max_length=50, blank=True)
    mother_tongue = models.CharField(max_length=50, blank=True)
    nationality = models.CharField(max_length=50, default="Indian")
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS, blank=True)
    aadhaar_number = models.CharField(max_length=12, blank=True, validators=[validate_aadhaar])
    previous_school = models.CharField(max_length=200, blank=True)
    previous_class = models.CharField(max_length=50, blank=True)
    sibling_admission_number = models.CharField(
        max_length=20, blank=True, help_text="Admission number of a brother or sister already studying here"
    )

    # Address
    address_line = models.TextField()
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=6, validators=[validate_pincode])

    # Parents and guardian
    father_name = models.CharField(max_length=100, blank=True)
    father_phone = models.CharField(max_length=10, blank=True, validators=[validate_indian_mobile])
    father_email = models.EmailField(blank=True)
    father_occupation = models.CharField(max_length=100, blank=True)
    father_qualification = models.CharField(max_length=100, blank=True)
    father_annual_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    mother_name = models.CharField(max_length=100, blank=True)
    mother_phone = models.CharField(max_length=10, blank=True, validators=[validate_indian_mobile])
    mother_email = models.EmailField(blank=True)
    mother_occupation = models.CharField(max_length=100, blank=True)
    mother_qualification = models.CharField(max_length=100, blank=True)
    mother_annual_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    guardian_name = models.CharField(max_length=100, blank=True)
    guardian_relationship = models.CharField(max_length=50, blank=True, help_text="e.g. Uncle")
    guardian_phone = models.CharField(max_length=10, blank=True, validators=[validate_indian_mobile])
    guardian_email = models.EmailField(blank=True)
    guardian_occupation = models.CharField(max_length=100, blank=True)
    primary_contact = models.CharField(max_length=20, choices=Relationship.choices)

    # Consent (parental consent for processing a child's data)
    declaration_accepted = models.BooleanField(default=False)
    consent_given_at = models.DateTimeField(null=True, blank=True)

    # Workflow
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    status_message = models.TextField(blank=True, help_text="Shown to the parent, e.g. which documents are missing")
    internal_notes = models.TextField(blank=True, help_text="Staff only")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [models.Index(fields=["session", "class_applied", "status"])]

    def __str__(self):
        return f"{self.application_number} {self.child_name}"

    @property
    def child_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def primary_phone(self):
        return getattr(self, f"{self.primary_contact}_phone", "")

    def required_document_types(self):
        return DocumentType.for_class(self.class_applied).filter(is_required=True)

    def current_documents(self):
        return self.documents.filter(is_current=True).select_related("document_type")

    def check_token(self, token):
        return bool(token) and secrets.compare_digest(self.access_token_hash, hash_token(token))

    @classmethod
    def next_number(cls, session):
        """Allocate the next application number for a session, e.g. LK-2026-27-00001."""
        from academics.models import AcademicSession
        from core.models import SchoolProfile

        with transaction.atomic():
            locked = AcademicSession.objects.select_for_update().get(pk=session.pk)
            seq = locked.next_application_number
            locked.next_application_number = seq + 1
            locked.save(update_fields=["next_application_number"])
        return f"{SchoolProfile.get().short_code}-{session.name}-{seq:05d}"


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


class ApplicationDocument(models.Model):
    class Verification(models.TextChoices):
        PENDING = "pending", "Not checked yet"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Not acceptable"

    application = models.ForeignKey(AdmissionApplication, on_delete=models.CASCADE, related_name="documents")
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT, related_name="+")
    file = models.FileField(upload_to=RandomPath("admission-documents"), storage=get_private_storage)
    content_type = models.CharField(max_length=50)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    is_current = models.BooleanField(default=True, help_text="False once a newer upload replaces it")
    verification = models.CharField(max_length=20, choices=Verification.choices, default=Verification.PENDING)
    verification_note = models.CharField(max_length=300, blank=True, help_text="Shown to the parent if rejected")
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    verified_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document_type__order", "-uploaded_at"]

    def __str__(self):
        return f"{self.document_type} for {self.application.application_number}"

    @property
    def extension(self):
        return {"application/pdf": "pdf", "image/png": "png"}.get(self.content_type, "jpg")


class ApplicationStatusChange(models.Model):
    application = models.ForeignKey(AdmissionApplication, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
