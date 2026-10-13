from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class AcademicSession(models.Model):
    """A school year, e.g. 2026-27 (1 April to 31 March)."""

    name = models.CharField(max_length=20, unique=True, help_text="e.g. 2026-27")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False, help_text="The session the school is running now")
    admissions_open = models.BooleanField(default=False, help_text="Accept online applications for this session")
    age_cutoff_date = models.DateField(
        null=True, blank=True, help_text="Date on which a child's age is checked for admission (defaults to start date)"
    )
    next_application_number = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(fields=["is_current"], condition=models.Q(is_current=True), name="one_current_session"),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError({"end_date": "End date must be after start date."})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_current:
                AcademicSession.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
            super().save(*args, **kwargs)

    @property
    def effective_age_cutoff(self):
        return self.age_cutoff_date or self.start_date

    @classmethod
    def current(cls):
        return cls.objects.filter(is_current=True).first()


class SchoolClass(models.Model):
    """A grade the school teaches, e.g. Nursery, LKG, Class 1."""

    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True, help_text="Short code, e.g. NUR, LKG, 1")
    order = models.PositiveSmallIntegerField(unique=True, help_text="Sort order; promotion goes to the next order")
    min_age_years = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Minimum age on the cut-off date")
    max_age_years = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Maximum age on the cut-off date")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "class"
        verbose_name_plural = "classes"

    def __str__(self):
        return self.name

    def next_class(self):
        return SchoolClass.objects.filter(order__gt=self.order, is_active=True).order_by("order").first()


class Section(models.Model):
    session = models.ForeignKey(AcademicSession, on_delete=models.PROTECT, related_name="sections")
    school_class = models.ForeignKey(SchoolClass, on_delete=models.PROTECT, related_name="sections")
    name = models.CharField(max_length=10, help_text="e.g. A")
    capacity = models.PositiveSmallIntegerField(default=40)
    class_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="class_teacher_of"
    )

    class Meta:
        ordering = ["session", "school_class__order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["session", "school_class", "name"], name="unique_section_per_class_session"),
        ]

    def __str__(self):
        return f"{self.school_class.name} {self.name} ({self.session.name})"


class Enrollment(models.Model):
    """A student's place in a section for one session."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Studying"
        PROMOTED = "promoted", "Promoted"
        DETAINED = "detained", "Detained"
        LEFT = "left", "Left school"

    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="enrollments")
    session = models.ForeignKey(AcademicSession, on_delete=models.PROTECT, related_name="enrollments")
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="enrollments")
    roll_number = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    enrolled_on = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["session", "section", "roll_number"]
        constraints = [
            models.UniqueConstraint(fields=["student", "session"], name="one_enrollment_per_session"),
            models.UniqueConstraint(
                fields=["section", "roll_number"], condition=models.Q(roll_number__isnull=False), name="unique_roll_in_section"
            ),
        ]

    def __str__(self):
        return f"{self.student} in {self.section}"

    def clean(self):
        if self.section_id and self.session_id and self.section.session_id != self.session_id:
            raise ValidationError({"section": "Section belongs to a different session."})

    @property
    def school_class(self):
        return self.section.school_class


class Subject(models.Model):
    name = models.CharField(max_length=60, unique=True)
    code = models.SlugField(max_length=20, unique=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class TeachingAssignment(models.Model):
    """Who teaches which subject in which section. Gives the teacher marks entry for it."""

    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teaching_assignments")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="teaching_assignments")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="teaching_assignments")

    class Meta:
        ordering = ["section", "subject__order"]
        constraints = [
            models.UniqueConstraint(fields=["section", "subject"], name="one_teacher_per_subject_section"),
        ]

    def __str__(self):
        return f"{self.teacher} teaches {self.subject} in {self.section}"


class PeriodSlot(models.Model):
    """The school's bell schedule, e.g. period 1 from 8:00 to 8:40."""

    number = models.PositiveSmallIntegerField(unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    label = models.CharField(max_length=30, blank=True, help_text="Optional, e.g. Assembly")

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"Period {self.number} ({self.start_time:%H:%M}-{self.end_time:%H:%M})"

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "End time must be after start time."})


class TimetableEntry(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 1, "Monday"
        TUESDAY = 2, "Tuesday"
        WEDNESDAY = 3, "Wednesday"
        THURSDAY = 4, "Thursday"
        FRIDAY = 5, "Friday"
        SATURDAY = 6, "Saturday"

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="timetable")
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    period = models.ForeignKey(PeriodSlot, on_delete=models.CASCADE, related_name="entries")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="+")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="timetable_entries"
    )

    class Meta:
        ordering = ["weekday", "period__number"]
        constraints = [
            models.UniqueConstraint(fields=["section", "weekday", "period"], name="one_subject_per_period"),
        ]

    def __str__(self):
        return f"{self.section} {self.get_weekday_display()} P{self.period.number}: {self.subject}"
