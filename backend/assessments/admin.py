from django.contrib import admin

from .models import Assessment, Mark


class MarkInline(admin.TabularInline):
    model = Mark
    extra = 0
    raw_id_fields = ["student"]


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ["name", "subject", "section", "date", "max_marks", "is_published"]
    list_filter = ["is_published", "subject", "section__session"]
    inlines = [MarkInline]
