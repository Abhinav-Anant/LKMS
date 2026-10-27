"""manage.py setup_school: every question a new school needs, with the example answers files."""

from datetime import time
from decimal import Decimal
from io import StringIO

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command

from academics.models import AcademicSession, PeriodSlot, SchoolClass, Section, Subject
from admissions.models import DocumentType
from core.management.commands import setup_school
from core.models import SchoolProfile
from exams.models import GradeBand
from fees.models import FeeAmount, FeeHead, Installment
from users.models import User

pytestmark = pytest.mark.django_db

EXAMPLES = settings.BASE_DIR.parent / "examples"
GREEN_VALLEY = str(EXAMPLES / "green-valley" / "school.json")
LOTUS = str(EXAMPLES / "lotus-kids" / "school.json")


class Person:
    """Answers each question by matching words in it; Enter (the suggestion) otherwise."""

    def __init__(self, monkeypatch, answers=None, passwords=()):
        self.answers, self.passwords = dict(answers or {}), iter(passwords)
        self.question, self.asked = "", []
        real_print = print

        def fake_print(*args, **kwargs):
            text = " ".join(str(a) for a in args)
            if text.strip() and not text.startswith(" "):
                self.question = text
            real_print(*args, **kwargs)

        monkeypatch.setattr(setup_school, "print", fake_print, raising=False)
        monkeypatch.setattr("builtins.input", self.reply)
        monkeypatch.setattr(setup_school.getpass, "getpass", lambda prompt="": next(self.passwords))

    def reply(self, prompt=""):
        self.asked.append(self.question)
        for words, answer in self.answers.items():
            if words in self.question:
                return answer.pop(0) if isinstance(answer, list) else answer
        return ""


def run(*args):
    call_command("setup_school", *args, stdout=StringIO())


def test_green_valley_from_its_answers_file_without_questions(monkeypatch):
    monkeypatch.setenv("LKMS_ADMIN_PASSWORD", "Green-valley-2026")
    run("--answers", GREEN_VALLEY, "--accept-defaults")

    school = SchoolProfile.get()
    assert (school.name, school.short_code, school.board, school.board_label) == (
        "Green Valley Public School", "GVPS", "cbse", "CBSE")
    assert school.brand_colour == "#15803d" and not school.logo
    assert (school.admission_number_prefix, school.admission_number_width, school.next_admission_number) == (
        "GV/", 5, 1201)
    assert (school.upi_id, school.upi_name, school.office_can_collect_fees) == (
        "greenvalley@okhdfcbank", "Green Valley Education Trust", True)
    assert (school.fee_reminder_days_before, school.fee_reminder_every_days) == (5, 10)

    current = AcademicSession.current()
    assert str(current.age_cutoff_date) == "2027-03-31"
    classes = list(SchoolClass.objects.filter(is_active=True))
    assert [c.name for c in classes] == ["Pre-Nursery", "Nursery", "KG", "Class 1", "Class 2", "Class 3",
                                         "Class 4", "Class 5"]
    assert (classes[0].min_age_years, classes[0].max_age_years) == (2, 3)
    assert Section.objects.filter(session=current).count() == 16
    assert list(Subject.objects.filter(is_active=True).values_list("name", flat=True))[3] == "EVS"

    slots = list(PeriodSlot.objects.all())
    assert len(slots) == 7 and slots[0].start_time == time(8, 30)
    assert slots[4].start_time == time(11, 15)  # 4 x 35 minutes from 8:30, then a 25-minute break
    assert DocumentType.objects.filter(is_active=True).count() == 4
    assert not DocumentType.objects.get(name="Previous class report card").is_required
    assert list(GradeBand.objects.order_by("-min_percent").values_list("grade", flat=True))[:2] == ["A1", "A2"]

    assert Installment.objects.filter(session=current).count() == 12
    assert Installment.objects.get(session=current, name="April").due_date.day == 7
    kg = SchoolClass.objects.get(name="KG")
    assert FeeAmount.objects.get(installment__name="May", school_class=kg, fee_head__code="tuition").amount == 2000
    assert FeeAmount.objects.filter(fee_head__code="transport-fee").count() == 12 * 8
    assert FeeAmount.objects.get(installment__name="April", school_class=kg, fee_head__code="admission").amount \
        == Decimal("10000")

    admin = User.objects.get(username="gvadmin")
    assert admin.role == "admin" and admin.check_password("Green-valley-2026")
    principal = User.objects.get(role="principal")
    assert principal.get_full_name() == "Suresh Gupta" and principal.must_change_password
    assert User.objects.get(role="office").phone == "9829000102"


