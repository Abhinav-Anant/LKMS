from django.contrib import admin

from .models import AdmissionApplication, ApplicationDocument, ApplicationStatusChange, DocumentType


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ["order", "name", "code", "is_required", "allow_pdf", "allow_image", "is_active"]
    list_display_links = ["name"]
    filter_horizontal = ["classes"]


class DocumentInline(admin.TabularInline):
    model = ApplicationDocument
    extra = 0
    fields = ["document_type", "content_type", "size", "is_current", "verification", "verification_note", "uploaded_at"]
    readonly_fields = fields
    can_delete = False


class HistoryInline(admin.TabularInline):
    model = ApplicationStatusChange
    extra = 0
    readonly_fields = ["from_status", "to_status", "changed_by", "message", "created_at"]
    can_delete = False


@admin.register(AdmissionApplication)
class AdmissionApplicationAdmin(admin.ModelAdmin):
    """Read-mostly: decisions go through the API so they are checked and audited."""

    list_display = ["application_number", "child_name", "class_applied", "session", "status", "submitted_at"]
    list_filter = ["status", "session", "class_applied"]
    search_fields = ["application_number", "first_name", "last_name", "father_phone", "mother_phone"]
    readonly_fields = ["application_number", "status", "status_message", "reviewed_by", "submitted_at",
                       "decided_at", "consent_given_at"]
    exclude = ["access_token_hash"]
    inlines = [DocumentInline, HistoryInline]
