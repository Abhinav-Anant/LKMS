from rest_framework import serializers

from academics.scope import can_enter_marks

from .models import Assessment


class AssessmentSerializer(serializers.ModelSerializer):
    section_label = serializers.SerializerMethodField()
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    term_name = serializers.CharField(source="term.name", read_only=True, default=None)
    marks_entered = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Assessment
        fields = [
            "id", "section", "section_label", "subject", "subject_name", "term", "term_name", "name", "date", "max_marks",
            "is_published", "published_at", "marks_entered",
        ]
        read_only_fields = ["is_published", "published_at"]

    def get_section_label(self, obj) -> str:
        return f"{obj.section.school_class.name} {obj.section.name}"

    def validate(self, attrs):
        section = attrs.get("section", getattr(self.instance, "section", None))
        subject = attrs.get("subject", getattr(self.instance, "subject", None))
        if not can_enter_marks(self.context["request"].user, section, subject):
            raise serializers.ValidationError("You do not teach this subject in this section.")
        term = attrs.get("term", getattr(self.instance, "term", None))
        if term and section and term.session_id != section.session_id:
            raise serializers.ValidationError({"term": "This term belongs to a different session."})
        if self.instance and ("section" in attrs or "subject" in attrs) and self.instance.marks.exists():
            if attrs.get("section", section) != self.instance.section or attrs.get("subject", subject) != self.instance.subject:
                raise serializers.ValidationError("Section and subject cannot change once marks are entered.")
        return attrs


class MarkRowSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    marks = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=0, allow_null=True, required=False)
    is_absent = serializers.BooleanField(default=False)
    remark = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class MarkSheetRowSerializer(MarkRowSerializer):
    roll_number = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    admission_number = serializers.CharField()


class MarkSheetSerializer(serializers.Serializer):
    assessment = AssessmentSerializer()
    can_edit = serializers.BooleanField()
    rows = MarkSheetRowSerializer(many=True)


class SaveMarksSerializer(serializers.Serializer):
    rows = MarkRowSerializer(many=True, allow_empty=False)
