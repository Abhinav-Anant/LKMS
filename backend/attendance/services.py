from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from academics.models import Enrollment
from academics.scope import can_take_attendance, sees_all
from core import audit
from core.notify import notify
from students.models import Student

from .models import AttendanceRecord

# Teachers may correct attendance up to this many days back; admin and principal any day.
TEACHER_EDIT_DAYS = 7


def roster(section):
    """Students studying in the section, in roll order."""
    return (
        Enrollment.objects.filter(section=section, status=Enrollment.Status.ACTIVE)
        .select_related("student")
        .order_by("roll_number", "student__first_name")
    )


def can_edit(user, section, day):
    if not can_take_attendance(user, section):
        return False
    today = timezone.localdate()
    if day > today or not (section.session.start_date <= day <= section.session.end_date):
        return False
    return sees_all(user) or (today - day).days <= TEACHER_EDIT_DAYS


def check_date(section, day):
    today = timezone.localdate()
    if day > today:
        raise ValidationError({"date": "Attendance cannot be marked for a future date."})
    if not (section.session.start_date <= day <= section.session.end_date):
        raise ValidationError({"date": "Date is outside this section's session."})
    if day.weekday() == 6:
        raise ValidationError({"date": "Sunday is not a school day."})


@transaction.atomic
def mark(request, section, day, rows):
    check_date(section, day)
    if not can_take_attendance(request.user, section):
        raise PermissionDenied("Only the class teacher can mark attendance for this section.")
    if not can_edit(request.user, section, day):
        raise PermissionDenied(f"Attendance older than {TEACHER_EDIT_DAYS} days can only be changed by the principal.")
    allowed = {e.student_id for e in roster(section)}
    unknown = [r["student"] for r in rows if r["student"] not in allowed]
    if unknown:
        raise ValidationError({"records": f"These students are not in this section: {unknown}"})
    existing = {r.student_id: r for r in AttendanceRecord.objects.filter(student_id__in=allowed, date=day)}
    changed = 0
    newly_absent = []
    for row in rows:
        record = existing.get(row["student"])
        if row["status"] == AttendanceRecord.Status.ABSENT and (record is None or record.status != AttendanceRecord.Status.ABSENT):
            newly_absent.append(row["student"])
        if record is None:
            AttendanceRecord.objects.create(
                student_id=row["student"], section=section, date=day, status=row["status"],
                note=row.get("note", ""), marked_by=request.user,
            )
            changed += 1
        elif record.status != row["status"] or record.note != row.get("note", ""):
            record.status, record.note, record.marked_by, record.section = row["status"], row.get("note", ""), request.user, section
            record.save()
            changed += 1
    audit.record(request, "attendance.marked", section, date=day.isoformat(), changed=changed, rows=len(rows))
    # Tell parents the same day only; corrections to earlier days stay quiet.
    if day == timezone.localdate():
        for student in Student.objects.filter(pk__in=newly_absent):
            notify("attendance.absent", student=student, date=day)
    return changed

