import base64
import hashlib
import hmac
import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from academics.models import AcademicSession, Enrollment, SchoolClass, Section
from core.models import AuditLog
from fees import cashfree, online
from fees.models import Concession, FeeHead, Installment, Invoice, OnlineOrder, Payment, PaymentIssue, WebhookEvent
from students.models import Guardian, Student, StudentGuardian

pytestmark = pytest.mark.django_db

SECRET = "test-cashfree-secret"


@pytest.fixture(autouse=True)
def cashfree_keys(settings):
    settings.CASHFREE_CLIENT_ID = "test-app-id"
    settings.CASHFREE_CLIENT_SECRET = SECRET
    settings.CASHFREE_ENV = "sandbox"
    settings.FRONTEND_BASE_URL = "https://school.example"
    settings.PUBLIC_API_BASE_URL = "https://school.example"


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


# ----- online payments -----

class FakeCashfree:
    def __init__(self):
        self.orders = {}
        self.payments = {}

    def create_order(self, *, order_id, amount, customer, return_url, notify_url=None, note=""):
        self.orders[order_id] = {"order_id": order_id, "order_amount": float(amount), "order_status": "ACTIVE"}
        self.created = {"customer": customer, "return_url": return_url, "notify_url": notify_url}
        return {"cf_order_id": 123, "payment_session_id": f"session_{order_id}", "order_status": "ACTIVE"}

    def get_order(self, order_id):
        return self.orders[order_id]

    def get_payments(self, order_id):
        return self.payments.get(order_id, [])

    def pay(self, order_id, amount=None):
        order = self.orders[order_id]
        order["order_status"] = "PAID"
        payment = {
            "cf_payment_id": "987654", "order_id": order_id, "payment_status": "SUCCESS",
            "payment_amount": amount if amount is not None else order["order_amount"], "payment_currency": "INR",
            "payment_group": "upi", "bank_reference": "UTR1", "payment_time": "2026-10-13T10:00:00+05:30",
        }
        self.payments[order_id] = [payment]
        return payment


@pytest.fixture
def gateway(monkeypatch):
    fake = FakeCashfree()
    monkeypatch.setattr(cashfree, "client", lambda: fake)
    return fake


@pytest.fixture
def invoice(staff, current, q1, class1):
    student = make_student(current, class1)
    generate(staff, q1)
    return Invoice.objects.get(student=student)


def start(public, invoice):
    token = online.make_pay_token(invoice)
    response = public.post(f"/api/v1/fees/public/pay/{token}/start/")
    assert response.status_code == 200, response.data
    return token, response.data


def signed(body: dict, timestamp="1760000000"):
    raw = json.dumps(body).encode()
    signature = base64.b64encode(hmac.new(SECRET.encode(), timestamp.encode() + raw, hashlib.sha256).digest()).decode()
    return raw, {"HTTP_X_WEBHOOK_TIMESTAMP": timestamp, "HTTP_X_WEBHOOK_SIGNATURE": signature}


def webhook_body(payment, order_amount, event="PAYMENT_SUCCESS_WEBHOOK"):
    return {"data": {"order": {"order_id": payment["order_id"], "order_amount": order_amount}, "payment": payment}, "type": event}


def test_pay_page_shows_invoice_without_login(public, invoice):
    token = online.make_pay_token(invoice)
    response = public.get(f"/api/v1/fees/public/pay/{token}/")
    assert response.status_code == 200
    assert response.data["invoice"]["number"] == invoice.number
    assert "phone" not in json.dumps(response.data)
    assert public.get(f"/api/v1/fees/public/pay/{token}x/").status_code == 404


def test_start_payment_creates_order_for_balance(public, invoice, gateway):
    token, data = start(public, invoice)
    order = OnlineOrder.objects.get(order_id=data["order_id"])
    assert order.amount == invoice.balance and order.status == OnlineOrder.Status.CREATED
    assert data["payment_session_id"] == f"session_{order.order_id}" and data["mode"] == "sandbox"
    assert gateway.created["customer"]["customer_phone"] == "9829011111"
    assert gateway.created["return_url"].endswith(f"/pay/{token}?order_id={order.order_id}")
    assert gateway.created["notify_url"] == "https://school.example/api/v1/fees/cashfree/webhook/"


