from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models, transaction

from .storage import RandomPath, get_private_storage

HEX_COLOUR = RegexValidator(r"^#[0-9a-fA-F]{6}$", "Use a colour code like #1d4ed8.")


class SchoolProfile(models.Model):
    """The single school this installation serves. Only one row is allowed."""

    BOARD_CHOICES = [
        ("cbse", "CBSE"),
        ("icse", "CISCE (ICSE)"),
        ("state", "State board"),
        ("other", "Other / not affiliated"),
    ]

    name = models.CharField(max_length=200, default="Your School Name")
    short_code = models.CharField(
        max_length=10, default="SCH", help_text="Used as the prefix of application numbers, e.g. SCH"
    )
    address = models.TextField(blank=True)
    district = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=6, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    udise_code = models.CharField("UDISE+ code", max_length=11, blank=True)
    board = models.CharField(max_length=10, choices=BOARD_CHOICES, default="state")
    board_name = models.CharField(
        max_length=100, blank=True, help_text="Full name of the board, e.g. Rajasthan Board of Secondary Education"
    )
    affiliation_number = models.CharField(max_length=50, blank=True)

    # Shown on the public website
    map_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, help_text="Where the school is, for the map, e.g. 26.830321"
    )
    map_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="e.g. 75.825578")
    facebook_url = models.URLField("Facebook page", blank=True)
    instagram_url = models.URLField("Instagram page", blank=True)
    youtube_url = models.URLField("YouTube channel", blank=True)
    x_url = models.URLField("X (Twitter) page", blank=True)

    # Look
    logo = models.FileField(upload_to=RandomPath("school"), storage=get_private_storage, blank=True)
    brand_colour = models.CharField(
        max_length=7, default="#1d4ed8", validators=[HEX_COLOUR], help_text="Main colour of the website, e.g. #1d4ed8"
    )

    # Fees
    upi_id = models.CharField("UPI ID", max_length=100, blank=True, help_text="Shown to parents on the payment page")
    upi_name = models.CharField("UPI account name", max_length=100, blank=True)
    upi_qr = models.FileField(
        "UPI QR code", upload_to=RandomPath("school"), storage=get_private_storage, blank=True,
        help_text="The bank's QR picture. Leave empty to show a QR code made from the UPI ID.",
    )
    office_can_collect_fees = models.BooleanField(
        default=False, help_text="Office staff may record fees paid at the office (cash, cheque)"
    )
    fee_reminder_days_before = models.PositiveSmallIntegerField(
        default=3, help_text="Send a WhatsApp reminder this many days before a fee is due"
    )
    fee_reminder_every_days = models.PositiveSmallIntegerField(
        default=7, help_text="Repeat the reminder every this many days while a fee is overdue"
    )

    admission_number_prefix = models.CharField(
        max_length=10, blank=True, help_text="Optional text before the admission (S.R.) number"
    )
    admission_number_width = models.PositiveSmallIntegerField(
        default=4, help_text="Digits to zero-pad the admission number to"
    )
    next_admission_number = models.PositiveIntegerField(
        default=1, help_text="Next serial number in the admission register"
    )

    captcha_enabled = models.BooleanField(
        "CAPTCHA on public forms", default=True,
        help_text="Visitors must type the letters from a picture before using the admission, tracking and parent sign-in forms",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "school profile"
        verbose_name_plural = "school profile"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise models.ProtectedError("The school profile cannot be deleted", {self})

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def board_label(self):
        return self.board_name or self.get_board_display()

    @property
    def payment_upi_id(self):
        return self.upi_id or settings.SCHOOL_UPI_ID

    @property
    def payment_upi_name(self):
        return self.upi_name or settings.SCHOOL_UPI_NAME or self.name

    @classmethod
    def allocate_admission_number(cls):
        """Take the next number from the admission register. Call inside a transaction."""
        from students.models import Student

        with transaction.atomic():
            cls.get()  # make sure the row exists before locking it
            profile = cls.objects.select_for_update().get(pk=1)
            while True:
                number = f"{profile.admission_number_prefix}{profile.next_admission_number:0{profile.admission_number_width}d}"
                profile.next_admission_number += 1
                if not Student.objects.filter(admission_number=number).exists():
                    break
            profile.save(update_fields=["next_admission_number", "updated_at"])
            return number


class GalleryPhoto(models.Model):
    """A photo of school life, shown to everyone on the website's gallery."""

    image = models.FileField(upload_to=RandomPath("gallery"), storage=get_private_storage)
    caption = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.caption or f"Photo {self.pk}"


class UsedCaptcha(models.Model):
    """A CAPTCHA challenge or pass that has been used, so it cannot be used again."""

    nonce = models.CharField(max_length=32, unique=True)
    used_at = models.DateTimeField(auto_now_add=True, db_index=True)


class AuditLog(models.Model):
    """Append-only record of who did what to student data."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=64, db_index=True)
    object_type = models.CharField(max_length=64, db_index=True)
    object_id = models.CharField(max_length=64, db_index=True)
    object_repr = models.CharField(max_length=200, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        who = self.actor or "public"
        return f"{self.created_at:%Y-%m-%d %H:%M} {who} {self.action} {self.object_type}#{self.object_id}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Audit log entries cannot be changed")
        super().save(*args, **kwargs)


class Counter(models.Model):
    """Gap-free running numbers, e.g. receipt numbers per session."""

    key = models.CharField(max_length=64, unique=True)
    next_value = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.key}: next {self.next_value}"

    @classmethod
    def take(cls, key):
        """Return the next number for `key`. Call inside a transaction so a rollback returns it."""
        cls.objects.get_or_create(key=key)
        counter = cls.objects.select_for_update().get(key=key)
        value = counter.next_value
        counter.next_value += 1
        counter.save(update_fields=["next_value"])
        return value
