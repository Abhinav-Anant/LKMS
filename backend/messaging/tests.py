import json
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import as_user
from messaging import outbox, whatsapp
from messaging.models import OptOut, OutgoingMessage

pytestmark = pytest.mark.django_db
PHONE = "9829011111"
S = OutgoingMessage.Status


@pytest.fixture
def wa(settings, monkeypatch):
    """WhatsApp switched on, with a fake sender that records what it was asked to send."""
    settings.WHATSAPP_ENABLED = True
    settings.WHATSAPP_SEND_GAP_SECONDS = 0
    settings.WHATSAPP_QUIET_HOURS = (0, 0)
    settings.WHATSAPP_RATE_PER_MINUTE = 100
    settings.FRONTEND_BASE_URL = "https://school.example"
    sent, failures = [], []

    def fake_send(phone, text):
        if failures:
            raise failures.pop(0)
        sent.append((phone, text))
        return f"MSG{len(sent)}"

    monkeypatch.setattr(whatsapp, "send_text", fake_send)
    return {"sent": sent, "failures": failures}


def request_code():
    APIClient().post("/api/v1/auth/parent/request-code/", {"phone": PHONE}, format="json")


def test_messages_are_not_sent_while_whatsapp_is_off(school, settings):
    settings.WHATSAPP_ENABLED = False
    request_code()
    row = OutgoingMessage.objects.get()
    assert row.status == S.SKIPPED and row.text == "(sign-in code hidden)"
    assert outbox.send_due() == 0


def test_sign_in_code_is_sent_then_hidden_from_the_log(school, wa):
    request_code()
    assert outbox.send_due() == 1
    phone, text = wa["sent"][0]
    assert phone == PHONE and "sign-in code is" in text
    row = OutgoingMessage.objects.get()
    assert row.status == S.SENT and row.provider_message_id == "MSG1" and row.text == "(sign-in code hidden)"


def test_opted_out_numbers_get_codes_but_not_alerts(school, wa, client_for):
    OptOut.objects.create(phone=PHONE)
    client = as_user(school["class_teacher"])
    day = timezone.localdate()
    if day.weekday() == 6:
        pytest.skip("Sunday is not a school day")
    client.post("/api/v1/attendance/sheet/", {"section": school["section"].pk, "date": day.isoformat(),
                                              "records": [{"student": school["students"][0].pk, "status": "absent"}]}, format="json")
    request_code()
    outbox.send_due()
    assert [r.status for r in OutgoingMessage.objects.order_by("created_at")] == [S.SKIPPED, S.SENT]
    assert len(wa["sent"]) == 1


def test_errors_are_retried_with_backoff_then_marked_failed(school, wa, settings):
    settings.WHATSAPP_MAX_ATTEMPTS = 2
    wa["failures"].append(whatsapp.WhatsAppError("server error 500"))
    request_code()
    outbox.send_due()
    row = OutgoingMessage.objects.get()
    assert row.status == S.QUEUED and row.attempts == 1 and row.next_attempt_at > timezone.now() + timedelta(seconds=50)

    OutgoingMessage.objects.update(next_attempt_at=timezone.now())
    wa["failures"].append(whatsapp.WhatsAppError("server error 500"))
    outbox.send_due()
    row.refresh_from_db()
    assert row.status == S.FAILED and row.attempts == 2 and row.text == "(sign-in code hidden)"


def test_rejected_numbers_fail_at_once(school, wa):
    wa["failures"].append(whatsapp.WhatsAppError("Rejected: not on WhatsApp", retry=False))
    request_code()
    outbox.send_due()
    assert OutgoingMessage.objects.get().status == S.FAILED


def test_offline_server_keeps_messages_queued_without_using_attempts(school, wa):
    wa["failures"].append(whatsapp.WhatsAppError("not connected", offline=True))
    request_code()
    assert outbox.send_due() == 0
    row = OutgoingMessage.objects.get()
    assert row.status == S.QUEUED and row.attempts == 0 and "not connected" in row.last_error


