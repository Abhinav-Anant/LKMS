from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "get_full_name", "role", "phone", "is_active", "last_login"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["username", "first_name", "last_name", "email", "phone"]
    fieldsets = BaseUserAdmin.fieldsets + (("LKMS", {"fields": ("role", "phone", "must_change_password")}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (("LKMS", {"fields": ("role", "phone", "first_name", "last_name")}),)
