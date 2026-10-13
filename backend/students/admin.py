from django.contrib import admin

from .models import Guardian, Student, StudentGuardian


class StudentGuardianInline(admin.TabularInline):
    model = StudentGuardian
    extra = 0
    raw_id_fields = ["guardian"]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ["admission_number", "first_name", "last_name", "date_of_birth", "status"]
    list_filter = ["status", "gender", "category"]
    search_fields = ["admission_number", "first_name", "last_name"]
    inlines = [StudentGuardianInline]
    readonly_fields = ["admission_number", "application", "created_at", "updated_at"]


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ["full_name", "phone", "email"]
    search_fields = ["full_name", "phone", "email"]
