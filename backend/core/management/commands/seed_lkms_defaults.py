"""Create placeholder school data so the system can be tried out.

Everything here is a PLACEHOLDER until Lotus Kids confirms its real classes,
sections and document list. Safe to run more than once: existing rows are kept.
"""

from datetime import date, time

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from academics.models import AcademicSession, PeriodSlot, SchoolClass, Section, Subject
from admissions.models import DocumentType
from core.models import SchoolProfile

CLASSES = [
    # name, code, min age, max age (on the session's cut-off date)
    ("Nursery", "NUR", 3, 4),
    ("LKG", "LKG", 4, 5),
    ("UKG", "UKG", 5, 6),
] + [(f"Class {n}", str(n), None, None) for n in range(1, 9)]

DOCUMENTS = [
    # code, name, required, description, allow_pdf, allow_image
    ("birth-certificate", "Birth certificate", True, "Issued by the municipality or gram panchayat", True, True),
    ("photo", "Passport-size photograph of the child", True, "Recent colour photo, JPG or PNG", False, True),
    ("child-aadhaar", "Child's Aadhaar card", False, "If the child has one", True, True),
    ("parent-id", "Parent's ID proof", True, "Aadhaar, voter ID, PAN or passport", True, True),
    ("address-proof", "Address proof", True, "Electricity bill, rent agreement or Aadhaar", True, True),
    ("transfer-certificate", "Transfer certificate (TC)", False, "From the previous school, for Class 2 and above", True, True),
    ("previous-report-card", "Previous class report card", False, "For Class 1 and above", True, True),
    ("category-certificate", "Caste / category certificate", False, "Only if applying under SC, ST, OBC, MBC or EWS", True, True),
]

SUBJECTS = ["Hindi", "English", "Mathematics", "Environmental Studies", "Science", "Social Science", "Sanskrit",
            "Computer", "Art", "Physical Education"]

PERIODS = [
    # number, start, end
    (1, time(8, 0), time(8, 40)), (2, time(8, 40), time(9, 20)), (3, time(9, 20), time(10, 0)),
    (4, time(10, 20), time(11, 0)), (5, time(11, 0), time(11, 40)), (6, time(11, 40), time(12, 20)),
]


def current_session_dates(today):
    start_year = today.year if today.month >= 4 else today.year - 1
    return start_year, date(start_year, 4, 1), date(start_year + 1, 3, 31)


class Command(BaseCommand):
    help = "Create placeholder classes, sections, sessions, document types, subjects and periods."

    @transaction.atomic
    def handle(self, *args, **options):
        SchoolProfile.get()

        year, start, end = current_session_dates(date.today())
        current, _ = AcademicSession.objects.get_or_create(
            name=f"{year}-{str(year + 1)[-2:]}", defaults={"start_date": start, "end_date": end, "is_current": True}
        )
        upcoming, _ = AcademicSession.objects.get_or_create(
            name=f"{year + 1}-{str(year + 2)[-2:]}",
            defaults={"start_date": date(year + 1, 4, 1), "end_date": date(year + 2, 3, 31), "admissions_open": True},
        )

        for order, (name, code, min_age, max_age) in enumerate(CLASSES, start=1):
            school_class, _ = SchoolClass.objects.get_or_create(
                code=code, defaults={"name": name, "order": order, "min_age_years": min_age, "max_age_years": max_age}
            )
            for session in (current, upcoming):
                Section.objects.get_or_create(session=session, school_class=school_class, name="A")

        for order, (code, name, required, description, allow_pdf, allow_image) in enumerate(DOCUMENTS, start=1):
            DocumentType.objects.get_or_create(code=code, defaults={
                "name": name, "is_required": required, "description": description,
                "allow_pdf": allow_pdf, "allow_image": allow_image, "order": order,
            })

        for order, name in enumerate(SUBJECTS, start=1):
            Subject.objects.get_or_create(name=name, defaults={"code": name.lower().replace(" ", "-")[:20], "order": order})
        for number, begins, ends in PERIODS:
            PeriodSlot.objects.get_or_create(number=number, defaults={"start_time": begins, "end_time": ends})

        call_command("seed_fee_placeholders", stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(
            f"Placeholder data ready: sessions {current} (current) and {upcoming} (admissions open), "
            f"{len(CLASSES)} classes with section A, {len(DOCUMENTS)} document types, "
            f"{len(SUBJECTS)} subjects and {len(PERIODS)} periods."
        ))
