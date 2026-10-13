import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from academics.models import AcademicSession, Enrollment, SchoolClass, Section
from conftest import png_file
from core.models import AuditLog
from fees import upi
from fees.models import Concession, FeeHead, Installment, Invoice, Payment, UpiSubmission
from students.models import Guardian, Student, StudentGuardian

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def frontend_url(settings):
    settings.FRONTEND_BASE_URL = "https://school.example"


@pytest.fixture
def current(seeded):
    return AcademicSession.current()


def make_student(session, school_class, name="Riya", admitted=None, number=None):
    section = Section.objects.get_or_create(session=session, school_class=school_class, name="A")[0]
    student = Student.objects.create(
        admission_number=number or f"S{Student.objects.count() + 1:04d}",
        admission_date=admitted or session.start_date - timedelta(days=400),
        admitted_in_class=school_class, first_name=name, last_name="Verma", date_of_birth=date(2018, 1, 1),
        gender="F", address_line="1 Main Road", city="Jaipur", district="Jaipur", pincode="302001",
    )
    guardian = Guardian.objects.create(full_name="Amit Verma", phone="9829011111")
    StudentGuardian.objects.create(student=student, guardian=guardian, relationship="father", is_primary_contact=True)
    Enrollment.objects.create(student=student, session=session, section=section, enrolled_on=session.start_date)
    return student


@pytest.fixture
def q1(current):
    return Installment.objects.get(session=current, name="Quarter 1")


@pytest.fixture
def class1():
    return SchoolClass.objects.get(code="1")


@pytest.fixture
def staff(client_for):
    return client_for("accountant")


def generate(client, installment):
    response = client.post("/api/v1/fees/invoices/generate/", {"installment": installment.pk}, format="json")
    assert response.status_code == 201, response.data
    return response.data


# ----- fee structure and invoices -----

def test_placeholder_fees_are_seeded(current, q1, class1):
    assert FeeHead.objects.filter(code="admission", new_students_only=True).exists()
    assert Installment.objects.filter(session=current).count() == 4
    assert q1.amounts.filter(school_class=class1).count() == 3  # tuition, admission, annual


def test_generate_invoices_charges_admission_fee_only_to_new_students(staff, current, q1, class1):
    old = make_student(current, class1, "Old")
    new = make_student(current, class1, "New", admitted=current.start_date + timedelta(days=5))
    result = generate(staff, q1)
    assert result["created"] == 2
    old_invoice = Invoice.objects.get(student=old)
    new_invoice = Invoice.objects.get(student=new)
    assert old_invoice.gross_amount == Decimal("7000")  # tuition 3000 + annual 4000
    assert new_invoice.gross_amount == Decimal("12000")  # plus admission 5000
    assert old_invoice.number.startswith(f"INV-{current.name}-")

    again = generate(staff, q1)
    assert again["created"] == 0 and again["skipped_existing"] == 2


def test_fee_structure_is_locked_once_invoices_exist(staff, current, q1, class1):
    make_student(current, class1)
    generate(staff, q1)
    tuition = FeeHead.objects.get(code="tuition")
    response = staff.post("/api/v1/fees/amounts/bulk/", {
        "installment": q1.pk, "amounts": [{"school_class": class1.pk, "fee_head": tuition.pk, "amount": "1"}],
    }, format="json")
    assert response.status_code == 403


def test_concession_needs_approval_and_updates_open_invoices(client_for, staff, current, q1, class1):
    student = make_student(current, class1)
    generate(staff, q1)
    office = client_for("office")
    tuition = FeeHead.objects.get(code="tuition")
    response = office.post("/api/v1/fees/concessions/", {
        "student": student.pk, "session": current.pk, "fee_head": tuition.pk, "kind": "percent", "value": "50",
        "reason": "Sibling",
    }, format="json")
    assert response.status_code == 201, response.data
    invoice = Invoice.objects.get(student=student)
    assert invoice.concession_amount == 0  # not approved yet

    concession_id = response.data["id"]
    assert office.post(f"/api/v1/fees/concessions/{concession_id}/decide/", {"approve": True}, format="json").status_code == 403
    principal = client_for("principal")
    response = principal.post(f"/api/v1/fees/concessions/{concession_id}/decide/", {"approve": True}, format="json")
    assert response.status_code == 200, response.data
    invoice.refresh_from_db()
    assert invoice.concession_amount == Decimal("1500")
    assert invoice.net_amount == Decimal("5500")


