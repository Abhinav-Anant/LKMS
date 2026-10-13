from django.contrib import admin

from .models import Notice


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ["title", "audience", "is_published", "published_at", "created_by"]
    list_filter = ["audience", "is_published"]
    filter_horizontal = ["sections"]
