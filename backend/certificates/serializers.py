from rest_framework import serializers

from .models import TransferCertificate


class TransferCertificateSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)
    class_label = serializers.SerializerMethodField()
    current_fees_due = serializers.SerializerMethodField()
    issued_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TransferCertificate
        fields = [
            "id", "student", "student_name", "admission_number", "class_label", "status", "number",
            "application_date", "leaving_date", "reason", "last_exam_result", "conduct", "remarks",
            "fees_due", "current_fees_due", "dues_waived_reason", "requested_at", "issued_on", "issued_by_name",
            "cancelled_at", "cancel_reason",
        ]
        read_only_fields = ["status", "number", "fees_due", "dues_waived_reason", "issued_on", "cancelled_at",
                            "cancel_reason"]

    def get_class_label(self, obj) -> str:
        if obj.details.get("last_class"):
            return obj.details["last_class"]
        e = obj.student.current_enrollment()
        return f"{e.section.school_class.name} {e.section.name}" if e else ""

    def get_current_fees_due(self, obj) -> str:
        from .services import fees_due

        return str(fees_due(obj.student)) if obj.status == obj.Status.REQUESTED else str(obj.fees_due)

    def get_issued_by_name(self, obj) -> str:
        u = obj.issued_by
        return (u.get_full_name() or u.username) if u else ""

    def validate(self, attrs):
        if self.instance and self.instance.status != TransferCertificate.Status.REQUESTED:
            raise serializers.ValidationError("An issued or cancelled TC cannot be edited.")
        student = attrs.get("student", getattr(self.instance, "student", None))
        if self.instance and "student" in attrs and attrs["student"] != self.instance.student:
            raise serializers.ValidationError({"student": "Cancel this request and start a new one instead."})
        if not self.instance:
            live = TransferCertificate.objects.filter(student=student).exclude(status=TransferCertificate.Status.CANCELLED)
            if live.exists():
                raise serializers.ValidationError({"student": "This student already has a TC request or TC."})
            if student.status != student.Status.ACTIVE:
                raise serializers.ValidationError({"student": f"This student is marked '{student.get_status_display()}'."})
        if attrs.get("leaving_date") and attrs["leaving_date"] < student.admission_date:
            raise serializers.ValidationError({"leaving_date": "Leaving date is before the admission date."})
        return attrs


class IssueSerializer(serializers.Serializer):
    dues_waived_reason = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=200)
