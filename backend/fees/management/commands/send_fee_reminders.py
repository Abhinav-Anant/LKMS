"""Remind parents about fees due soon or overdue. Run daily, e.g. from cron:

    0 9 * * *  cd /srv/lkms/backend && .venv/bin/python manage.py send_fee_reminders
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from core.notify import notify
from fees import upi
from fees.models import Invoice


class Command(BaseCommand):
    help = "Send fee reminders (through the notification hook) for invoices due soon or overdue."

    def add_arguments(self, parser):
        parser.add_argument("--days-before", type=int, default=3, help="Remind this many days before the due date")
        parser.add_argument("--every", type=int, default=7, help="Repeat overdue reminders every N days")

    def handle(self, *args, **options):
        now = timezone.now()
        today = timezone.localdate()
        invoices = (
            Invoice.objects.filter(status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTLY_PAID])
            .filter(due_date__lte=today + timedelta(days=options["days_before"]))
            .filter(Q(last_reminder_at__isnull=True) | Q(last_reminder_at__lt=now - timedelta(days=options["every"])))
            .select_related("student")
        )
        sent = 0
        for invoice in invoices:
            notify(
                "fee.reminder", student=invoice.student, invoice=invoice.number, balance=invoice.balance,
                due_date=invoice.due_date, overdue=invoice.due_date < today, pay_link=upi.pay_link(invoice),
            )
            invoice.last_reminder_at = now
            invoice.save(update_fields=["last_reminder_at"])
            sent += 1
        self.stdout.write(f"Queued {sent} fee reminders.")