def test_full_concession_makes_invoice_paid(client_for, staff, current, q1, class1):
    student = make_student(current, class1)
    Concession.objects.create(student=student, session=current, kind="percent", value=100, reason="RTE", status="approved")
    generate(staff, q1)
    assert Invoice.objects.get(student=student).status == Invoice.Status.PAID


# ----- offline payments -----

def test_record_cash_payment_issues_receipt(staff, current, q1, class1):
    student = make_student(current, class1)
    generate(staff, q1)
    invoice = Invoice.objects.get(student=student)
    response = staff.post(f"/api/v1/fees/invoices/{invoice.pk}/pay/", {"amount": "2000", "mode": "cash"}, format="json")
    assert response.status_code == 201, response.data
    assert response.data["receipt_number"].startswith(f"RCT-{current.name}-")
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PARTLY_PAID and invoice.balance == Decimal("5000")

    receipt = staff.get(f"/api/v1/fees/payments/{response.data['id']}/receipt/")
    assert receipt.status_code == 200 and receipt["Content-Type"] == "application/pdf"
    assert receipt.content.startswith(b"%PDF")


def test_offline_payment_cannot_exceed_balance_and_cheque_needs_number(staff, current, q1, class1):
    student = make_student(current, class1)
    generate(staff, q1)
    invoice = Invoice.objects.get(student=student)
    url = f"/api/v1/fees/invoices/{invoice.pk}/pay/"
    assert staff.post(url, {"amount": "7000.01", "mode": "cash"}, format="json").status_code == 400
    response = staff.post(url, {"amount": "100", "mode": "cheque"}, format="json")
    assert response.status_code == 400 and "reference" in response.data


def test_office_and_teacher_permissions(client_for, staff, current, q1, class1):
    student = make_student(current, class1)
    generate(staff, q1)
    invoice = Invoice.objects.get(student=student)
    office = client_for("office")
    assert office.get("/api/v1/fees/invoices/").status_code == 200
    assert office.post(f"/api/v1/fees/invoices/{invoice.pk}/pay/", {"amount": "10", "mode": "cash"}, format="json").status_code == 403
    assert client_for("teacher").get("/api/v1/fees/invoices/").status_code == 403


def test_reverse_payment_restores_balance(client_for, staff, current, q1, class1):
    student = make_student(current, class1)
    generate(staff, q1)
    invoice = Invoice.objects.get(student=student)
    payment = staff.post(f"/api/v1/fees/invoices/{invoice.pk}/pay/", {"amount": "7000", "mode": "cash"}, format="json").data
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID
    assert staff.post(f"/api/v1/fees/payments/{payment['id']}/reverse/", {"reason": "x"}, format="json").status_code == 403
    response = client_for("principal").post(f"/api/v1/fees/payments/{payment['id']}/reverse/", {"reason": "Wrong student"}, format="json")
    assert response.status_code == 200
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.UNPAID and invoice.amount_paid == 0
    assert AuditLog.objects.filter(action="fees.payment_reversed").exists()


def test_reports(staff, current, q1, class1):
    student = make_student(current, class1)
    generate(staff, q1)
    invoice = Invoice.objects.get(student=student)
    staff.post(f"/api/v1/fees/invoices/{invoice.pk}/pay/", {"amount": "1000", "mode": "cash"}, format="json")
    daily = staff.get("/api/v1/fees/reports/daily-collection/").data
    assert Decimal(str(daily["total"])) == Decimal("1000") and daily["by_mode"][0]["mode"] == "cash"
    Invoice.objects.filter(pk=invoice.pk).update(due_date=timezone.localdate() - timedelta(days=1))
    defaulters = staff.get("/api/v1/fees/reports/defaulters/").data
    assert [row["number"] for row in defaulters] == [invoice.number]


# ----- UPI payments reported by parents -----

@pytest.fixture
def invoice(staff, current, q1, class1):
    student = make_student(current, class1)
    generate(staff, q1)
    return Invoice.objects.get(student=student)


def pay_url(invoice, suffix=""):
    return f"/api/v1/fees/public/pay/{upi.make_pay_token(invoice)}/{suffix}"


def report(public, invoice, utr="412345678901", amount=None, file=None, **extra):
    data = {
        "utr": utr, "amount": str(amount or invoice.balance), "paid_on": timezone.localdate().isoformat(),
        "screenshot": file or png_file("upi.png"), **extra,
    }
    return public.post(pay_url(invoice, "upi/"), data, format="multipart")


