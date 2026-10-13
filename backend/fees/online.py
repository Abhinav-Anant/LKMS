"""Online fee payments through Cashfree.

The browser never tells LKMS a payment succeeded. An order is marked paid
only from (a) a webhook whose signature checks out, or (b) LKMS asking
Cashfree directly for the order's payments. Both paths go through
`apply_gateway_payment`, which is idempotent.
"""

import json
import logging
import secrets
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core import audit

from . import cashfree, services
from .models import Invoice, OnlineOrder, Payment, PaymentIssue, WebhookEvent

logger = logging.getLogger("lkms.payments")

PAY_LINK_SALT = "lkms.fees.pay-link"
FINAL_STATUSES = {OnlineOrder.Status.PAID, OnlineOrder.Status.MISMATCH}


# ----- pay links -----

def make_pay_token(invoice):
    return signing.dumps({"i": invoice.pk}, salt=PAY_LINK_SALT, compress=True)


def invoice_from_token(token):
    max_age = settings.PAY_LINK_MAX_AGE_DAYS * 86400
    try:
        data = signing.loads(token, salt=PAY_LINK_SALT, max_age=max_age)
    except signing.BadSignature:
        return None
    return Invoice.objects.select_related("student", "session", "school_class", "installment").filter(pk=data.get("i")).first()


def pay_link(invoice):
    return f"{settings.FRONTEND_BASE_URL}/pay/{make_pay_token(invoice)}"


# ----- starting a payment -----

def _customer(invoice):
    student = invoice.student
    link = student.guardian_links.select_related("guardian").order_by("-is_primary_contact").first()
    guardian = link.guardian if link else None
    customer = {
        "customer_id": f"STU{student.pk}",
        "customer_phone": guardian.phone if guardian else "",
        "customer_name": (guardian.full_name if guardian else student.full_name)[:100],
    }
    if guardian and guardian.email:
        customer["customer_email"] = guardian.email
    return customer


def start_payment(request, invoice, token):
    """Create a Cashfree order for the invoice's current balance."""
    if invoice.status in (Invoice.Status.PAID, Invoice.Status.CANCELLED):
        raise ValidationError("There is nothing to pay on this invoice.")
    amount = invoice.balance
    if amount < 1:
        raise ValidationError("The balance is too small to pay online.")
    customer = _customer(invoice)
    if not customer["customer_phone"]:
        raise ValidationError("No parent mobile number on record. Please contact the school office.")

    order = OnlineOrder.objects.create(
        order_id=f"LK{invoice.pk}-{secrets.token_hex(6)}", invoice=invoice, amount=amount,
        created_by=request.user if request.user.is_authenticated else None,
    )
    notify_url = f"{settings.PUBLIC_API_BASE_URL}/api/v1/fees/cashfree/webhook/"
    data = cashfree.client().create_order(
        order_id=order.order_id,
        amount=amount,
        customer=customer,
        return_url=f"{settings.FRONTEND_BASE_URL}/pay/{token}?order_id={order.order_id}",
        # Cashfree accepts only https callback URLs; in development set the webhook in the dashboard instead.
        notify_url=notify_url if notify_url.startswith("https://") else None,
        note=f"{invoice.number} {invoice.student.admission_number}",
    )
    order.cf_order_id = str(data.get("cf_order_id", ""))
    order.payment_session_id = data.get("payment_session_id", "")
    order.save(update_fields=["cf_order_id", "payment_session_id"])
    audit.record(request, "fees.online_order_created", order, invoice=invoice.number, amount=str(amount))
    return order


# ----- confirming a payment -----

