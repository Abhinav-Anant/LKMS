from rest_framework import serializers

from .grading import CO_SCHOLASTIC_AREAS, CO_SCHOLASTIC_GRADES
from .models import ExamTerm, GradeBand


class ExamTermSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source="session.name", read_only=True)
    assessments = serializers.IntegerField(source="assessments_count", read_only=True, default=0)
    unpublished_assessments = serializers.IntegerField(source="unpublished_count", read_only=True, default=0)

    class Meta:
        model = ExamTerm
        fields = ["id", "session", "session_name", "name", "order", "start_date", "end_date", "is_published",
                  "published_at", "assessments", "unpublished_assessments"]
        read_only_fields = ["is_published", "published_at"]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "End date must be on or after the start date."})
        session = attrs.get("session", getattr(self.instance, "session", None))
        if self.instance and "session" in attrs and attrs["session"] != self.instance.session \
                and self.instance.assessments.exists():
            raise serializers.ValidationError({"session": "Tests already belong to this term."})
        if session and start and end and (start < session.start_date or end > session.end_date):
            raise serializers.ValidationError({"start_date": f"Dates must fall within the {session.name} session."})
        return attrs


class GradeBandSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeBand
        fields = ["id", "grade", "min_percent", "description", "is_pass"]


class SubjectResultSerializer(serializers.Serializer):
    subject = serializers.CharField()
    percent = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True)
    grade = serializers.CharField()


class ResultRowSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    roll_number = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    admission_number = serializers.CharField()
    subjects = SubjectResultSerializer(many=True)
    obtained = serializers.DecimalField(max_digits=8, decimal_places=2)
    maximum = serializers.DecimalField(max_digits=8, decimal_places=2)
    percent = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True)
    grade = serializers.CharField()
    result = serializers.CharField()
    attendance_present = serializers.IntegerField()
    attendance_marked = serializers.IntegerField()
    remark = serializers.CharField()
    co_scholastic = serializers.DictField(child=serializers.CharField())


class ResultSheetSerializer(serializers.Serializer):
    term = ExamTermSerializer()
    section = serializers.IntegerField()
    section_label = serializers.CharField()
    can_edit_remarks = serializers.BooleanField()
    co_scholastic_areas = serializers.ListField(child=serializers.CharField())
    co_scholastic_grades = serializers.ListField(child=serializers.CharField())
    rows = ResultRowSerializer(many=True)


class RemarkRowSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    remark = serializers.CharField(max_length=300, allow_blank=True, required=False, default="")
    co_scholastic = serializers.DictField(child=serializers.CharField(allow_blank=True), required=False, default=dict)

    def validate_co_scholastic(self, value):
        unknown = set(value) - set(CO_SCHOLASTIC_AREAS)
        if unknown:
            raise serializers.ValidationError(f"Unknown area: {', '.join(sorted(unknown))}.")
        bad = {g for g in value.values() if g and g not in CO_SCHOLASTIC_GRADES}
        if bad:
            raise serializers.ValidationError(f"Use one of {', '.join(CO_SCHOLASTIC_GRADES)}.")
        return {k: v for k, v in value.items() if v}


class SaveRemarksSerializer(serializers.Serializer):
    rows = RemarkRowSerializer(many=True, allow_empty=False)
