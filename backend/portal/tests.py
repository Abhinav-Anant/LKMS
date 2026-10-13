import logging
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from academics.models import PeriodSlot, TimetableEntry
from assessments.models import Assessment, Mark
from attendance.models import AttendanceRecord
from conftest import as_user, make_user
from notices.models import Notice
from users.models import LoginCode, User

pytestmark = pytest.mark.django_db
PHONE = "9829011111"


def code_from_log(caplog):
    for record in caplog.records:
        if "parent_login_code" in record.getMessage():
            return record.getMessage().split("'code': '")[1][:6]
    raise AssertionError("no code was sent")


def sign_in(caplog, phone=PHONE):
    client = APIClient()
    with caplog.at_level(logging.INFO, logger="lkms.notify"):
        assert client.post("/api/v1/auth/parent/request-code/", {"phone": phone}, format="json").status_code == 200
    response = client.post("/api/v1/auth/parent/verify-code/", {"phone": phone, "code": code_from_log(caplog)}, format="json")
    assert response.status_code == 200, response.data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client, response.data


def test_parent_signs_in_with_a_code_and_sees_both_children(school, caplog, settings):
    settings.DEBUG = True
    client, data = sign_in(caplog, "+91 98290 11111")
    assert data["user"]["role"] == "parent" and data["user"]["capabilities"] == []
    children = client.get("/api/v1/parent/children/").data
    assert sorted(c["full_name"] for c in children) == ["Kabir Verma", "Riya Verma"]
    assert children[0]["class_label"] == "Class 1 A" and children[0]["class_teacher"] == "ct"
    school["father"].refresh_from_db()
    assert school["father"].user.username == f"parent-{PHONE}"


def test_unknown_number_gets_the_same_answer_and_no_code(school, caplog):
    with caplog.at_level(logging.INFO, logger="lkms.notify"):
        known = APIClient().post("/api/v1/auth/parent/request-code/", {"phone": PHONE}, format="json")
        unknown = APIClient().post("/api/v1/auth/parent/request-code/", {"phone": "9000000000"}, format="json")
    assert known.data == unknown.data
    assert LoginCode.objects.filter(phone="9000000000").count() == 0


def test_codes_are_hidden_from_production_logs(school, caplog, settings):
    settings.DEBUG = False
    with caplog.at_level(logging.INFO, logger="lkms.notify"):
        APIClient().post("/api/v1/auth/parent/request-code/", {"phone": PHONE}, format="json")
    assert "'code': '***'" in caplog.text


def test_wrong_codes_lock_the_code_after_five_tries(school, caplog, settings):
    settings.DEBUG = True
    client = APIClient()
    with caplog.at_level(logging.INFO, logger="lkms.notify"):
        client.post("/api/v1/auth/parent/request-code/", {"phone": PHONE}, format="json")
    right = code_from_log(caplog)
    wrong = "000000" if right != "000000" else "111111"
    for _ in range(5):
        assert client.post("/api/v1/auth/parent/verify-code/", {"phone": PHONE, "code": wrong}, format="json").status_code == 400
    assert client.post("/api/v1/auth/parent/verify-code/", {"phone": PHONE, "code": right}, format="json").status_code == 400


def test_code_works_once_and_expires(school, client_for):
    office = client_for("office")
    issued = office.post("/api/v1/auth/parent/issue-code/", {"phone": PHONE}, format="json")
    assert issued.status_code == 200 and len(issued.data["children"]) == 2
    code = issued.data["code"]
    assert APIClient().post("/api/v1/auth/parent/verify-code/", {"phone": PHONE, "code": code}, format="json").status_code == 200
    assert APIClient().post("/api/v1/auth/parent/verify-code/", {"phone": PHONE, "code": code}, format="json").status_code == 400

    code = office.post("/api/v1/auth/parent/issue-code/", {"phone": PHONE}, format="json").data["code"]
    LoginCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert APIClient().post("/api/v1/auth/parent/verify-code/", {"phone": PHONE, "code": code}, format="json").status_code == 400


def test_teachers_cannot_issue_parent_codes(school):
    response = as_user(school["class_teacher"]).post("/api/v1/auth/parent/issue-code/", {"phone": PHONE}, format="json")
    assert response.status_code == 403