def test_return_page_does_not_trust_browser(public, invoice, gateway):
    token, data = start(public, invoice)
    # Parent comes back but Cashfree has no successful payment: still waiting.
    response = public.get(f"/api/v1/fees/public/pay/{token}/orders/{data['order_id']}/")
    assert response.data["status"] == "created"
    invoice.refresh_from_db()
    assert invoice.amount_paid == 0

    gateway.pay(data["order_id"])
    response = public.get(f"/api/v1/fees/public/pay/{token}/orders/{data['order_id']}/")
    assert response.data["status"] == "paid" and response.data["receipt_number"]
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID
    pdf = public.get(f"/api/v1/fees/public/pay/{token}/receipts/{response.data['receipt_number']}/")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_signed_webhook_marks_paid_once(public, invoice, gateway):
    _, data = start(public, invoice)
    payment = gateway.pay(data["order_id"])
    raw, headers = signed(webhook_body(payment, float(invoice.balance)))
    for _ in range(2):  # Cashfree retries; the second call must not pay twice
        response = public.generic("POST", "/api/v1/fees/cashfree/webhook/", raw, content_type="application/json", **headers)
        assert response.status_code == 200
    assert Payment.objects.filter(invoice=invoice, mode="online").count() == 1
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID
    assert WebhookEvent.objects.filter(signature_valid=True, processed=True).count() == 2


def test_webhook_with_bad_signature_is_rejected(public, invoice, gateway):
    _, data = start(public, invoice)
    payment = gateway.pay(data["order_id"])
    raw, headers = signed(webhook_body(payment, float(invoice.balance)))
    tampered = raw.replace(b'"SUCCESS"', b'"SUCCESS" ')
    response = public.generic("POST", "/api/v1/fees/cashfree/webhook/", tampered, content_type="application/json", **headers)
    assert response.status_code == 400
    missing = public.generic("POST", "/api/v1/fees/cashfree/webhook/", raw, content_type="application/json")
    assert missing.status_code == 400
    invoice.refresh_from_db()
    assert invoice.amount_paid == 0
    assert WebhookEvent.objects.filter(signature_valid=False).count() == 2


def test_wrong_amount_is_flagged_not_credited(public, invoice, gateway):
    _, data = start(public, invoice)
    payment = gateway.pay(data["order_id"], amount=1)
    raw, headers = signed(webhook_body(payment, 1))
    public.generic("POST", "/api/v1/fees/cashfree/webhook/", raw, content_type="application/json", **headers)
    order = OnlineOrder.objects.get(order_id=data["order_id"])
    assert order.status == OnlineOrder.Status.MISMATCH
    assert PaymentIssue.objects.filter(kind="amount_mismatch", order=order).exists()
    invoice.refresh_from_db()
    assert invoice.amount_paid == 0


def test_failed_payment_webhook(public, invoice, gateway):
    _, data = start(public, invoice)
    payment = {"order_id": data["order_id"], "payment_status": "FAILED", "payment_amount": float(invoice.balance)}
    raw, headers = signed(webhook_body(payment, float(invoice.balance), "PAYMENT_FAILED_WEBHOOK"))
    public.generic("POST", "/api/v1/fees/cashfree/webhook/", raw, content_type="application/json", **headers)
    assert OnlineOrder.objects.get(order_id=data["order_id"]).status == OnlineOrder.Status.FAILED


def test_online_payment_after_office_payment_is_flagged_as_overpaid(public, staff, invoice, gateway):
    _, data = start(public, invoice)
    staff.post(f"/api/v1/fees/invoices/{invoice.pk}/pay/", {"amount": str(invoice.balance), "mode": "cash"}, format="json")
    gateway.pay(data["order_id"])
    online.sync_order(OnlineOrder.objects.get(order_id=data["order_id"]))
    assert PaymentIssue.objects.filter(kind="overpaid").exists()


def test_reconciliation_picks_up_missed_webhook(public, invoice, gateway):
    _, data = start(public, invoice)
    gateway.pay(data["order_id"])  # webhook never arrived
    counts = online.reconcile(timezone.now() - timedelta(days=1))
    assert counts["newly_paid"] == 1
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID

    # Cashfree later disagrees with what we recorded: flagged for a person.
    gateway.orders[data["order_id"]]["order_status"] = "ACTIVE"
    counts = online.reconcile(timezone.now() - timedelta(days=1))
    assert counts["issues"] == 1
    assert PaymentIssue.objects.filter(kind="not_paid_at_gateway").exists()


def test_signature_helper_accepts_documented_forms():
    raw, ts = b'{"a":1}', "123"
    plain = base64.b64encode(hmac.new(SECRET.encode(), ts.encode() + raw, hashlib.sha256).digest()).decode()
    dotted = base64.b64encode(hmac.new(SECRET.encode(), ts.encode() + b"." + raw, hashlib.sha256).digest()).decode()
    assert cashfree.verify_signature(raw, ts, plain)
    assert cashfree.verify_signature(raw, ts, dotted)
    assert not cashfree.verify_signature(raw, "124", plain)
    assert not cashfree.verify_signature(raw, ts, "")
