from datetime import date
from decimal import Decimal

import pytest

from academics.models import Enrollment
from certificates.models import TransferCertificate
from certificates.words import date_words
from conftest import as_user, make_user
from core.models import AuditLog
from fees.models import Invoice
from messaging.models import OutgoingMessage
from students.models import Student

pytestmark = pytest.mark.django_db


def request_tc(client, student, **extra):
    return client.post("/api/v1/certificates/tc/", {
        "student": student.pk, "application_date": "2026-10-01", "leaving_date": "2026-10-10",
        "reason": "Family moving to Delhi", "last_exam_result": "Passed Class 1", **extra,
    }, format="json")


def test_date_of_birth_in_words():
    assert date_words(date(2019, 1, 10)) == "Tenth January Two Thousand Nineteen"
    assert date_words(date(2018, 12, 31)) == "Thirty First December Two Thousand Eighteen"
    assert date_words(date(2020, 2, 22)) == "Twenty Second February Two Thousand Twenty"


def test_office_requests_and_principal_issues(school, client_for, settings):
    settings.WHATSAPP_ENABLED = True
    riya = school["students"][0]
    office, principal = client_for("office"), client_for("principal")
    requested = request_tc(office, riya)
    assert requested.status_code == 201, requested.data
    tc_id = requested.data["id"]
    assert office.post(f"/api/v1/certificates/tc/{tc_id}/issue/", {}, format="json").status_code == 403
    assert office.get(f"/api/v1/certificates/tc/{tc_id}/pdf/").status_code == 400  # not issued yet

    issued = principal.post(f"/api/v1/certificates/tc/{tc_id}/issue/", {}, format="json")
    assert issued.status_code == 200, issued.data
    assert issued.data["status"] == "issued" and issued.data["number"] == f"TC/{school['session'].name}/0001"
    riya.refresh_from_db()
    assert riya.status == Student.Status.TC_ISSUED
    assert Enrollment.objects.get(student=riya).status == Enrollment.Status.LEFT
    tc = TransferCertificate.objects.get()
    assert tc.details["father_name"] == "Amit Verma" and tc.details["last_class"] == "Class 1"
    assert OutgoingMessage.objects.filter(event="tc.issued").count() == 1
    assert AuditLog.objects.filter(action="tc.issued").exists()

    pdf = office.get(f"/api/v1/certificates/tc/{tc_id}/pdf/")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    # Issued TCs cannot be edited.
    assert office.patch(f"/api/v1/certificates/tc/{tc_id}/", {"reason": "x"}, format="json").status_code == 400


def test_unpaid_fees_block_the_tc_unless_the_principal_gives_a_reason(school, client_for):
    riya = school["students"][0]
    Invoice.objects.create(number="INV-1", student=riya, session=school["session"],
                           school_class=school["section"].school_class, due_date=date(2026, 7, 1),
                           gross_amount=Decimal("2500"))
    principal = client_for("principal")
    tc_id = request_tc(principal, riya).data["id"]
    blocked = principal.post(f"/api/v1/certificates/tc/{tc_id}/issue/", {}, format="json")
    assert blocked.status_code == 400 and blocked.data["fees_due"] == "2500.00"
    assert TransferCertificate.objects.get().number is None
    waived = principal.post(f"/api/v1/certificates/tc/{tc_id}/issue/", {"dues_waived_reason": "Hardship"}, format="json")
    assert waived.status_code == 200
    assert waived.data["fees_due"] == "2500.00" and waived.data["dues_waived_reason"] == "Hardship"


def test_one_tc_per_student_and_cancelling_restores_the_student(school, client_for):
    riya, kabir = school["students"]
    principal = client_for("principal")
    first = request_tc(principal, riya).data["id"]
    assert request_tc(principal, riya).status_code == 400
    principal.post(f"/api/v1/certificates/tc/{first}/issue/", {}, format="json")
    cancelled = principal.post(f"/api/v1/certificates/tc/{first}/cancel/", {"reason": "Issued by mistake"}, format="json")
    assert cancelled.status_code == 200 and cancelled.data["status"] == "cancelled"
    riya.refresh_from_db()
    assert riya.status == Student.Status.ACTIVE
    assert Enrollment.objects.get(student=riya).status == Enrollment.Status.ACTIVE
    # The cancelled number stays used: the next TC gets 0002.
    second = request_tc(principal, kabir).data["id"]
    issued = principal.post(f"/api/v1/certificates/tc/{second}/issue/", {}, format="json")
    assert issued.data["number"].endswith("/0002")


def test_office_can_withdraw_a_request_but_not_an_issued_tc(school, client_for):
    office, principal = client_for("office"), client_for("principal")
    tc_id = request_tc(office, school["students"][0]).data["id"]
    principal.post(f"/api/v1/certificates/tc/{tc_id}/issue/", {}, format="json")
    assert office.post(f"/api/v1/certificates/tc/{tc_id}/cancel/", {"reason": "x"}, format="json").status_code == 403
    other = request_tc(office, school["students"][1]).data["id"]
    assert office.post(f"/api/v1/certificates/tc/{other}/cancel/", {"reason": "Parent changed mind"},
                       format="json").status_code == 200


def test_teachers_and_accountants_cannot_see_tcs(school):
    assert as_user(school["class_teacher"]).get("/api/v1/certificates/tc/").status_code == 403
    assert as_user(make_user("accountant")).get("/api/v1/certificates/tc/").status_code == 403
