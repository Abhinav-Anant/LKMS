"""Fee rules: building invoices, applying concessions, recording and reversing payments."""

from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from academics.models import Enrollment
from core import audit
from core.models import Counter
from core.notify import notify

from .models import Concession, FeeAmount, Invoice, InvoiceLine, Payment, PaymentIssue

ZERO = Decimal("0")
PAISA = Decimal("0.01")


def _money(value):
    return Decimal(value).quantize(PAISA, rounding=ROUND_HALF_UP)


def next_number(prefix, session):
    """e.g. INV-2026-27-00001; numbers run per session and never repeat."""
    value = Counter.take(f"{prefix}:{session.pk}")
    return f"{prefix}-{session.name}-{value:05d}"


# ----- concessions -----

def concession_for_lines(lines, concessions):
    """Work out concession per line. `lines` is a list of (fee_head, amount)."""
    result = [ZERO] * len(lines)
    for concession in concessions:
        matching = [i for i, (head, _) in enumerate(lines) if concession.fee_head_id in (None, head.pk)]
        if concession.kind == Concession.Kind.PERCENT:
            rate = min(concession.value, Decimal("100")) / 100
            for i in matching:
                result[i] += _money(lines[i][1] * rate)
        else:
            remaining = concession.value
            for i in matching:
                take = min(remaining, lines[i][1] - result[i])
                result[i] += take
                remaining -= take
    # Never give more off a line than the line is worth.
    return [min(off, amount) for off, (_, amount) in zip(result, lines)]


def approved_concessions(student, session):
    return list(Concession.objects.filter(student=student, session=session, status=Concession.Status.APPROVED))


def apply_concessions(invoice):
    """Recalculate an open invoice's concessions; the net amount never drops below what was already paid."""
    lines = list(invoice.lines.select_related("fee_head"))
    offs = concession_for_lines([(line.fee_head, line.amount) for line in lines], approved_concessions(invoice.student, invoice.session))
    room = invoice.gross_amount - invoice.amount_paid
    for line, off in zip(lines, offs):
        off = max(min(off, room), ZERO)
        room -= off
        if line.concession != off:
            line.concession = off
            line.save(update_fields=["concession"])
    invoice.concession_amount = sum((line.concession for line in lines), ZERO)
    invoice.refresh_status()
    invoice.save(update_fields=["concession_amount", "status", "updated_at"])


@transaction.atomic
def request_concession(request, **data):
    concession = Concession.objects.create(requested_by=request.user, **data)
    audit.record(request, "fees.concession_requested", concession, reason=concession.reason)
    return concession


@transaction.atomic
def decide_concession(request, concession, approve, note=""):
    if concession.status != Concession.Status.PENDING:
        raise ValidationError("This concession has already been decided.")
    concession.status = Concession.Status.APPROVED if approve else Concession.Status.REJECTED
    concession.decided_by = request.user
    concession.decided_at = timezone.now()
    concession.decision_note = note
    concession.save()
    if approve:
        _reapply_open_invoices(concession)
    audit.record(request, f"fees.concession_{concession.status}", concession, note=note)
    return concession


@transaction.atomic
def cancel_concession(request, concession, note=""):
    if concession.status not in (Concession.Status.PENDING, Concession.Status.APPROVED):
        raise ValidationError("Only pending or approved concessions can be cancelled.")
    was_approved = concession.status == Concession.Status.APPROVED
    concession.status = Concession.Status.CANCELLED
    concession.decision_note = note
    concession.save(update_fields=["status", "decision_note"])
    if was_approved:
        _reapply_open_invoices(concession)
    audit.record(request, "fees.concession_cancelled", concession, note=note)


def _reapply_open_invoices(concession):
    open_invoices = Invoice.objects.select_for_update().filter(
        student=concession.student, session=concession.session,
        status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTLY_PAID],
    )
    for invoice in open_invoices:
        apply_concessions(invoice)


# ----- invoices -----

def _is_new_student(student, session):
    return session.start_date <= student.admission_date <= session.end_date