def test_pay_page_shows_school_upi_without_login(public, invoice):
    response = public.get(pay_url(invoice))
    assert response.status_code == 200
    assert response.data["upi_id"] == "8619190956@SBI"
    assert response.data["payee_name"] == "Lotus Kids Education Society"
    assert response.data["invoice"]["number"] == invoice.number
    assert "phone" not in json.dumps(response.data, default=str)
    assert public.get(f"/api/v1/fees/public/pay/{upi.make_pay_token(invoice)}x/").status_code == 404


def test_parent_report_waits_for_staff_and_does_not_mark_paid(public, invoice):
    response = report(public, invoice, utr="412345678901")
    assert response.status_code == 201, response.data
    assert Decimal(str(response.data["pending_amount"])) == invoice.balance
    assert response.data["submissions"][0]["status"] == "pending"
    invoice.refresh_from_db()
    assert invoice.amount_paid == 0 and invoice.status == Invoice.Status.UNPAID
    assert AuditLog.objects.filter(action="fees.upi_submitted").exists()


def test_same_transaction_id_cannot_be_sent_twice(public, invoice):
    assert report(public, invoice, utr="412345678901").status_code == 201
    again = report(public, invoice, utr="412345678901", amount=10)
    assert again.status_code == 400 and "utr" in again.data


def test_report_needs_a_real_image_or_pdf_and_valid_utr(public, invoice):
    fake = SimpleUploadedFile("receipt.png", b"not really an image", content_type="image/png")
    assert report(public, invoice, file=fake).status_code == 400
    assert report(public, invoice, utr="12 34").status_code == 400
    tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
    assert report(public, invoice, paid_on=tomorrow).status_code == 400


def test_staff_approve_records_payment_and_receipt(public, staff, invoice):
    report(public, invoice, utr="412345678901")
    submission = UpiSubmission.objects.get()
    assert staff.get(f"/api/v1/fees/upi-submissions/{submission.pk}/screenshot/").status_code == 200
    response = staff.post(f"/api/v1/fees/upi-submissions/{submission.pk}/approve/", {}, format="json")
    assert response.status_code == 200, response.data
    assert response.data["status"] == "approved" and response.data["receipt_number"].startswith("RCT-")
    payment = Payment.objects.get()
    assert payment.mode == "upi" and payment.reference == "412345678901"
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID

    page = public.get(pay_url(invoice)).data
    assert page["receipts"][0]["receipt_number"] == payment.receipt_number
    pdf = public.get(pay_url(invoice, f"receipts/{payment.receipt_number}/"))
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    # A transaction ID already receipted cannot be reported again.
    assert report(public, invoice, utr="412345678901").status_code == 400


def test_staff_can_approve_a_different_amount(public, staff, invoice):
    report(public, invoice, amount=7000)
    submission = UpiSubmission.objects.get()
    staff.post(f"/api/v1/fees/upi-submissions/{submission.pk}/approve/", {"amount": "5000"}, format="json")
    invoice.refresh_from_db()
    assert invoice.amount_paid == Decimal("5000") and invoice.status == Invoice.Status.PARTLY_PAID


def test_reject_with_reason_lets_parent_send_again(public, staff, invoice):
    report(public, invoice, utr="412345678901")
    submission = UpiSubmission.objects.get()
    assert staff.post(f"/api/v1/fees/upi-submissions/{submission.pk}/reject/", {}, format="json").status_code == 400
    response = staff.post(f"/api/v1/fees/upi-submissions/{submission.pk}/reject/", {"reason": "Not in bank statement"}, format="json")
    assert response.status_code == 200 and response.data["status"] == "rejected"
    assert staff.post(f"/api/v1/fees/upi-submissions/{submission.pk}/approve/", {}, format="json").status_code == 400
    page = public.get(pay_url(invoice)).data
    assert page["submissions"][0]["reject_reason"] == "Not in bank statement"
    assert report(public, invoice, utr="412345678901").status_code == 201


def test_office_can_see_but_not_approve_upi(public, client_for, invoice):
    report(public, invoice)
    submission = UpiSubmission.objects.get()
    office = client_for("office")
    assert office.get("/api/v1/fees/upi-submissions/?status=pending").data["count"] == 1
    assert office.post(f"/api/v1/fees/upi-submissions/{submission.pk}/approve/", {}, format="json").status_code == 403
    assert client_for("teacher").get("/api/v1/fees/upi-submissions/").status_code == 403


def test_paid_invoice_takes_no_more_reports(public, staff, invoice):
    staff.post(f"/api/v1/fees/invoices/{invoice.pk}/pay/", {"amount": str(invoice.balance), "mode": "cash"}, format="json")
    assert report(public, invoice).status_code == 400
