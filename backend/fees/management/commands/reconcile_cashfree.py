"""Check recent online payments against Cashfree. Run nightly, e.g. from cron:

    30 1 * * *  cd /srv/lkms/backend && .venv/bin/python manage.py reconcile_cashfree
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from fees import cashfree, online


class Command(BaseCommand):
    help = "Compare online fee orders from the last few days with Cashfree and fix or flag differences."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=3, help="How many days back to check (default 3)")

    def handle(self, *args, **options):
        if not cashfree.is_configured():
            raise CommandError("Cashfree keys are not set (CASHFREE_CLIENT_ID / CASHFREE_CLIENT_SECRET).")
        counts = online.reconcile(timezone.now() - timedelta(days=options["days"]))
        self.stdout.write(
            f"Checked {counts['checked']} orders: {counts['newly_paid']} newly confirmed paid, "
            f"{counts['expired_or_failed']} expired or failed, {counts['issues']} need checking, "
            f"{counts['errors']} could not be checked."
        )
        if counts["issues"] or counts["errors"]:
            self.stdout.write(self.style.WARNING("See Fees > Payment issues in the staff app."))
