"""Client for the WhatsApp server in whatsapp-server/ (Blastup).

It runs on the same machine, reachable only on 127.0.0.1, and every call
carries WHATSAPP_API_KEY. Nothing else in LKMS talks to it.
"""

import json
import urllib.error
import urllib.request

from django.conf import settings


class WhatsAppError(Exception):
    """Sending failed. `retry` says whether trying again later may work."""

    def __init__(self, message, retry=True, offline=False):
        super().__init__(message)
        self.retry = retry
        self.offline = offline


def _call(method, path, body=None, timeout=None):
    if not settings.WHATSAPP_API_URL or not settings.WHATSAPP_API_KEY:
        raise WhatsAppError("WhatsApp server is not configured (WHATSAPP_API_URL / WHATSAPP_API_KEY).", offline=True)
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        settings.WHATSAPP_API_URL.rstrip("/") + path, data=data, method=method,
        headers={"X-API-Key": settings.WHATSAPP_API_KEY, "Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout or settings.WHATSAPP_TIMEOUT_SECONDS) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as err:
        try:
            detail = json.loads(err.read() or b"{}").get("error") or err.reason
        except ValueError:
            detail = err.reason
        if err.code == 503:
            raise WhatsAppError(f"WhatsApp is not connected: {detail}", offline=True) from err
        if err.code in (400, 422):
            raise WhatsAppError(f"Rejected: {detail}", retry=False) from err
        if err.code in (401, 403):
            raise WhatsAppError("The WhatsApp server refused the API key.", offline=True) from err
        raise WhatsAppError(f"WhatsApp server error {err.code}: {detail}") from err
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        raise WhatsAppError(f"Cannot reach the WhatsApp server: {getattr(err, 'reason', err)}", offline=True) from err


def send_text(phone, text):
    """Send a text to a 10-digit Indian mobile number. Returns the WhatsApp message id."""
    result = _call("POST", "/api/send/text", {"to": f"91{phone}", "text": text})
    return (result.get("data") or {}).get("messageId") or ""


def status():
    """Connection state of the school's WhatsApp number: {'state': 'connected' | 'qr_ready' | ..., 'phone': ...}."""
    data = _call("GET", "/api/whatsapp/status").get("data") or {}
    return {"state": data.get("status", "disconnected"), "phone": data.get("phone"), "name": data.get("pushName")}


def qr_code():
    """A data: URL of the QR code to link the school's phone, or None when there is none to scan."""
    try:
        return (_call("GET", "/api/whatsapp/qr").get("data") or {}).get("qr")
    except WhatsAppError as err:
        if "404" in str(err) or "QR not available" in str(err):
            return None
        raise


def reconnect():
    _call("POST", "/api/whatsapp/reconnect", {})
