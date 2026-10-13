"""Create PLACEHOLDER fee heads, installments and amounts for the current session.

The amounts are made up so the screens can be tried out. Replace them with
the school's real fee structure (Fees > Setup in the staff app) before use.
Safe to run more than once: existing rows are kept.
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from academics.models import AcademicSession, SchoolClass
from fees.models import FeeAmount, FeeHead, Installment

HEADS = [
    # code, name, new students only
    ("admission", "Admission fee", True),
    ("tuition", "Tuition fee", False),
    ("annual", "Annual charges", False),
    ("exam", "Examination fee", False),
]

# Quarterly tuition by class band (placeholder rupees).
TUITION = {"pre-primary": Decimal("2500"), "primary": Decimal("3000"), "upper": Decimal("3500")}
ONE_TIME = {"admission": Decimal("5000"), "annual": Decimal("4000")}
EXAM = Decimal("500")


def band(school_class):
    if school_class.code in ("NUR", "LKG", "UKG"):
        return "pre-primary"
    return "primary" if school_class.code.isdigit() and int(school_class.code) <= 5 else "upper"


class Command(BaseCommand):
    help = "Create placeholder fee heads, four quarterly installments and sample amounts."

    @transaction.atomic
    def handle(self, *args, **options):
        session = AcademicSession.current()
        if session is None:
            raise CommandError("Set a current academic session first (seed_lkms_defaults does this).")
        heads = {}
        for order, (code, name, new_only) in enumerate(HEADS, start=1):
            heads[code], _ = FeeHead.objects.get_or_create(
                code=code, defaults={"name": name, "new_students_only": new_only, "order": order}
            )

        year = session.start_date.year
        quarters = [
            ("Quarter 1", date(year, 4, 10)), ("Quarter 2", date(year, 7, 10)),
            ("Quarter 3", date(year, 10, 10)), ("Quarter 4", date(year + 1, 1, 10)),
        ]
        for order, (name, due) in enumerate(quarters, start=1):
            installment, created = Installment.objects.get_or_create(
                session=session, name=name, defaults={"due_date": due, "order": order}
            )
            if not created:
                continue
            for school_class in SchoolClass.objects.filter(is_active=True):
                rows = {"tuition": TUITION[band(school_class)]}
                if order == 1:
                    rows.update(ONE_TIME)
                if order in (2, 4):
                    rows["exam"] = EXAM
                for code, amount in rows.items():
                    FeeAmount.objects.get_or_create(
                        installment=installment, school_class=school_class, fee_head=heads[code], defaults={"amount": amount}
                    )
        self.stdout.write(self.style.SUCCESS(
            f"Placeholder fees ready for {session}: {len(HEADS)} heads, 4 quarterly installments. Amounts are samples only."
        ))
