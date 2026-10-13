from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from academics.models import AcademicSession, SchoolClass, Section
from core.models import SchoolProfile
from fees.models import FeeAmount, FeeHead, Installment
from users.models import User

pytestmark = pytest.mark.django_db

FIRST_RUN = [
    # 1. the school
    "", "", "Main Road, Kota", "Kota", "", "324001", "9829012345", "", "", "08123456789", "", "", "", "", "120",
    # 2. school year
    "", "", "",
    # 3. classes
    "n", "Nursery, LKG, UKG, Class 1, Class 2", "a, b", "35",
    # 4. fees: quarterly, due on the 10th, tuition per class, the rest the same for all, one extra fee
    "4", "", "", "2,500", "2500", "2500", "3000", "3000", "", "5000", "", "4000", "", "500",
    "Transport fee", "y", "", "800", "",
    # 5. administrator
    "abhinav", "Abhinav", "", "",
]


def run(monkeypatch, answers, passwords=()):
    answers, passwords = iter(answers), iter(passwords)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr("core.management.commands.setup_school.getpass.getpass", lambda prompt="": next(passwords))
    call_command("setup_school", stdout=StringIO())
    assert next(answers, None) is None, "not every answer was used"


def test_first_run_saves_everything(monkeypatch, capsys):
    run(monkeypatch, FIRST_RUN, ["short", "Lotus-admin-2026", "Lotus-admin-2026"])

    profile = SchoolProfile.get()
    assert (profile.name, profile.address, profile.pincode, profile.udise_code) == (
        "Lotus Kids School", "Main Road, Kota", "324001", "08123456789")
    assert profile.next_admission_number == 120

    current = AcademicSession.current()
    upcoming = AcademicSession.objects.get(admissions_open=True)
    assert current.start_date.month == 4 and current.end_date.month == 3
    assert upcoming.start_date.year == current.start_date.year + 1

    classes = list(SchoolClass.objects.filter(is_active=True))
    assert [(c.name, c.code) for c in classes] == [
        ("Nursery", "NUR"), ("LKG", "LKG"), ("UKG", "UKG"), ("Class 1", "1"), ("Class 2", "2")]
    assert classes[0].min_age_years == 3
    assert Section.objects.count() == 5 * 2 * 2
    assert set(Section.objects.values_list("capacity", flat=True)) == {35}

    assert list(Installment.objects.filter(session=current).values_list("name", flat=True)) == [
        "Quarter 1", "Quarter 2", "Quarter 3", "Quarter 4"]
    assert Installment.objects.get(session=current, name="Quarter 3").due_date.day == 10
    assert FeeAmount.objects.count() == 5 * 4 * 2 + 5 * 3  # tuition and transport every quarter, 3 heads once
    tuition = FeeAmount.objects.get(fee_head__code="tuition", school_class__code="1", installment__order=2)
    assert tuition.amount == Decimal("3000")
    assert FeeHead.objects.get(code="admission").new_students_only
    assert not FeeAmount.objects.filter(fee_head__code="exam", installment__order=2).exists()
    assert FeeHead.objects.get(code="transport-fee").name == "Transport fee"

    admin = User.objects.get(username="abhinav")
    assert admin.role == "admin" and admin.is_superuser and admin.check_password("Lotus-admin-2026")
    out = capsys.readouterr().out
    assert "This password is too short" in out
    assert "Nursery: ₹17,700" in out  # 4 x (2500 + 800) + 4000 + 500


def test_running_again_keeps_everything(monkeypatch):
    run(monkeypatch, FIRST_RUN, ["Lotus-admin-2026", "Lotus-admin-2026"])
    before = list(FeeAmount.objects.values_list("pk", "amount"))

    # Enter for every question, then "no" to entering fees again and to changing the administrator.
    run(monkeypatch, [""] * 15 + [""] * 3 + [""] * 3 + ["", ""])

    assert SchoolProfile.get().address == "Main Road, Kota"
    assert SchoolClass.objects.filter(is_active=True).count() == 5
    assert set(Section.objects.values_list("capacity", flat=True)) == {35}
    assert list(FeeAmount.objects.values_list("pk", "amount")) == before
    assert User.objects.filter(role="admin").count() == 1


def test_replaces_placeholder_classes_and_fees(monkeypatch):
    call_command("seed_lkms_defaults", stdout=StringIO())
    answers = [""] * 2 + ["Kota", "Kota", "", "324001", "9829012345"] + [""] * 8 + [""] * 3 + [
        "n", "LKG, UKG, Class 1", "", "",
        "y", "1", "15", "y", "30000", "", "5000", "", "0", "", "0", "",
        "abhinav", "Abhinav", "", "9829012345",
    ]
    run(monkeypatch, answers, ["Lotus-admin-2026", "Lotus-admin-2026"])

    assert list(SchoolClass.objects.filter(is_active=True).values_list("code", flat=True)) == ["LKG", "UKG", "1"]
    assert not SchoolClass.objects.get(code="NUR").is_active
    session = AcademicSession.current()
    assert list(Installment.objects.filter(session=session).values_list("name", flat=True)) == ["Annual fee"]
    assert set(FeeAmount.objects.values_list("fee_head__code", flat=True)) == {"tuition", "admission"}
    assert FeeAmount.objects.count() == 6
