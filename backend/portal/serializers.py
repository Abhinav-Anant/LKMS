from rest_framework import serializers

from attendance.models import AttendanceRecord
from fees.models import Invoice, Payment


class ChildSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    admission_number = serializers.CharField()
    class_label = serializers.CharField(allow_null=True)
    roll_number = serializers.IntegerField(allow_null=True)
    class_teacher = serializers.CharField(allow_null=True)


class AttendanceDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    status = serializers.ChoiceField(choices=AttendanceRecord.Status.choices)
    note = serializers.CharField(allow_blank=True)


class AttendanceMonthSerializer(serializers.Serializer):
    month = serializers.CharField()
    present = serializers.IntegerField()
    absent = serializers.IntegerField()
    late = serializers.IntegerField()
    leave = serializers.IntegerField()
    percentage = serializers.FloatField(allow_null=True)
    days = AttendanceDaySerializer(many=True)


class ParentInvoiceSerializer(serializers.ModelSerializer):
    installment_name = serializers.CharField(source="installment.name", read_only=True, default="")
    net_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    pay_link = serializers.CharField(allow_null=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "number", "installment_name", "due_date", "net_amount", "amount_paid", "balance", "status",
            "status_label", "pay_link",
        ]


class ParentPaymentSerializer(serializers.ModelSerializer):
    mode_label = serializers.CharField(source="get_mode_display", read_only=True)
    invoice_number = serializers.CharField(source="invoice.number", read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "receipt_number", "invoice_number", "amount", "mode", "mode_label", "paid_on"]


class ParentFeesSerializer(serializers.Serializer):
    invoices = ParentInvoiceSerializer(many=True)
    payments = ParentPaymentSerializer(many=True)
    total_due = serializers.DecimalField(max_digits=10, decimal_places=2)


class ParentMarkSerializer(serializers.Serializer):
    assessment = serializers.IntegerField()
    name = serializers.CharField()
    subject = serializers.CharField()
    date = serializers.DateField()
    max_marks = serializers.DecimalField(max_digits=6, decimal_places=2)
    marks = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True)
    is_absent = serializers.BooleanField()
    remark = serializers.CharField(allow_blank=True)


class ParentReportCardSerializer(serializers.Serializer):
    term = serializers.IntegerField()
    name = serializers.CharField()
    session = serializers.CharField()
    published_at = serializers.DateTimeField()
