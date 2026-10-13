"""Thin client for the Cashfree Payment Gateway API.

Only the calls LKMS needs: create an order, read an order and its payments,
and check a webhook signature. Credentials come from settings (environment).
API reference: https://www.cashfree.com/docs/api-reference/payments/latest
"""

import base64
import hashlib
import hmac
import uuid

import requests
from django.conf import settings

BASE_URLS = {
    "sandbox": "https://sandbox.cashfree.com/pg",
    "production": "https://api.cashfree.com/pg",
}


class CashfreeError(Exception):
    def __init__(self, message, status=None, data=None):
        super().__init__(message)
        self.status = status
        self.data = data


def is_configured():
    return bool(settings.CASHFREE_CLIENT_ID and settings.CASHFREE_CLIENT_SECRET)


class CashfreeClient:
    timeout = 15

    def __init__(self):
        if not is_configured():
            raise CashfreeError("Online payments are not set up (Cashfree keys missing).")
        self.base_url = BASE_URLS[settings.CASHFREE_ENV]

    def _headers(self):
        return {
            "x-client-id": settings.CASHFREE_CLIENT_ID,
            "x-client-secret": settings.CASHFREE_CLIENT_SECRET,
            "x-api-version": settings.CASHFREE_API_VERSION,
            "x-request-id": uuid.uuid4().hex,
            "Accept": "application/json",
        }

    def _call(self, method, path, **kwargs):
        headers = self._headers()
        if method == "POST":
            headers["x-idempotency-key"] = str(uuid.uuid4())
        try:
            response = requests.request(method, f"{self.base_url}{path}", headers=headers, timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise CashfreeError(f"Could not reach Cashfree: {exc.__class__.__name__}") from exc
        try:
            data = response.json()
        except ValueError:
            data = None
        if response.status_code >= 400:
            message = (data or {}).get("message") if isinstance(data, dict) else None
            raise CashfreeError(message or f"Cashfree returned {response.status_code}", response.status_code, data)
        return data

    def create_order(self, *, order_id, amount, customer, return_url, notify_url=None, note=""):
        body = {
            "order_id": order_id,
            "order_amount": float(amount),
            "order_currency": "INR",
            "customer_details": customer,
            "order_meta": {"return_url": return_url},
            "order_note": note[:200],
        }
        if notify_url:
            body["order_meta"]["notify_url"] = notify_url
        return self._call("POST", "/orders", json=body)

    def get_order(self, order_id):
        return self._call("GET", f"/orders/{order_id}")

    def get_payments(self, order_id):
        return self._call("GET", f"/orders/{order_id}/payments") or []


def client():
    """Factory so tests can swap in a fake."""
    return CashfreeClient()


def _sign(message: bytes) -> str:
    digest = hmac.new(settings.CASHFREE_CLIENT_SECRET.encode(), message, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def verify_signature(raw_body: bytes, timestamp: str, signature: str) -> bool:
    """Base64(HMAC-SHA256(timestamp + raw body, secret key)), compared in constant time.

    Cashfree's docs show the signed string both as timestamp+body and as
    timestamp.body, so either form is accepted; both need the secret key.
    """
    if not (settings.CASHFREE_CLIENT_SECRET and timestamp and signature):
        return False
    ts = timestamp.encode()
    for message in (ts + raw_body, ts + b"." + raw_body):
        if hmac.compare_digest(_sign(message), signature):
            return True
    return False
