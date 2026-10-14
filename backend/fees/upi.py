"""Fees paid by parents to the school's UPI QR code.

The school has no payment gateway, so LKMS cannot see UPI payments itself.
Parents report the payment (transaction ID and a screenshot of the receipt)
from their pay link; a staff member checks it against the bank statement and
approves it, which records the payment and issues the school's receipt.
"""

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core import audit
from core.models import SchoolProfile
from core.notify import notify

from . import services
from .models import Invoice, Payment, UpiSubmission

PAY_LINK_SALT = "lkms.fees.pay-link"


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


def upi_details():
    school = SchoolProfile.get()
    return {"upi_id": school.payment_upi_id, "payee_name": school.payment_upi_name}


def pending_amount(invoice):
    return sum((s.amount for s in invoice.upi_submissions.filter(status=UpiSubmission.Status.PENDING)), 0)


# ----- parent reports a payment -----

def _utr_taken(utr):
    return (
        UpiSubmission.objects.filter(utr__iexact=utr).exclude(status=UpiSubmission.Status.REJECTED).exists()
        or Payment.objects.filter(reference__iexact=utr, mode=Payment.Mode.UPI, status=Payment.Status.COMPLETED).exists()
    )


def submit(request, invoice, *, amount, utr, paid_on, payer_name, screenshot, screenshot_type, ip):
    if invoice.status in (Invoice.Status.PAID, Invoice.Status.CANCELLED):
        raise ValidationError("There is nothing left to pay on this invoice.")
    if paid_on > timezone.localdate():
        raise ValidationError({"paid_on": "The payment date cannot be in the future."})
    if _utr_taken(utr):
        raise ValidationError({"utr": "This transaction ID has already been sent to the school."})
    try:
        with transaction.atomic():
            submission = UpiSubmission.objects.create(
                invoice=invoice, amount=amount, utr=utr, paid_on=paid_on, payer_name=payer_name,
                screenshot=screenshot, screenshot_type=screenshot_type, submitted_from=ip,
            )
    except IntegrityError as exc:
        raise ValidationError({"utr": "This transaction ID has already been sent to the school."}) from exc
    audit.record(request, "fees.upi_submitted", submission, invoice=invoice.number, amount=str(amount), utr=utr)
    notify("fee.upi_submitted", student=invoice.student, invoice=invoice.number, amount=amount, utr=utr)
    return submission


# ----- staff check it -----

@transaction.atomic
def approve(request, submission, amount=None):
    """Staff confirmed the money is in the bank: record it and issue a receipt."""
    submission = UpiSubmission.objects.select_for_update().get(pk=submission.pk)
    if submission.status != UpiSubmission.Status.PENDING:
        raise ValidationError("This payment has already been checked.")
    payment = services.record_payment(
        request, submission.invoice, amount=amount or submission.amount, mode=Payment.Mode.UPI,
        paid_on=submission.paid_on, reference=submission.utr,
    )
    submission.status = UpiSubmission.Status.APPROVED
    submission.payment = payment
    submission.reviewed_by = request.user
    submission.reviewed_at = timezone.now()
    submission.save()
    audit.record(request, "fees.upi_approved", submission, receipt=payment.receipt_number, amount=str(payment.amount))
    return submission


@transaction.atomic
def reject(request, submission, reason):
    submission = UpiSubmission.objects.select_for_update().get(pk=submission.pk)
    if submission.status != UpiSubmission.Status.PENDING:
        raise ValidationError("This payment has already been checked.")
    submission.status = UpiSubmission.Status.REJECTED
    submission.reject_reason = reason
    submission.reviewed_by = request.user
    submission.reviewed_at = timezone.now()
    submission.save()
    audit.record(request, "fees.upi_rejected", submission, reason=reason)
    notify("fee.upi_rejected", student=submission.invoice.student, invoice=submission.invoice.number, reason=reason)
    return submission
