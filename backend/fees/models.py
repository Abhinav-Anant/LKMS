from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from core.storage import RandomPath, get_private_storage

MONEY = {"max_digits": 10, "decimal_places": 2}


class FeeHead(models.Model):
    """A kind of charge, e.g. Tuition fee, Admission fee, Annual charges."""

    code = models.SlugField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    new_students_only = models.BooleanField(
        default=False, help_text="Charge only to students admitted in this session (e.g. admission fee)"
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Installment(models.Model):
    """A point in the session when fees fall due, e.g. Quarter 1 due 10 April."""

    session = models.ForeignKey("academics.AcademicSession", on_delete=models.PROTECT, related_name="installments")
    name = models.CharField(max_length=50)
    due_date = models.DateField()
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["session", "order"]
        constraints = [models.UniqueConstraint(fields=["session", "name"], name="unique_installment_name")]

    def __str__(self):
        return f"{self.name} ({self.session.name})"


class FeeAmount(models.Model):
    """How much a class pays for one head in one installment (the fee structure)."""

    installment = models.ForeignKey(Installment, on_delete=models.CASCADE, related_name="amounts")
    school_class = models.ForeignKey("academics.SchoolClass", on_delete=models.PROTECT, related_name="fee_amounts")
    fee_head = models.ForeignKey(FeeHead, on_delete=models.PROTECT, related_name="amounts")
    amount = models.DecimalField(**MONEY, validators=[MinValueValidator(Decimal("0"))])

    class Meta:
        ordering = ["installment", "school_class__order", "fee_head__order"]
        constraints = [
            models.UniqueConstraint(fields=["installment", "school_class", "fee_head"], name="unique_fee_amount"),
        ]

    def __str__(self):
        return f"{self.school_class} {self.fee_head} {self.installment}: {self.amount}"


class Concession(models.Model):
    """A discount for one student in one session. Takes effect only once approved."""

    class Kind(models.TextChoices):
        PERCENT = "percent", "Percentage"
        FIXED = "fixed", "Fixed amount per installment"

    class Status(models.TextChoices):
        PENDING = "pending", "Waiting for approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="concessions")
    session = models.ForeignKey("academics.AcademicSession", on_delete=models.PROTECT, related_name="concessions")
    fee_head = models.ForeignKey(
        FeeHead, null=True, blank=True, on_delete=models.PROTECT, related_name="concessions",
        help_text="Leave empty to apply to every head",
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    value = models.DecimalField(**MONEY, validators=[MinValueValidator(Decimal("0.01"))])
    reason = models.CharField(max_length=200, help_text="e.g. Sibling, staff ward, RTE, merit")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        amount = f"{self.value}%" if self.kind == self.Kind.PERCENT else f"Rs {self.value}"
        return f"{amount} off {self.fee_head or 'all fees'} for {self.student}"


class Invoice(models.Model):
    """What one student owes for one installment."""

    class Status(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PARTLY_PAID = "partly_paid", "Partly paid"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    number = models.CharField(max_length=30, unique=True)
    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="invoices")
    session = models.ForeignKey("academics.AcademicSession", on_delete=models.PROTECT, related_name="invoices")
    installment = models.ForeignKey(Installment, null=True, blank=True, on_delete=models.PROTECT, related_name="invoices")
    school_class = models.ForeignKey("academics.SchoolClass", on_delete=models.PROTECT, related_name="+")
    due_date = models.DateField()
    gross_amount = models.DecimalField(**MONEY, default=Decimal("0"))
    concession_amount = models.DecimalField(**MONEY, default=Decimal("0"))
    amount_paid = models.DecimalField(**MONEY, default=Decimal("0"))
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.UNPAID, db_index=True)
    cancel_reason = models.CharField(max_length=200, blank=True)
    last_reminder_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-due_date", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "installment"],
                condition=~models.Q(status="cancelled"),
                name="one_live_invoice_per_installment",
            ),
        ]

    def __str__(self):
        return f"{self.number} {self.student.full_name}"

    @property
    def net_amount(self):
        return self.gross_amount - self.concession_amount

    @property
    def balance(self):
        return max(self.net_amount - self.amount_paid, Decimal("0"))

    def refresh_status(self):
        if self.status == self.Status.CANCELLED:
            return
        if self.amount_paid >= self.net_amount:
            self.status = self.Status.PAID
        elif self.amount_paid > 0:
            self.status = self.Status.PARTLY_PAID
        else:
            self.status = self.Status.UNPAID


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    fee_head = models.ForeignKey(FeeHead, on_delete=models.PROTECT, related_name="+")
    amount = models.DecimalField(**MONEY)
    concession = models.DecimalField(**MONEY, default=Decimal("0"))

    class Meta:
        ordering = ["fee_head__order"]

    @property
    def net(self):
        return self.amount - self.concession


class Payment(models.Model):
    class Mode(models.TextChoices):
        CASH = "cash", "Cash"
        CHEQUE = "cheque", "Cheque"
        BANK_TRANSFER = "bank_transfer", "Bank transfer"
        UPI = "upi", "UPI to school account"

    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        REVERSED = "reversed", "Reversed"

    receipt_number = models.CharField(max_length=30, unique=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(**MONEY, validators=[MinValueValidator(Decimal("0.01"))])
    mode = models.CharField(max_length=15, choices=Mode.choices)
    reference = models.CharField(max_length=100, blank=True, help_text="Cheque number or UPI/bank transaction reference (UTR)")
    paid_on = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.COMPLETED)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversal_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.receipt_number} Rs {self.amount}"


class UpiSubmission(models.Model):
    """A parent's report that they paid by scanning the school's UPI QR code.

    Nothing is credited until a staff member checks the money arrived in the
    school's bank account and approves it; approving records a Payment and
    issues the receipt.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Waiting for the school to check"
        APPROVED = "approved", "Verified and receipted"
        REJECTED = "rejected", "Not verified"

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="upi_submissions")
    amount = models.DecimalField(**MONEY, validators=[MinValueValidator(Decimal("1"))])
    utr = models.CharField("UPI transaction ID (UTR)", max_length=30, db_index=True)
    paid_on = models.DateField()
    payer_name = models.CharField(max_length=100, blank=True)
    screenshot = models.FileField(upload_to=RandomPath("upi-receipts"), storage=get_private_storage)
    screenshot_type = models.CharField(max_length=50)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    submitted_from = models.GenericIPAddressField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reject_reason = models.CharField(max_length=200, blank=True)
    payment = models.OneToOneField(Payment, null=True, blank=True, on_delete=models.PROTECT, related_name="upi_submission")

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            # The same bank transaction cannot be claimed twice (a rejected claim can be sent again).
            models.UniqueConstraint(fields=["utr"], condition=~models.Q(status="rejected"), name="unique_live_utr"),
        ]

    def __str__(self):
        return f"UPI {self.utr} Rs {self.amount} for {self.invoice.number}"
