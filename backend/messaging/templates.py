"""The words of every WhatsApp message LKMS sends. Edit here to change the wording.

Each builder takes the `notify()` context and returns a list of (phone, text, student)
to send, or [] when the event needs no message.
"""

from django.conf import settings

from core.models import SchoolProfile


def _school():
    return SchoolProfile.get().name


def _money(value):
    text = f"₹{value:,.2f}"
    return text[:-3] if text.endswith(".00") else text


def _date(value):
    return f"{value:%d %b %Y}"


FOOTER = "\n\nTo stop these messages, tell the school office."


def student_phone(student):
    """The number to message about a student: the primary contact, else any guardian."""
    link = student.guardian_links.select_related("guardian").order_by("-is_primary_contact", "id").first()
    return link.guardian.phone if link else ""


def _about(student, text):
    phone = student_phone(student)
    return [(phone, f"{_school()}: {text}{FOOTER}", student)] if phone else []


def parent_login_code(ctx):
    return [(ctx["phone"], f"{_school()}: your parent portal sign-in code is {ctx['code']}. "
             f"It works for {ctx['minutes']} minutes. Do not share it with anyone.", None)]


def fee_reminder(ctx):
    s = ctx["student"]
    when = (f"was due on {_date(ctx['due_date'])} and is overdue" if ctx["overdue"] else f"is due on {_date(ctx['due_date'])}")
    return _about(s, f"the fee of {_money(ctx['balance'])} for {s.full_name} (bill {ctx['invoice']}) {when}. "
                     f"Pay by UPI here: {ctx['pay_link']} or at the school office.")


def fee_payment_received(ctx):
    s = ctx["student"]
    return _about(s, f"we received {_money(ctx['amount'])} for {s.full_name}. Receipt number {ctx['receipt']}. Thank you.")


def fee_upi_submitted(ctx):
    s = ctx["student"]
    return _about(s, f"we got your UPI payment details for {s.full_name} ({_money(ctx['amount'])}, UTR {ctx['utr']}). "
                     "The school will check them and send the receipt.")


def fee_upi_rejected(ctx):
    s = ctx["student"]
    return _about(s, f"we could not match your UPI payment for {s.full_name} (bill {ctx['invoice']}): {ctx['reason']}. "
                     "Please contact the school office.")


def _track_link():
    return f"{settings.FRONTEND_BASE_URL}/track"


def admission_submitted(ctx):
    a = ctx["application"]
    if not a.primary_phone:
        return []
    return [(a.primary_phone, f"{_school()}: application {a.application_number} for {a.child_name} has been received. "
             f"Track it at {_track_link()}{FOOTER}", None)]


def admission_status_changed(ctx):
    a = ctx["application"]
    if not a.primary_phone:
        return []
    message = f" {a.status_message}" if a.status_message else ""
    return [(a.primary_phone, f"{_school()}: application {a.application_number} for {a.child_name} is now "
             f"'{a.get_status_display()}'.{message} Track it at {_track_link()}{FOOTER}", None)]


def attendance_absent(ctx):
    from .models import OutgoingMessage

    s = ctx["student"]
    # Marked absent, corrected, then absent again: tell the parent only once a day.
    if OutgoingMessage.objects.filter(event="attendance.absent", student=s, created_at__date=ctx["date"]).exists():
        return []
    return _about(s, f"{s.full_name} was marked absent today ({_date(ctx['date'])}). "
                     "If you did not expect this, please contact the class teacher.")


def notice_published(ctx):
    notice = ctx["notice"]
    body = notice.body if len(notice.body) <= 900 else notice.body[:900].rsplit(" ", 1)[0] + "…"
    return [(phone, f"{_school()}: {notice.title}\n\n{body}{FOOTER}", None) for phone in ctx["phones"]]


def report_card_published(ctx):
    from .models import OutgoingMessage

    s, term = ctx["student"], ctx["term"]
    label = f"{term.name} {term.session.name}"
    # Published, withdrawn for a correction, then published again: one message is enough.
    if OutgoingMessage.objects.filter(event="report_card.published", student=s, text__contains=label).exists():
        return []
    return _about(s, f"the {label} report card of {s.full_name} is ready. "
                     f"See it in the parent portal: {settings.FRONTEND_BASE_URL}/parent")


def tc_issued(ctx):
    tc = ctx["tc"]
    return _about(tc.student, f"transfer certificate {tc.number} for {tc.student.full_name} has been issued. "
                              "Please collect it from the school office.")


BUILDERS = {
    "parent_login_code": parent_login_code,
    "fee.reminder": fee_reminder,
    "fee.payment_received": fee_payment_received,
    "fee.upi_submitted": fee_upi_submitted,
    "fee.upi_rejected": fee_upi_rejected,
    "admission.submitted": admission_submitted,
    "admission.status_changed": admission_status_changed,
    "attendance.absent": attendance_absent,
    "notice.published": notice_published,
    "report_card.published": report_card_published,
    "tc.issued": tc_issued,
}

LOGIN_EVENTS = {"parent_login_code"}
