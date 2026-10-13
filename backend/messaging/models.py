from django.conf import settings
from django.db import models


class OutgoingMessage(models.Model):
    """One WhatsApp message: queued by `core.notify`, sent by the `send_whatsapp` worker. Doubles as the send log."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Waiting to send"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Not sent"

    class Kind(models.TextChoices):
        LOGIN = "login", "Sign-in code"
        ALERT = "alert", "Alert"

    event = models.CharField(max_length=40, db_index=True)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    phone = models.CharField(max_length=10, db_index=True)
    text = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED, db_index=True)
    skip_reason = models.CharField(max_length=100, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(db_index=True)
    last_error = models.CharField(max_length=300, blank=True)
    provider_message_id = models.CharField(max_length=100, blank=True)
    student = models.ForeignKey("students.Student", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event} to {self.phone}: {self.get_status_display()}"


class OptOut(models.Model):
    """A number that asked not to get WhatsApp alerts. Sign-in codes the parent asks for are still sent."""

    phone = models.CharField(max_length=10, unique=True)
    note = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "WhatsApp opt-out"

    def __str__(self):
        return self.phone