def test_unsent_sign_in_codes_expire(school, wa):
    request_code()
    OutgoingMessage.objects.update(created_at=timezone.now() - timedelta(minutes=11))
    outbox.send_due()
    row = OutgoingMessage.objects.get()
    assert row.status == S.SKIPPED and not wa["sent"] and row.text == "(sign-in code hidden)"


def _alerts(n, phone=PHONE):
    now = timezone.now()
    OutgoingMessage.objects.bulk_create([
        OutgoingMessage(event="test", kind="alert", phone=phone, text=f"alert {i}", next_attempt_at=now) for i in range(n)
    ])


def test_sending_rate_is_limited_per_minute(db, wa, settings):
    settings.WHATSAPP_RATE_PER_MINUTE = 2
    _alerts(3, "9000000001")
    assert outbox.send_due() == 2
    assert outbox.send_due() == 0
    assert OutgoingMessage.objects.filter(status=S.QUEUED).count() == 1


def test_daily_limit_per_number(db, wa, settings):
    settings.WHATSAPP_DAILY_LIMIT_PER_NUMBER = 2
    _alerts(3)
    outbox.send_due()
    assert OutgoingMessage.objects.filter(status=S.SKIPPED, skip_reason__startswith="Daily limit").count() == 1


def test_alerts_wait_during_quiet_hours_but_codes_go(school, wa, settings):
    settings.WHATSAPP_QUIET_HOURS = (0, 24)
    _alerts(1, "9000000001")
    request_code()
    assert outbox.send_due() == 1
    assert wa["sent"][0][0] == PHONE
    assert OutgoingMessage.objects.filter(status=S.QUEUED, kind="alert").count() == 1


def test_absence_alert_only_for_today_and_only_once(school, wa):
    day = timezone.localdate()
    if day.weekday() == 6:
        pytest.skip("Sunday is not a school day")
    client = as_user(school["class_teacher"])
    riya = school["students"][0]
    body = {"section": school["section"].pk, "date": day.isoformat(), "records": [{"student": riya.pk, "status": "absent"}]}
    client.post("/api/v1/attendance/sheet/", body, format="json")
    client.post("/api/v1/attendance/sheet/", {**body, "records": [{"student": riya.pk, "status": "present"}]}, format="json")
    client.post("/api/v1/attendance/sheet/", body, format="json")
    rows = OutgoingMessage.objects.filter(event="attendance.absent")
    assert rows.count() == 1 and "Riya Verma was marked absent today" in rows[0].text and rows[0].phone == PHONE


def test_notice_goes_once_to_each_family(school, wa, client_for):
    principal = client_for("principal")
    response = principal.post("/api/v1/notices/", {"title": "PTM on Saturday", "body": "Parents meeting at 10 am.",
                                                   "send_whatsapp": True}, format="json")
    assert response.status_code == 201, response.data
    rows = OutgoingMessage.objects.filter(event="notice.published")
    # Riya and Kabir share their father's number.
    assert rows.count() == 1 and "PTM on Saturday" in rows[0].text
    principal.patch(f"/api/v1/notices/{response.data['id']}/", {"body": "Changed"}, format="json")
    assert OutgoingMessage.objects.filter(event="notice.published").count() == 1


def test_staff_only_notice_is_not_sent(school, wa, client_for):
    client_for("principal").post("/api/v1/notices/", {"title": "Staff meeting", "body": "x", "audience": "staff",
                                                      "send_whatsapp": True}, format="json")
    assert not OutgoingMessage.objects.exists()


def test_admission_messages(public, application_data, wa):
    response = public.post("/api/v1/admissions/public/apply/", application_data, format="json")
    assert response.status_code == 201
    row = OutgoingMessage.objects.get(event="admission.submitted")
    assert row.phone == "9829012345" and "https://school.example/track" in row.text


def test_payment_receipt_message(school, wa, client_for):
    from fees.models import Installment

    accountant = client_for("accountant")
    installment = Installment.objects.filter(session=school["session"]).first()
    accountant.post("/api/v1/fees/invoices/generate/", {"installment": installment.pk}, format="json")
    invoice = accountant.get("/api/v1/fees/invoices/").data["results"][0]
    accountant.post(f"/api/v1/fees/invoices/{invoice['id']}/pay/", {"amount": "500", "mode": "cash"}, format="json")
    row = OutgoingMessage.objects.get(event="fee.payment_received")
    assert "we received ₹500 for" in row.text and "Receipt number RCT-" in row.text


