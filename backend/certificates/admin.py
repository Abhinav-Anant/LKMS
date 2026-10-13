from django.contrib import admin

from .models import TransferCertificate


@admin.register(TransferCertificate)
class TransferCertificateAdmin(admin.ModelAdmin):
    list_display = ["number", "student", "status", "issued_on"]
    list_filter = ["status"]
    readonly_fields = [f.name for f in TransferCertificate._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
