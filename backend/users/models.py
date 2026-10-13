from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A login. Staff sign in with username and password; parent logins arrive in Phase 3."""

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
