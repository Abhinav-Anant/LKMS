from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ExamTerm(models.Model):
    """A reporting period that groups tests into one report card, e.g. Half-yearly or Annual."""

    session = models.ForeignKey("academics.AcademicSession", on_delete=models.PROTECT, related_name="exam_terms")
    name = models.CharField(max_length=60, help_text="e.g. Half-yearly, Annual")
    order = models.PositiveSmallIntegerField(default=1)
    start_date = models.DateField(help_text="Attendance on the report card is counted from this date")
    end_date = models.DateField()
    is_published = models.BooleanField(default=False, help_text="Parents see report cards only once published")
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-session__start_date", "order"]
        constraints = [models.UniqueConstraint(fields=["session", "name"], name="unique_term_name_per_session")]

    def __str__(self):
        return f"{self.name} {self.session.name}"

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date must be on or after the start date."})


class GradeBand(models.Model):
    """One row of the grading scale: a percentage of at least `min_percent` earns `grade`."""

    grade = models.CharField(max_length=4, unique=True)
    min_percent = models.DecimalField(
        max_digits=5, decimal_places=2, unique=True, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    description = models.CharField(max_length=60, blank=True, help_text="e.g. Outstanding")
    is_pass = models.BooleanField(default=True, help_text="Untick for the failing grade")

    class Meta:
        ordering = ["-min_percent"]

    def __str__(self):
        return f"{self.grade} ({self.min_percent}% and above)"


class ReportCardEntry(models.Model):
    """What the class teacher adds to a student's report card for a term."""

    term = models.ForeignKey(ExamTerm, on_delete=models.CASCADE, related_name="entries")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="report_card_entries")
    remark = models.CharField(max_length=300, blank=True)
    co_scholastic = models.JSONField(default=dict, blank=True, help_text="Area name to grade, e.g. {\"Art\": \"A\"}")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["term", "student"], name="one_report_entry_per_term")]

    def __str__(self):
        return f"{self.student} {self.term}"
