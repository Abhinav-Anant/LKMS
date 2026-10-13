from django.contrib import admin

from .models import Concession, FeeAmount, FeeHead, Installment, Invoice, InvoiceLine, OnlineOrder, Payment, PaymentIssue, WebhookEvent


@admin.register(FeeHead)
class FeeHeadAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "new_students_only", "order", "is_active"]
    list_editable = ["order", "is_active"]


class FeeAmountInline(admin.TabularInline):
    model = FeeAmount
    extra = 0


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = ["name", "session", "due_date", "order"]
    list_filter = ["session"]
    inlines = [FeeAmountInline]


@admin.register(Concession)
class ConcessionAdmin(admin.ModelAdmin):
    list_display = ["student", "session", "fee_head", "kind", "value", "status", "requested_by", "decided_by"]
    list_filter = ["status", "session"]
    search_fields = ["student__first_name", "student__admission_number"]
    readonly_fields = ["status", "requested_by", "decided_by", "decided_at"]


class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class LineInline(ReadOnlyInline):
    model = InvoiceLine


class PaymentInline(ReadOnlyInline):
    model = Payment
    fields = ["receipt_number", "amount", "mode", "reference", "paid_on", "status"]


class ReadOnlyAdmin(admin.ModelAdmin):
    """Money records change only through the app, so they are audited."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(ReadOnlyAdmin):
    list_display = ["number", "student", "school_class", "installment", "due_date", "net_amount", "amount_paid", "status"]
    list_filter = ["status", "session", "school_class"]
    search_fields = ["number", "student__first_name", "student__admission_number"]
    inlines = [LineInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = ["receipt_number", "invoice", "amount", "mode", "paid_on", "status", "received_by"]
    list_filter = ["mode", "status", "paid_on"]
    search_fields = ["receipt_number", "reference", "invoice__number"]


@admin.register(OnlineOrder)
class OnlineOrderAdmin(ReadOnlyAdmin):
    list_display = ["order_id", "invoice", "amount", "status", "payment_group", "created_at", "paid_at"]
    list_filter = ["status"]
    search_fields = ["order_id", "cf_payment_id", "invoice__number"]


@admin.register(WebhookEvent)
class WebhookEventAdmin(ReadOnlyAdmin):
    list_display = ["received_at", "event_type", "order_id", "signature_valid", "processed", "error"]
    list_filter = ["signature_valid", "processed", "event_type"]
    search_fields = ["order_id"]


@admin.register(PaymentIssue)
class PaymentIssueAdmin(admin.ModelAdmin):
    list_display = ["created_at", "kind", "order", "resolved"]
    list_filter = ["resolved", "kind"]
    readonly_fields = ["kind", "order", "detail", "created_at"]
