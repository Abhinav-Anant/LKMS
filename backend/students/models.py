from django.conf import settings
from django.db import models

from core.storage import RandomPath, get_private_storage

from .choices import BLOOD_GROUPS, Category, Gender, Relationship
from .validators import validate_aadhaar, validate_indian_mobile, validate_pincode


class Student(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Studying"
        LEFT = "left", "Left school"
        TC_ISSUED = "tc_issued", "TC issued"
        ALUMNI = "alumni", "Passed out"

    admission_number = models.CharField(max_length=20, unique=True, help_text="Serial number in the admission register")
    admission_date = models.DateField()
    admitted_in_class = models.ForeignKey("academics.SchoolClass", on_delete=models.PROTECT, related_name="+")
    application = models.OneToOneField(
        "admissions.AdmissionApplication", null=True, blank=True, on_delete=models.SET_NULL, related_name="student"
    )

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

    address_line = models.TextField()
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100, default="Rajasthan")
    pincode = models.CharField(max_length=6, validators=[validate_pincode])

    previous_school = models.CharField(max_length=200, blank=True)
    photo = models.ImageField(upload_to=RandomPath("student-photos"), storage=get_private_storage, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    guardians = models.ManyToManyField("Guardian", through="StudentGuardian", related_name="students")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["first_name", "last_name"]
        indexes = [models.Index(fields=["first_name", "last_name"])]

    def __str__(self):
        return f"{self.full_name} ({self.admission_number})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def current_enrollment(self):
        return self.enrollments.select_related("section__school_class", "session").filter(session__is_current=True).first()


class Guardian(models.Model):
    """A parent or guardian. One guardian can be linked to several children (siblings)."""

    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=10, validators=[validate_indian_mobile], db_index=True)
    alternate_phone = models.CharField(max_length=10, blank=True, validators=[validate_indian_mobile])
    email = models.EmailField(blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    qualification = models.CharField(max_length=100, blank=True)
    annual_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    address = models.TextField(blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="guardian_profile",
        help_text="Parent portal login (Phase 3)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.phone})"


class StudentGuardian(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="guardian_links")
    guardian = models.ForeignKey(Guardian, on_delete=models.PROTECT, related_name="student_links")
    relationship = models.CharField(max_length=20, choices=Relationship.choices)
    relationship_detail = models.CharField(max_length=50, blank=True, help_text="For guardians, e.g. Uncle")
    is_primary_contact = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "guardian"], name="unique_student_guardian"),
            models.UniqueConstraint(
                fields=["student"], condition=models.Q(is_primary_contact=True), name="one_primary_contact_per_student"
            ),
        ]

    def __str__(self):
        return f"{self.guardian.full_name} is {self.get_relationship_display()} of {self.student.full_name}"