def _decimal(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return None


@transaction.atomic
def apply_gateway_payment(order_id, payment, source):
    """Apply one Cashfree payment entity to our order. Safe to call any number of times."""
    order = OnlineOrder.objects.select_for_update().select_related("invoice").filter(order_id=order_id).first()
    if order is None:
        PaymentIssue.objects.create(kind=PaymentIssue.Kind.UNKNOWN_ORDER, detail=f"{source}: order {order_id} not found")
        return None

    status = (payment.get("payment_status") or "").upper()
    order.last_checked_at = timezone.now()
    if order.status in FINAL_STATUSES:
        order.save(update_fields=["last_checked_at"])
        return order

    if status == "SUCCESS":
        amount = _decimal(payment.get("payment_amount"))
        currency = payment.get("payment_currency") or "INR"
        order.cf_payment_id = str(payment.get("cf_payment_id") or "")
        order.payment_group = str(payment.get("payment_group") or "")[:30]
        order.bank_reference = str(payment.get("bank_reference") or "")[:100]
        order.paid_at = parse_datetime(payment.get("payment_time") or "") or timezone.now()
        if amount != order.amount or currency != "INR":
            order.status = OnlineOrder.Status.MISMATCH
            order.status_note = f"Cashfree reports {currency} {amount}, order was INR {order.amount}"
            order.save()
            PaymentIssue.objects.create(kind=PaymentIssue.Kind.AMOUNT_MISMATCH, order=order, detail=f"{source}: {order.status_note}")
            logger.warning("Amount mismatch on %s: %s", order.order_id, order.status_note)
            return order
        order.status = OnlineOrder.Status.PAID
        order.status_note = f"Confirmed by {source}"
        order.save()
        services.record_payment(
            None, order.invoice, amount=amount, mode=Payment.Mode.ONLINE,
            paid_on=timezone.localdate(order.paid_at), reference=order.cf_payment_id, online_order=order,
        )
    elif status in ("FAILED", "USER_DROPPED", "CANCELLED", "VOID"):
        order.status = OnlineOrder.Status.FAILED
        order.status_note = f"{status.lower()} ({source})"
        order.save()
    else:
        order.save(update_fields=["last_checked_at"])
    return order


def sync_order(order):
    """Ask Cashfree for the order's state and apply it. Returns the refreshed order."""
    if order.status in FINAL_STATUSES:
        return order
    gateway = cashfree.client()
    payments = gateway.get_payments(order.order_id)
    success = next((p for p in payments if (p.get("payment_status") or "").upper() == "SUCCESS"), None)
    if success:
        return apply_gateway_payment(order.order_id, success, "status check")
    remote = gateway.get_order(order.order_id)
    remote_status = (remote.get("order_status") or "").upper()
    with transaction.atomic():
        order = OnlineOrder.objects.select_for_update().get(pk=order.pk)
        order.last_checked_at = timezone.now()
        if order.status == OnlineOrder.Status.CREATED and remote_status in ("EXPIRED", "TERMINATED"):
            order.status = OnlineOrder.Status.EXPIRED
            order.status_note = remote_status.lower()
        elif order.status == OnlineOrder.Status.CREATED and payments:
            latest = payments[0]
            if (latest.get("payment_status") or "").upper() in ("FAILED", "USER_DROPPED", "CANCELLED", "VOID"):
                order.status = OnlineOrder.Status.FAILED
                order.status_note = latest["payment_status"].lower()
        order.save()
    return order


# ----- webhook -----

PAYMENT_EVENTS = {"PAYMENT_SUCCESS_WEBHOOK", "PAYMENT_FAILED_WEBHOOK", "PAYMENT_USER_DROPPED_WEBHOOK"}


def handle_webhook(raw_body: bytes, timestamp: str, signature: str):
    """Store the call, check the signature, then apply it. Returns (http_status, message)."""
    event = WebhookEvent.objects.create(
        raw_body=raw_body.decode("utf-8", errors="replace"), timestamp=timestamp[:30], signature=signature[:200],
        signature_valid=cashfree.verify_signature(raw_body, timestamp, signature),
    )
    if not event.signature_valid:
        event.error = "bad signature"
        event.save(update_fields=["error"])
        logger.warning("Rejected Cashfree webhook %s: bad signature", event.pk)
        return 400, "invalid signature"
    try:
        payload = json.loads(raw_body)
        event.event_type = str(payload.get("type", ""))[:60]
        data = payload.get("data") or {}
        event.order_id = str((data.get("order") or {}).get("order_id", ""))[:45]
    except (ValueError, AttributeError):
        event.error = "body is not valid JSON"
        event.save(update_fields=["error"])
        return 400, "invalid body"

    if event.event_type in PAYMENT_EVENTS and event.order_id:
        apply_gateway_payment(event.order_id, data.get("payment") or {}, f"webhook {event.pk}")
    event.processed = True
    event.save(update_fields=["event_type", "order_id", "processed"])
    return 200, "ok"


# ----- reconciliation -----

def reconcile(since):
    """Compare recent orders with Cashfree. Returns counts for the report."""
    counts = {"checked": 0, "newly_paid": 0, "expired_or_failed": 0, "issues": 0, "errors": 0}
    gateway = cashfree.client()
    for order in OnlineOrder.objects.filter(created_at__gte=since).select_related("invoice"):
        counts["checked"] += 1
        before = order.status
        try:
            if order.status == OnlineOrder.Status.PAID:
                remote = gateway.get_order(order.order_id)
                remote_amount = _decimal(remote.get("order_amount"))
                if (remote.get("order_status") or "").upper() != "PAID" or remote_amount != order.amount:
                    PaymentIssue.objects.get_or_create(
                        kind=PaymentIssue.Kind.NOT_PAID_AT_GATEWAY, order=order, resolved=False,
                        defaults={"detail": f"Cashfree shows {remote.get('order_status')} INR {remote_amount}"},
                    )
                    counts["issues"] += 1
                continue
            order = sync_order(order)
        except cashfree.CashfreeError as exc:
            counts["errors"] += 1
            logger.error("Reconciliation could not check %s: %s", order.order_id, exc)
            continue
        if before != order.status:
            if order.status == OnlineOrder.Status.PAID:
                counts["newly_paid"] += 1
            elif order.status in (OnlineOrder.Status.EXPIRED, OnlineOrder.Status.FAILED):
                counts["expired_or_failed"] += 1
            elif order.status == OnlineOrder.Status.MISMATCH:
                counts["issues"] += 1
    return counts