def test_a_broken_template_never_breaks_the_action(school, wa, monkeypatch):
    from messaging import templates

    monkeypatch.setitem(templates.BUILDERS, "parent_login_code", lambda ctx: 1 / 0)
    response = APIClient().post("/api/v1/auth/parent/request-code/", {"phone": PHONE}, format="json")
    assert response.status_code == 200


def test_staff_pages(school, wa, client_for, monkeypatch):
    monkeypatch.setattr(whatsapp, "status", lambda: {"state": "connected", "phone": "919829000000", "name": "LKS"})
    office = client_for("office")
    status = office.get("/api/v1/whatsapp/status/").data
    assert status["state"] == "connected" and status["enabled"]
    request_code()
    log = office.get("/api/v1/whatsapp/messages/").data["results"]
    assert log[0]["event"] == "parent_login_code"
    assert office.post("/api/v1/whatsapp/opt-outs/", {"phone": "+91 98290 22222", "note": "asked at PTM"}, format="json").status_code == 201
    assert OptOut.objects.filter(phone="9829022222").exists()
    assert office.get("/api/v1/whatsapp/qr/").status_code == 403
    assert as_user(school["class_teacher"]).get("/api/v1/whatsapp/messages/").status_code == 403


def test_failed_alert_can_be_retried(db, wa, client_for):
    _alerts(1)
    row = OutgoingMessage.objects.get()
    OutgoingMessage.objects.update(status=S.FAILED, attempts=5)
    response = client_for("office").post(f"/api/v1/whatsapp/messages/{row.pk}/retry/")
    assert response.status_code == 200 and response.data["status"] == "queued"


def test_parent_can_turn_alerts_off_and_on(school, client_for):
    code = client_for("office").post("/api/v1/auth/parent/issue-code/", {"phone": PHONE}, format="json").data["code"]
    tokens = APIClient().post("/api/v1/auth/parent/verify-code/", {"phone": PHONE, "code": code}, format="json").data
    parent = APIClient()
    parent.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert parent.get("/api/v1/parent/whatsapp/").data == {"whatsapp_alerts": True}
    assert parent.put("/api/v1/parent/whatsapp/", {"whatsapp_alerts": False}, format="json").data == {"whatsapp_alerts": False}
    assert OptOut.objects.filter(phone=PHONE).exists()
    parent.put("/api/v1/parent/whatsapp/", {"whatsapp_alerts": True}, format="json")
    assert not OptOut.objects.exists()


class _FakeBlastup(BaseHTTPRequestHandler):
    calls = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _FakeBlastup.calls.append((self.path, self.headers["X-API-Key"], body))
        if body["to"] == "910000000000":
            self._reply(400, {"success": False, "error": "Invalid number"})
        elif body["to"] == "919999999999":
            self._reply(503, {"success": False, "error": "WhatsApp is not connected"})
        else:
            self._reply(200, {"success": True, "data": {"messageId": "ABC123"}})

    def _reply(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def test_http_client_talks_to_the_blastup_api(settings):
    server = HTTPServer(("127.0.0.1", 0), _FakeBlastup)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        settings.WHATSAPP_API_URL = f"http://127.0.0.1:{server.server_port}"
        settings.WHATSAPP_API_KEY = "wa_test"
        assert whatsapp.send_text("9829011111", "hello") == "ABC123"
        assert _FakeBlastup.calls[-1] == ("/api/send/text", "wa_test", {"to": "919829011111", "text": "hello"})
        with pytest.raises(whatsapp.WhatsAppError) as bad:
            whatsapp.send_text("0000000000", "x")
        assert not bad.value.retry
        with pytest.raises(whatsapp.WhatsAppError) as offline:
            whatsapp.send_text("9999999999", "x")
        assert offline.value.offline
        settings.WHATSAPP_API_URL = "http://127.0.0.1:1"
        with pytest.raises(whatsapp.WhatsAppError) as down:
            whatsapp.send_text("9829011111", "x")
        assert down.value.offline
    finally:
        server.shutdown()
