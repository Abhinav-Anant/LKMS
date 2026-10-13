from django.contrib import admin

from .models import OptOut, OutgoingMessage


@admin.register(OutgoingMessage)
class OutgoingMessageAdmin(admin.ModelAdmin):
    list_display = ["created_at", "event", "phone", "status", "attempts", "sent_at"]
    list_filter = ["status", "event", "kind"]
    search_fields = ["phone"]
    readonly_fields = [f.name for f in OutgoingMessage._meta.fields]


@admin.register(OptOut)
class OptOutAdmin(admin.ModelAdmin):
    list_display = ["phone", "note", "created_by", "created_at"]
    search_fields = ["phone"]
