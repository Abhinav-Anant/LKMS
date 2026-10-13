from rest_framework import serializers

from .models import AttendanceRecord


class SheetQuerySerializer(serializers.Serializer):
    section = serializers.IntegerField()
    date = serializers.DateField()


class SheetRowSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    roll_number = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    admission_number = serializers.CharField()
    status = serializers.ChoiceField(choices=AttendanceRecord.Status.choices, allow_null=True)
    note = serializers.CharField(allow_blank=True)


class SheetSerializer(serializers.Serializer):
    section = serializers.IntegerField()
    section_label = serializers.CharField()
    date = serializers.DateField()
    can_edit = serializers.BooleanField()
    marked = serializers.BooleanField()
    marked_by = serializers.CharField(allow_null=True)
    rows = SheetRowSerializer(many=True)


class AttendanceRowSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    status = serializers.ChoiceField(choices=AttendanceRecord.Status.choices)
    note = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class AttendanceMarkSerializer(serializers.Serializer):
    section = serializers.IntegerField()
    date = serializers.DateField()
    records = AttendanceRowSerializer(many=True, allow_empty=False)


class MonthSummaryRowSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    roll_number = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    present = serializers.IntegerField()
    absent = serializers.IntegerField()
    late = serializers.IntegerField()
    leave = serializers.IntegerField()
    marked_days = serializers.IntegerField()
    percentage = serializers.FloatField(allow_null=True)
