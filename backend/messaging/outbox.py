"""Queue and send WhatsApp messages.

`queue()` is called by `core.notify` inside the web request and only writes rows.
The `send_whatsapp` worker calls `send_due()` to deliver them, which keeps the
school's number under a gentle sending rate so WhatsApp does not block it.
"""

import logging
import random
import time
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from . import templates, whatsapp
from .models import OptOut, OutgoingMessage

logger = logging.getLogger("lkms.messaging")

# Wait this long before retry 1, 2, 3, ... (minutes).
BACKOFF_MINUTES = [1, 5, 15, 60, 180]
LOGIN_CODE_TTL = timedelta(minutes=10)
S = OutgoingMessage.Status


def queue(event, **context):
    """Turn a notify() event into queued messages. Returns the rows created."""
    builder = templates.BUILDERS.get(event)
    if builder is None:
        return []
    kind = OutgoingMessage.Kind.LOGIN if event in templates.LOGIN_EVENTS else OutgoingMessage.Kind.ALERT
    now = timezone.now()
    rows = []
    for phone, text, student in builder(context):
        row = OutgoingMessage(event=event, kind=kind, phone=phone, text=text, student=student, next_attempt_at=now)
        if not settings.WHATSAPP_ENABLED:
            row.status, row.skip_reason = S.SKIPPED, "WhatsApp is switched off"
        elif kind == OutgoingMessage.Kind.ALERT and OptOut.objects.filter(phone=phone).exists():
            row.status, row.skip_reason = S.SKIPPED, "Parent opted out"
        rows.append(row)
    created = OutgoingMessage.objects.bulk_create(rows)
    for row in created:
        if row.kind == OutgoingMessage.Kind.LOGIN and row.status == S.SKIPPED:
            _redact(row)
    return created


def _redact(row):
    """Sign-in codes are not kept once they can no longer be sent."""
    if row.kind == OutgoingMessage.Kind.LOGIN:
        row.text = "(sign-in code hidden)"
        OutgoingMessage.objects.filter(pk=row.pk).update(text=row.text)


def in_quiet_hours(moment=None):
    """No alerts at night (school's local time). Sign-in codes go any time."""
    start, end = settings.WHATSAPP_QUIET_HOURS
    hour = timezone.localtime(moment).hour
    return hour >= start or hour < end if start > end else start <= hour < end


def sent_in_last_minute():
    return OutgoingMessage.objects.filter(status=S.SENT, sent_at__gte=timezone.now() - timedelta(minutes=1)).count()


def _sent_today(phone):
    midnight = timezone.make_aware(datetime.combine(timezone.localdate(), datetime.min.time()))
    return OutgoingMessage.objects.filter(phone=phone, status=S.SENT, kind=OutgoingMessage.Kind.ALERT,
                                          sent_at__gte=midnight).count()


def expire_stale():
    """Sign-in codes nobody could send in time are dropped; the parent asks again or gets one from the office."""
    stale = OutgoingMessage.objects.filter(kind=OutgoingMessage.Kind.LOGIN, status=S.QUEUED,
                                           created_at__lt=timezone.now() - LOGIN_CODE_TTL)
    return stale.update(status=S.SKIPPED, skip_reason="Code expired before it could be sent", text="(sign-in code hidden)")


def due_messages(limit):
    now = timezone.now()
    qs = OutgoingMessage.objects.filter(status=S.QUEUED, next_attempt_at__lte=now)
    if in_quiet_hours(now):
        qs = qs.filter(kind=OutgoingMessage.Kind.LOGIN)
    # Sign-in codes first, then oldest first.
    return list(qs.order_by("kind", "created_at")[:limit]) if limit > 0 else []


SENT, OFFLINE, OTHER = "sent", "offline", "other"


