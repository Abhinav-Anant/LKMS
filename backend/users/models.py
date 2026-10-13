from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A login. Staff sign in with username and password; parents with their mobile number and a one-time code."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        PRINCIPAL = "principal", "Principal"
        OFFICE = "office", "Office staff"
        ACCOUNTANT = "accountant", "Accountant"
        TEACHER = "teacher", "Teacher"
        PARENT = "parent", "Parent"
        STUDENT = "student", "Student"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TEACHER, db_index=True)
    phone = models.CharField(max_length=15, blank=True, db_index=True)
    must_change_password = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_school_staff(self):
        return self.role in {self.Role.ADMIN, self.Role.PRINCIPAL, self.Role.OFFICE, self.Role.ACCOUNTANT, self.Role.TEACHER}


class LoginCode(models.Model):
    """A one-time 6-digit code for a parent to sign in with their mobile number.

    Only a keyed hash of the code is stored. Codes are sent by WhatsApp (Phase 4)
    or read out by the school office, which can issue one from the staff portal.
    """

    class Source(models.TextChoices):
        REQUESTED = "requested", "Requested by parent"
        STAFF = "staff", "Issued by school office"

    phone = models.CharField(max_length=10, db_index=True)
    code_hash = models.CharField(max_length=64)
    source = models.CharField(max_length=10, choices=Source.choices)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
    issued_by = models.ForeignKey("User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Login code for {self.phone} ({self.get_source_display()})"
