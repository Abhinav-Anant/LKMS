from rest_framework import serializers

from .models import OptOut, OutgoingMessage


class OutgoingMessageSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True, default=None)

    class Meta:
        model = OutgoingMessage
        fields = [
            "id", "event", "kind", "phone", "text", "status", "status_label", "skip_reason", "attempts",
            "next_attempt_at", "last_error", "student", "student_name", "created_at", "sent_at",
        ]


class OptOutSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(max_length=20)
    created_by_name = serializers.CharField(source="created_by", read_only=True, default=None)

    class Meta:
        model = OptOut
        fields = ["id", "phone", "note", "created_by_name", "created_at"]

    def validate_phone(self, value):
        from students.validators import normalise_mobile

        digits = normalise_mobile(value)
        if len(digits) != 10:
            raise serializers.ValidationError("Enter a 10-digit mobile number.")
        if OptOut.objects.filter(phone=digits).exists():
            raise serializers.ValidationError("This number has already opted out.")
        return digits


class WhatsAppStatusSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    reachable = serializers.BooleanField()
    state = serializers.CharField()
    phone = serializers.CharField(allow_null=True)
    error = serializers.CharField(allow_blank=True)
    queued = serializers.IntegerField()
    sent_24h = serializers.IntegerField()
    failed_24h = serializers.IntegerField()
    skipped_24h = serializers.IntegerField()
    opted_out = serializers.IntegerField()
    oldest_queued = serializers.DateTimeField(allow_null=True)
    quiet_hours = serializers.CharField()
    rate_per_minute = serializers.IntegerField()


class QrSerializer(serializers.Serializer):
    qr = serializers.CharField(allow_null=True)


class AlertsPreferenceSerializer(serializers.Serializer):
    whatsapp_alerts = serializers.BooleanField()