def test_parent_cannot_use_staff_pages_or_other_children(school, caplog, settings):
    settings.DEBUG = True
    client, _ = sign_in(caplog)
    assert client.get("/api/v1/students/").status_code == 403
    assert client.get("/api/v1/fees/invoices/").status_code == 403
    other = make_user("parent", "parent-9000000000")
    other.phone = "9000000000"
    other.save()
    stranger = as_user(other)
    assert stranger.get(f"/api/v1/parent/children/{school['students'][0].pk}/attendance/").status_code == 404


def test_parent_sees_attendance_published_marks_timetable_and_notices(school, caplog, settings):
    settings.DEBUG = True
    client, _ = sign_in(caplog)
    riya = school["students"][0]
    today = timezone.localdate()
    AttendanceRecord.objects.create(student=riya, section=school["section"], date=today, status="absent")
    attendance = client.get(f"/api/v1/parent/children/{riya.pk}/attendance/").data
    assert attendance["absent"] == 1 and attendance["percentage"] == 0.0

    draft = Assessment.objects.create(section=school["section"], subject=school["maths"], name="UT1", date=today, max_marks=20)
    Mark.objects.create(assessment=draft, student=riya, marks=15)
    assert client.get(f"/api/v1/parent/children/{riya.pk}/marks/").data == []
    draft.is_published = True
    draft.save()
    assert client.get(f"/api/v1/parent/children/{riya.pk}/marks/").data[0]["marks"] == "15.00"

    TimetableEntry.objects.create(section=school["section"], weekday=1, period=PeriodSlot.objects.get(number=1),
                                  subject=school["maths"], teacher=school["maths_teacher"])
    assert len(client.get(f"/api/v1/parent/children/{riya.pk}/timetable/").data) == 1

    Notice.objects.create(title="All", body="x", audience="everyone", published_at=timezone.now())
    Notice.objects.create(title="Staff", body="x", audience="staff", published_at=timezone.now())
    elsewhere = Notice.objects.create(title="Other class", body="x", audience="parents", published_at=timezone.now())
    elsewhere.sections.add(school["section"].__class__.objects.exclude(pk=school["section"].pk).first())
    mine = Notice.objects.create(title="Class 1 A", body="x", audience="parents", published_at=timezone.now())
    mine.sections.add(school["section"])
    titles = {n["title"] for n in client.get("/api/v1/parent/notices/").data}
    assert titles == {"All", "Class 1 A"}


def test_parent_fees_show_pay_link_and_receipts(school, caplog, settings, client_for):
    from fees.models import Installment

    settings.DEBUG = True
    settings.FRONTEND_BASE_URL = "https://school.example"
    accountant = client_for("accountant")
    installment = Installment.objects.filter(session=school["session"]).first()
    assert accountant.post("/api/v1/fees/invoices/generate/", {"installment": installment.pk}, format="json").status_code == 201
    riya = school["students"][0]
    client, _ = sign_in(caplog)
    fees = client.get(f"/api/v1/parent/children/{riya.pk}/fees/").data
    invoice = fees["invoices"][0]
    assert invoice["pay_link"].startswith("https://school.example/pay/")
    accountant.post(f"/api/v1/fees/invoices/{invoice['id']}/pay/", {"amount": "100", "mode": "cash"}, format="json")
    payment = client.get(f"/api/v1/parent/children/{riya.pk}/fees/").data["payments"][0]
    receipt = client.get(f"/api/v1/parent/children/{riya.pk}/receipts/{payment['id']}/")
    assert receipt.status_code == 200 and receipt["Content-Type"] == "application/pdf"


def test_principal_dashboard(school, client_for):
    data = client_for("principal").get("/api/v1/reports/dashboard/").data
    assert data["students_total"] == 2
    assert {"name": "Class 1", "students": 2} in data["students_by_class"]
    assert "Class 1 A" in data["attendance_today"]["sections_not_marked"]
    assert client_for("accountant").get("/api/v1/reports/dashboard/").status_code == 403


def test_parent_accounts_cannot_use_staff_login(school, client_for):
    client_for("office").post("/api/v1/auth/parent/issue-code/", {"phone": PHONE}, format="json")
    user = User.objects.filter(role="parent").first()
    assert user is None or not user.has_usable_password()
