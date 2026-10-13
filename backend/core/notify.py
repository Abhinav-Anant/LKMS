"""Outgoing notifications (WhatsApp in Phase 4).

Domain code calls `notify(event, **context)` and never talks to a messaging
provider directly. Until the WhatsApp adapter is added, events are only logged.
"""

import logging

logger = logging.getLogger("lkms.notify")


def notify(event, **context):
    logger.info("notification event=%s context=%s", event, {k: str(v) for k, v in context.items()})