@transaction.atomic
def generate_invoices(request, installment, class_ids=None):
    """Create invoices for every student studying in the installment's session.

    Students who already have a live invoice for this installment are skipped,
    so running it again only picks up newly admitted students.
    """
    session = installment.session
    enrollments = (
        Enrollment.objects.filter(session=session, status=Enrollment.Status.ACTIVE)
        .select_related("student", "section__school_class")
        .order_by("section__school_class__order", "student__first_name")
    )
    if class_ids:
        enrollments = enrollments.filter(section__school_class_id__in=class_ids)

    amounts = {}
    for row in FeeAmount.objects.filter(installment=installment, fee_head__is_active=True).select_related("fee_head"):
        amounts.setdefault(row.school_class_id, []).append(row)

    existing = set(
        Invoice.objects.filter(installment=installment).exclude(status=Invoice.Status.CANCELLED).values_list("student_id", flat=True)
    )
    created, skipped_existing, skipped_no_fees = [], 0, 0
    for enrollment in enrollments:
        student = enrollment.student
        if student.pk in existing:
            skipped_existing += 1
            continue
        school_class = enrollment.section.school_class
        rows = [
            r for r in sorted(amounts.get(school_class.pk, []), key=lambda r: r.fee_head.order)
            if r.amount > 0 and (not r.fee_head.new_students_only or _is_new_student(student, session))
        ]
        if not rows:
            skipped_no_fees += 1
            continue
        lines = [(r.fee_head, r.amount) for r in rows]
        offs = concession_for_lines(lines, approved_concessions(student, session))
        invoice = Invoice.objects.create(
            number=next_number("INV", session), student=student, session=session, installment=installment,
            school_class=school_class, due_date=installment.due_date,
            gross_amount=sum((a for _, a in lines), ZERO), concession_amount=sum(offs, ZERO),
            created_by=request.user,
        )
        InvoiceLine.objects.bulk_create(
            InvoiceLine(invoice=invoice, fee_head=head, amount=amount, concession=off)
            for (head, amount), off in zip(lines, offs)
        )
        invoice.refresh_status()  # a 100% concession makes it paid straight away
        invoice.save(update_fields=["status"])
        created.append(invoice)

    audit.record(request, "fees.invoices_generated", installment, created=len(created),
                 skipped_existing=skipped_existing, skipped_no_fees=skipped_no_fees)
    return {"created": len(created), "skipped_existing": skipped_existing, "skipped_no_fees": skipped_no_fees}


@transaction.atomic
def cancel_invoice(request, invoice, reason):
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.payments.filter(status=Payment.Status.COMPLETED).exists():
        raise ValidationError("Reverse the payments on this invoice before cancelling it.")
    if invoice.status == Invoice.Status.CANCELLED:
        raise ValidationError("This invoice is already cancelled.")
    invoice.status = Invoice.Status.CANCELLED
    invoice.cancel_reason = reason
    invoice.save(update_fields=["status", "cancel_reason", "updated_at"])
    audit.record(request, "fees.invoice_cancelled", invoice, reason=reason)
    return invoice


# ----- payments -----

@transaction.atomic
def record_payment(request, invoice, *, amount, mode, paid_on=None, reference="", online_order=None):
    """Record money received against an invoice and issue a receipt number.

    Offline payments may not exceed the balance. An online payment is money
    already taken by Cashfree, so it is always recorded; any excess is flagged.
    """
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    amount = _money(amount)
    if amount <= 0:
        raise ValidationError({"amount": "Amount must be more than zero."})
    if invoice.status == Invoice.Status.CANCELLED and online_order is None:
        raise ValidationError("This invoice is cancelled.")
    balance = invoice.balance
    if online_order is None and amount > balance:
        raise ValidationError({"amount": f"Amount is more than the balance of Rs {balance}."})

    payment = Payment.objects.create(
        receipt_number=next_number("RCT", invoice.session), invoice=invoice, amount=amount, mode=mode,
        reference=reference, paid_on=paid_on or timezone.localdate(), online_order=online_order,
        received_by=request.user if request is not None and request.user.is_authenticated else None,
    )
    invoice.amount_paid += amount
    invoice.refresh_status()
    invoice.save(update_fields=["amount_paid", "status", "updated_at"])
    if online_order is not None and amount > balance:
        PaymentIssue.objects.create(
            kind=PaymentIssue.Kind.OVERPAID, order=online_order,
            detail=f"Rs {amount} paid online against a balance of Rs {balance} on {invoice.number}.",
        )
    audit.record(request, "fees.payment_recorded", payment, invoice=invoice.number, amount=str(amount), mode=mode)
    notify("fee.payment_received", student=invoice.student, amount=amount, receipt=payment.receipt_number)
    return payment


@transaction.atomic
def reverse_payment(request, payment, reason):
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status == Payment.Status.REVERSED:
        raise ValidationError("This payment is already reversed.")
    invoice = Invoice.objects.select_for_update().get(pk=payment.invoice_id)
    payment.status = Payment.Status.REVERSED
    payment.reversed_by = request.user
    payment.reversed_at = timezone.now()
    payment.reversal_reason = reason
    payment.save()
    invoice.amount_paid -= payment.amount
    invoice.refresh_status()
    invoice.save(update_fields=["amount_paid", "status", "updated_at"])
    audit.record(request, "fees.payment_reversed", payment, reason=reason, amount=str(payment.amount))
    return payment
