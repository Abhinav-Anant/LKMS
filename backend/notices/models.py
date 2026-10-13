from django.conf import settings
from django.db import models


class Notice(models.Model):
    """An announcement for staff, parents or both, optionally limited to some sections."""

    class Audience(models.TextChoices):
        EVERYONE = "everyone", "Everyone"
        STAFF = "staff", "Staff only"
        PARENTS = "parents", "Parents only"

    title = models.CharField(max_length=150)
    body = models.TextField()
    audience = models.CharField(max_length=10, choices=Audience.choices, default=Audience.EVERYONE)
    sections = models.ManyToManyField(
        "academics.Section", blank=True, related_name="notices",
        help_text="Leave empty for the whole school; otherwise only parents of these sections see it",
    )
    is_published = models.BooleanField(default=True)
    send_whatsapp = models.BooleanField(default=False, help_text="Also send to parents on WhatsApp when published")
    whatsapp_queued_at = models.DateTimeField(null=True, blank=True, editable=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title
