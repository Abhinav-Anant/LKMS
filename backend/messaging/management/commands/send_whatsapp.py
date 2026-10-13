"""Deliver queued WhatsApp messages. Run it as a service on the server:

    python manage.py send_whatsapp --loop

Without --loop it sends what is due once and exits (handy from cron).
"""

import time

from django.core.management.base import BaseCommand

from messaging import outbox


class Command(BaseCommand):
    help = "Send queued WhatsApp messages, respecting the rate limit, quiet hours and opt-outs."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true", help="Keep running, checking the queue every few seconds")
        parser.add_argument("--every", type=float, default=5.0, help="Seconds between checks with --loop")

    def handle(self, *args, **options):
        while True:
            sent = outbox.send_due()
            if sent or not options["loop"]:
                self.stdout.write(f"Sent {sent} WhatsApp message(s).")
            if not options["loop"]:
                return
            time.sleep(options["every"])
