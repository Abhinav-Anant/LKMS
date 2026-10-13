from django.conf import settings
from django.db import models


class AttendanceRecord(models.Model):
    """One student's attendance for one school day, marked by the class teacher."""

    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        LEAVE = "leave", "On leave"

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="attendance")
    section = models.ForeignKey("academics.Section", on_delete=models.PROTECT, related_name="attendance")
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    note = models.CharField(max_length=200, blank=True)
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["student", "date"], name="one_attendance_per_student_day"),
        ]

    def __str__(self):
        return f"{self.student} {self.date}: {self.get_status_display()}"

    @property
    def counts_present(self):
        return self.status in (self.Status.PRESENT, self.Status.LATE)
