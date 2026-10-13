from django.conf import settings
from django.db import models, transaction


class SchoolProfile(models.Model):
    """The single school this installation serves. Only one row is allowed."""

    BOARD_CHOICES = [
        ("rbse", "Rajasthan Board (RBSE)"),
        ("cbse", "CBSE"),
        ("other", "Other / not affiliated"),
    ]

    name = models.CharField(max_length=200, default="Lotus Kids School")
    short_code = models.CharField(
        max_length=10, default="LK", help_text="Used as the prefix of application numbers, e.g. LK"
    )
    address = models.TextField(blank=True)
    district = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, default="Rajasthan")
    pincode = models.CharField(max_length=6, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    udise_code = models.CharField("UDISE+ code", max_length=11, blank=True)
    board = models.CharField(max_length=10, choices=BOARD_CHOICES, default="rbse")
    affiliation_number = models.CharField(max_length=50, blank=True)

    admission_number_prefix = models.CharField(
        max_length=10, blank=True, help_text="Optional text before the admission (S.R.) number"
    )
    admission_number_width = models.PositiveSmallIntegerField(
        default=4, help_text="Digits to zero-pad the admission number to"
    )
    next_admission_number = models.PositiveIntegerField(
        default=1, help_text="Next serial number in the admission register"
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