def send_one(row):
    """Try to send one queued message. Returns SENT, OFFLINE (stop the batch) or OTHER."""
    claimed = OutgoingMessage.objects.filter(pk=row.pk, status=S.QUEUED).update(status=S.SENDING, next_attempt_at=timezone.now())
    if not claimed:
        return OTHER
    if row.kind == OutgoingMessage.Kind.ALERT:
        if OptOut.objects.filter(phone=row.phone).exists():
            OutgoingMessage.objects.filter(pk=row.pk).update(status=S.SKIPPED, skip_reason="Parent opted out")
            return OTHER
        if _sent_today(row.phone) >= settings.WHATSAPP_DAILY_LIMIT_PER_NUMBER:
            OutgoingMessage.objects.filter(pk=row.pk).update(status=S.SKIPPED, skip_reason="Daily limit for this number reached")
            return OTHER
    try:
        message_id = whatsapp.send_text(row.phone, row.text)
    except whatsapp.WhatsAppError as err:
        return _failed(row, err)
    OutgoingMessage.objects.filter(pk=row.pk).update(
        status=S.SENT, sent_at=timezone.now(), provider_message_id=message_id[:100], attempts=row.attempts + 1, last_error="",
    )
    _redact(row)
    return SENT


def _failed(row, err):
    now = timezone.now()
    if err.offline:
        # Not this message's fault: put it back without using up an attempt.
        OutgoingMessage.objects.filter(pk=row.pk).update(status=S.QUEUED, last_error=str(err)[:300],
                                                          next_attempt_at=now + timedelta(minutes=1))
        logger.warning("WhatsApp offline, will retry: %s", err)
        return OFFLINE
    attempts = row.attempts + 1
    if not err.retry or attempts >= settings.WHATSAPP_MAX_ATTEMPTS:
        OutgoingMessage.objects.filter(pk=row.pk).update(status=S.FAILED, attempts=attempts, last_error=str(err)[:300])
        _redact(row)
    else:
        wait = BACKOFF_MINUTES[min(attempts - 1, len(BACKOFF_MINUTES) - 1)]
        OutgoingMessage.objects.filter(pk=row.pk).update(status=S.QUEUED, attempts=attempts, last_error=str(err)[:300],
                                                          next_attempt_at=now + timedelta(minutes=wait))
    return OTHER


def send_due(sleep=time.sleep):
    """Send what is due, within the per-minute limit. Returns how many were sent."""
    if not settings.WHATSAPP_ENABLED:
        return 0
    expire_stale()
    # A worker that died mid-send leaves rows in "sending"; give them back after a while.
    OutgoingMessage.objects.filter(status=S.SENDING, next_attempt_at__lt=timezone.now() - timedelta(minutes=5)).update(status=S.QUEUED)
    sent = 0
    for row in due_messages(settings.WHATSAPP_RATE_PER_MINUTE - sent_in_last_minute()):
        result = send_one(row)
        if result == OFFLINE:
            break
        if result == SENT:
            sent += 1
            # Space messages out with some randomness, as a person would.
            gap = settings.WHATSAPP_SEND_GAP_SECONDS
            if gap:
                sleep(random.uniform(gap, gap * 2))
    return sent


def retry(row):
    """Staff asked to send a failed message again."""
    OutgoingMessage.objects.filter(pk=row.pk, status=S.FAILED).exclude(kind=OutgoingMessage.Kind.LOGIN).update(
        status=S.QUEUED, attempts=0, next_attempt_at=timezone.now(), last_error=""
    )


def summary():
    since = timezone.now() - timedelta(days=1)
    recent = OutgoingMessage.objects.filter(created_at__gte=since)
    return {
        "queued": OutgoingMessage.objects.filter(status=S.QUEUED).count(),
        "sent_24h": recent.filter(status=S.SENT).count(),
        "failed_24h": recent.filter(status=S.FAILED).count(),
        "skipped_24h": recent.filter(status=S.SKIPPED).count(),
        "opted_out": OptOut.objects.count(),
        "oldest_queued": OutgoingMessage.objects.filter(status=S.QUEUED).order_by("created_at")
        .values_list("created_at", flat=True).first(),
    }
