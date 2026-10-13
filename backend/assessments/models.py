from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Assessment(models.Model):
    """A test or exam in one subject for one section, e.g. Unit Test 1 in Class 3 A Maths."""

    section = models.ForeignKey("academics.Section", on_delete=models.PROTECT, related_name="assessments")
    subject = models.ForeignKey("academics.Subject", on_delete=models.PROTECT, related_name="assessments")
    name = models.CharField(max_length=80, help_text="e.g. Unit Test 1, Half-yearly")
    date = models.DateField()
    max_marks = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(1)])
    is_published = models.BooleanField(default=False, help_text="Parents see marks only once published")
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "subject__order"]
        constraints = [
            models.UniqueConstraint(fields=["section", "subject", "name"], name="unique_assessment_name"),
        ]

    def __str__(self):
        return f"{self.name}: {self.subject} ({self.section})"


class Mark(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="marks")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="marks")
    marks = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    is_absent = models.BooleanField(default=False)
    remark = models.CharField(max_length=200, blank=True)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["assessment", "student"]
        constraints = [
            models.UniqueConstraint(fields=["assessment", "student"], name="one_mark_per_student_assessment"),
        ]

    def __str__(self):
        return f"{self.student}: {'AB' if self.is_absent else self.marks}/{self.assessment.max_marks}"
