"""Outgoing notifications.

Domain code calls `notify(event, **context)` and never talks to a messaging
provider directly. Each event is logged and, when it has a WhatsApp template
(messaging/templates.py), queued for the `send_whatsapp` worker.
"""

import logging

from django.conf import settings

# Never write one-time codes to production logs.
SECRET_KEYS = {"code"}

logger = logging.getLogger("lkms.notify")


def notify(event, **context):
    shown = {k: ("***" if k in SECRET_KEYS and not settings.DEBUG else str(v)) for k, v in context.items()}
    logger.info("notification event=%s context=%s", event, shown)

    from django.db import transaction

    from messaging.outbox import queue

    try:
        with transaction.atomic():
            queue(event, **context)
    except Exception:
        # A message that cannot be queued must never break the action that triggered it.
        logger.exception("could not queue WhatsApp message for event=%s", event)
