from django.contrib import admin

from .models import AcademicSession, Enrollment, SchoolClass, Section


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ["name", "start_date", "end_date", "is_current", "admissions_open"]


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ["order", "name", "code", "min_age_years", "max_age_years", "is_active"]
    list_display_links = ["name"]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ["__str__", "capacity", "class_teacher"]
    list_filter = ["session", "school_class"]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ["student", "session", "section", "roll_number", "status"]
    list_filter = ["session", "section__school_class", "status"]
    search_fields = ["student__first_name", "student__last_name", "student__admission_number"]
    raw_id_fields = ["student"]
