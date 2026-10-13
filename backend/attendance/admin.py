from django.contrib import admin

from .models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ["date", "student", "section", "status", "marked_by"]
    list_filter = ["status", "date", "section__school_class"]
    search_fields = ["student__first_name", "student__admission_number"]
    date_hierarchy = "date"
