"""Outgoing notifications (WhatsApp in Phase 4).

Domain code calls `notify(event, **context)` and never talks to a messaging
provider directly. Until the WhatsApp adapter is added, events are only logged.
"""

import logging

from django.conf import settings

# Never write one-time codes to production logs.
SECRET_KEYS = {"code"}

logger = logging.getLogger("lkms.notify")


def notify(event, **context):
    shown = {k: ("***" if k in SECRET_KEYS and not settings.DEBUG else str(v)) for k, v in context.items()}
    logger.info("notification event=%s context=%s", event, shown)
