from collections import Counter as Tally
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from academics.models import AcademicSession, Enrollment
from attendance.models import AttendanceRecord
from core.models import Counter
from fees.models import Invoice
from students.models import Student

from .models import TransferCertificate
from .words import date_words


class DuesOutstanding(Exception):
    def __init__(self, amount):
        super().__init__(f"Fees of Rs {amount:,.2f} are unpaid.")
        self.amount = amount


def fees_due(student):
    invoices = Invoice.objects.filter(student=student).exclude(status=Invoice.Status.CANCELLED)
    return sum((i.balance for i in invoices), Decimal("0"))


def last_enrollment(student):
    return (Enrollment.objects.filter(student=student).select_related("section__school_class", "session")
            .order_by("-session__start_date").first())


def snapshot(student):
    """The student's details as they will be printed. Frozen at issue so later edits don't change the TC."""
    guardians = {"father": "", "mother": "", "guardian": ""}
    for link in student.guardian_links.select_related("guardian").order_by("-is_primary_contact"):
        if not guardians[link.relationship]:
            guardians[link.relationship] = link.guardian.full_name
    e = last_enrollment(student)
    days = Tally()
    if e:
        days.update(AttendanceRecord.objects.filter(student=student, section__session=e.session)
                    .values_list("status", flat=True))
    return {
        "name": student.full_name, "admission_number": student.admission_number,
        "father_name": guardians["father"], "mother_name": guardians["mother"], "guardian_name": guardians["guardian"],
        "date_of_birth": student.date_of_birth.isoformat(), "date_of_birth_words": date_words(student.date_of_birth),
        "gender": student.get_gender_display(), "nationality": student.nationality, "religion": student.religion,
        "category": student.get_category_display(),
        "admission_date": student.admission_date.isoformat(), "admitted_in_class": student.admitted_in_class.name,
        "last_class": e.section.school_class.name if e else "", "last_session": e.session.name if e else "",
        "working_days": sum(days.values()), "days_present": days["present"] + days["late"],
    }


def tc_number(session_name):
    return f"TC/{session_name}/{Counter.take(f'tc:{session_name}'):04d}"


@transaction.atomic
def issue(tc, user, dues_waived_reason=""):
    tc = TransferCertificate.objects.select_for_update().get(pk=tc.pk)
    if tc.status != TransferCertificate.Status.REQUESTED:
        raise ValueError("Only a requested TC can be issued.")
    due = fees_due(tc.student)
    if due > 0 and not dues_waived_reason.strip():
        raise DuesOutstanding(due)
    session = AcademicSession.current()
    today = timezone.localdate()
    tc.number = tc_number(session.name if session else str(today.year))
    tc.status = TransferCertificate.Status.ISSUED
    tc.issued_by, tc.issued_on = user, today
    tc.fees_due = due
    tc.dues_waived_reason = dues_waived_reason.strip() if due > 0 else ""
    tc.details = snapshot(tc.student)
    tc.save()
    Student.objects.filter(pk=tc.student_id).update(status=Student.Status.TC_ISSUED)
    Enrollment.objects.filter(student=tc.student, status=Enrollment.Status.ACTIVE).update(status=Enrollment.Status.LEFT)
    return tc


@transaction.atomic
def cancel(tc, user, reason):
    """Cancel a request, or withdraw an issued TC. The number stays used so the register has no gaps."""
    tc = TransferCertificate.objects.select_for_update().get(pk=tc.pk)
    if tc.status == TransferCertificate.Status.CANCELLED:
        raise ValueError("This TC is already cancelled.")
    was_issued = tc.status == TransferCertificate.Status.ISSUED
    tc.status = TransferCertificate.Status.CANCELLED
    tc.cancelled_by, tc.cancelled_at, tc.cancel_reason = user, timezone.now(), reason
    tc.save()
    if was_issued:
        student = tc.student
        if student.status == Student.Status.TC_ISSUED:
            Student.objects.filter(pk=student.pk).update(status=Student.Status.ACTIVE)
            current = Enrollment.objects.filter(student=student, session__is_current=True, status=Enrollment.Status.LEFT)
            current.update(status=Enrollment.Status.ACTIVE)
    return tc
