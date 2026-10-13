from decimal import Decimal

from django.conf import settings
from django.db import models


class TransferCertificate(models.Model):
    """A school leaving / transfer certificate. Requested by the office, issued by the principal."""

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        ISSUED = "issued", "Issued"
        CANCELLED = "cancelled", "Cancelled"

    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="transfer_certificates")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REQUESTED, db_index=True)
    number = models.CharField(max_length=30, unique=True, null=True, blank=True, help_text="Given when issued")

    application_date = models.DateField(help_text="When the parent asked for the TC")
    leaving_date = models.DateField(help_text="Last day the student attended")
    reason = models.CharField(max_length=200, help_text="e.g. Family moving to another city")
    last_exam_result = models.CharField(max_length=200, blank=True, help_text="e.g. Passed Class 3, promoted to Class 4")
    conduct = models.CharField(max_length=50, default="Good")
    remarks = models.CharField(max_length=300, blank=True)

    fees_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"), help_text="Unpaid fees when issued")
    dues_waived_reason = models.CharField(max_length=200, blank=True, help_text="Why the TC was issued with fees unpaid")
    details = models.JSONField(default=dict, blank=True, help_text="Student details as printed, frozen when issued")

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    requested_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    issued_on = models.DateField(null=True, blank=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+")
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-requested_at"]
        verbose_name = "transfer certificate"
        constraints = [
            models.UniqueConstraint(fields=["student"], condition=~models.Q(status="cancelled"), name="one_live_tc_per_student"),
        ]

    def __str__(self):
        return f"TC {self.number or '(not issued)'} {self.student.full_name}"
