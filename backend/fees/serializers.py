from rest_framework import serializers

from .models import Concession, FeeAmount, FeeHead, Installment, Invoice, InvoiceLine, OnlineOrder, Payment, PaymentIssue


class FeeHeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeHead
        fields = ["id", "code", "name", "new_students_only", "order", "is_active"]


class InstallmentSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta:
        model = Installment
        fields = ["id", "session", "session_name", "name", "due_date", "order"]


class FeeAmountSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeAmount
        fields = ["id", "installment", "school_class", "fee_head", "amount"]


class FeeAmountRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeAmount
        fields = ["school_class", "fee_head", "amount"]
        validators = []  # uniqueness is handled by update_or_create


class FeeAmountBulkSerializer(serializers.Serializer):
    """Set many amounts for one installment in one call; amount 0 removes a row."""

    installment = serializers.PrimaryKeyRelatedField(queryset=Installment.objects.all())
    amounts = FeeAmountRowSerializer(many=True, allow_empty=False)


class InvoiceLineSerializer(serializers.ModelSerializer):
    fee_head_name = serializers.CharField(source="fee_head.name", read_only=True)
    net = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = InvoiceLine
        fields = ["id", "fee_head", "fee_head_name", "amount", "concession", "net"]


class PaymentSerializer(serializers.ModelSerializer):
    mode_label = serializers.CharField(source="get_mode_display", read_only=True)
    received_by = serializers.StringRelatedField()
    invoice_number = serializers.CharField(source="invoice.number", read_only=True)
    student_name = serializers.CharField(source="invoice.student.full_name", read_only=True)
    admission_number = serializers.CharField(source="invoice.student.admission_number", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "receipt_number", "invoice", "invoice_number", "student_name", "admission_number", "amount", "mode",
            "mode_label", "reference", "paid_on", "status", "received_by", "created_at", "reversal_reason", "reversed_at",
        ]


class RecordPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    mode = serializers.ChoiceField(choices=[c for c in Payment.Mode.choices if c[0] != Payment.Mode.ONLINE])
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    paid_on = serializers.DateField(required=False)

    def validate(self, attrs):
        if attrs["mode"] in (Payment.Mode.CHEQUE, Payment.Mode.BANK_TRANSFER, Payment.Mode.UPI) and not attrs.get("reference"):
            raise serializers.ValidationError({"reference": "Enter the cheque number or transaction reference."})
        return attrs


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=200)


class OnlineOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlineOrder
        fields = ["id", "order_id", "amount", "status", "status_note", "payment_group", "cf_payment_id", "created_at", "paid_at"]


class InvoiceListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)
    class_name = serializers.CharField(source="school_class.name", read_only=True)
    installment_name = serializers.CharField(source="installment.name", read_only=True, default="")
    net_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "number", "student", "student_name", "admission_number", "class_name", "installment_name", "due_date",
            "gross_amount", "concession_amount", "net_amount", "amount_paid", "balance", "status",
        ]


class InvoiceDetailSerializer(InvoiceListSerializer):
    session_name = serializers.CharField(source="session.name", read_only=True)
    lines = InvoiceLineSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    online_orders = OnlineOrderSerializer(many=True, read_only=True)

    class Meta(InvoiceListSerializer.Meta):
        fields = InvoiceListSerializer.Meta.fields + [
            "session", "session_name", "cancel_reason", "created_at", "lines", "payments", "online_orders",
        ]


class GenerateInvoicesSerializer(serializers.Serializer):
    installment = serializers.PrimaryKeyRelatedField(queryset=Installment.objects.select_related("session"))
    classes = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)


class ConcessionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    fee_head_name = serializers.CharField(source="fee_head.name", read_only=True, default="All fees")
    requested_by = serializers.StringRelatedField()
    decided_by = serializers.StringRelatedField()

    class Meta:
        model = Concession
        fields = [
            "id", "student", "student_name", "admission_number", "session", "session_name", "fee_head", "fee_head_name",
            "kind", "value", "reason", "status", "requested_by", "requested_at", "decided_by", "decided_at", "decision_note",
        ]
        read_only_fields = ["status", "requested_at", "decided_at", "decision_note"]

    def validate(self, attrs):
        if attrs.get("kind") == Concession.Kind.PERCENT and attrs.get("value", 0) > 100:
            raise serializers.ValidationError({"value": "A percentage cannot be more than 100."})
        return attrs


class DecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    note = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class PaymentIssueSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    order_id = serializers.CharField(source="order.order_id", read_only=True, default="")
    invoice = serializers.IntegerField(source="order.invoice_id", read_only=True, default=None)

    class Meta:
        model = PaymentIssue
        fields = ["id", "kind", "kind_label", "order_id", "invoice", "detail", "resolved", "resolved_note", "created_at"]
        read_only_fields = ["kind", "detail", "created_at"]


class PublicInvoiceSerializer(serializers.ModelSerializer):
    """What a parent sees on the pay page: no phone numbers, no other students."""

    student_name = serializers.CharField(source="student.first_name", read_only=True)
    class_name = serializers.CharField(source="school_class.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    installment_name = serializers.CharField(source="installment.name", read_only=True, default="")
    lines = InvoiceLineSerializer(many=True, read_only=True)
    net_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "number", "student_name", "class_name", "session_name", "installment_name", "due_date", "lines",
            "gross_amount", "concession_amount", "net_amount", "amount_paid", "balance", "status",
        ]