def test_accept_defaults_stops_at_a_missing_answer(monkeypatch):
    with pytest.raises(CommandError, match="Address"):
        run("--answers", LOTUS, "--accept-defaults")


def test_lotus_kids_interactively(monkeypatch, capsys):
    Person(monkeypatch, {
        "Address?": "Main Road, Kota", "District?": "Kota", "PIN code?": "324001", "School phone": "9829012345",
        "Logo picture?": ["/no/such/file.png", ""],
        "Tuition fee for": "3,000", "Tuition fee is the same": "y", "Tuition fee, in rupees": "3000",
        "Admission fee, in rupees": "5000", "Annual charges, in rupees": "4000",
        "Examination fee, in rupees": "500",
        "Username?": "abhinav", "First name?": "Abhinav",
        "Name of a staff member": ["Priya Sharma", ""], "Their role?": "principal",
    }, passwords=["short", "Lotus-admin-2026", "Lotus-admin-2026"])
    run("--answers", LOTUS)

    school = SchoolProfile.get()
    assert (school.name, school.state, school.board_label) == (
        "Lotus Kids School", "Rajasthan", "Rajasthan Board of Secondary Education (RBSE)")
    assert school.brand_colour == "#ad2972"
    assert school.upi_qr and school.upi_id == "8619190956@SBI"
    assert SchoolClass.objects.filter(is_active=True).count() == 12
    assert FeeAmount.objects.filter(fee_head__code="tuition").count() == 12 * 4
    assert (school.map_latitude, school.map_longitude) == (Decimal("26.830321"), Decimal("75.825578"))
    assert set(FeeHead.objects.values_list("code", flat=True)) >= {"tuition", "admission", "annual", "exam"}
    assert User.objects.get(username="abhinav").role == "admin"
    priya = User.objects.get(username="priya")
    assert priya.role == "principal" and priya.must_change_password

    out = capsys.readouterr().out
    assert "No file there" in out and "This password is too short" in out
    assert "Nursery: ₹16,500" in out  # 4 x 3000 + 4000 + 500
    assert "username priya, temporary password Lk-" in out


def test_running_again_keeps_everything(monkeypatch):
    monkeypatch.setenv("LKMS_ADMIN_PASSWORD", "Green-valley-2026")
    run("--answers", GREEN_VALLEY, "--accept-defaults")
    fees = list(FeeAmount.objects.values_list("pk", "amount"))
    staff = User.objects.count()

    person = Person(monkeypatch)  # Enter for everything: keep what is saved
    run()
    assert "Fees for" in " ".join(person.asked)  # asked whether to enter fees again, and kept them
    assert list(FeeAmount.objects.values_list("pk", "amount")) == fees
    assert SchoolProfile.get().name == "Green Valley Public School"
    assert SchoolClass.objects.filter(is_active=True).count() == 8
    assert set(Section.objects.values_list("capacity", flat=True)) == {35}
    assert PeriodSlot.objects.count() == 7
    assert list(GradeBand.objects.order_by("-min_percent").values_list("grade", flat=True))[0] == "A1"
    assert User.objects.count() == staff


def test_replaces_placeholder_classes_and_fees(monkeypatch):
    call_command("seed_lkms_defaults", stdout=StringIO())
    Person(monkeypatch, {
        "School name?": "Sunrise School", "Address?": "Station Road", "District?": "Ajmer", "State?": "Rajasthan",
        "PIN code?": "305001", "School phone": "9829012345", "Full name of the board": "RBSE",
        "Is this list right?": ["n", "y", "y"], "Type the classes": "LKG, UKG, Class 1",
        "Enter them again": "y", "How often": "1", "UPI ID?": "sunrise@sbi", "Tuition fee is the same": "y", "Tuition fee, in rupees": "30000",
        "Admission fee, in rupees": "5000", "Annual charges, in rupees": "0", "Examination fee, in rupees": "0",
        "Username?": "owner", "First name?": "Owner",
    }, passwords=["Sunrise-owner-2026", "Sunrise-owner-2026"])
    run()

    assert list(SchoolClass.objects.filter(is_active=True).values_list("code", flat=True)) == ["LKG", "UKG", "1"]
    assert not SchoolClass.objects.get(code="NUR").is_active
    assert SchoolProfile.get().short_code == "SS"
    session = AcademicSession.current()
    assert list(Installment.objects.filter(session=session).values_list("name", flat=True)) == ["Annual fee"]
    assert set(FeeAmount.objects.values_list("fee_head__code", flat=True)) == {"tuition", "admission"}
    assert FeeAmount.objects.count() == 6
