from rest_framework import serializers

from .models import AcademicSession, Enrollment, PeriodSlot, SchoolClass, Section, Subject, TeachingAssignment, TimetableEntry


class AcademicSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicSession
        fields = ["id", "name", "start_date", "end_date", "is_current", "admissions_open", "age_cutoff_date"]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_date": "End date must be after start date."})
        return attrs


class SchoolClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolClass
        fields = ["id", "name", "code", "order", "min_age_years", "max_age_years", "is_active"]


class SectionSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="school_class.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    strength = serializers.IntegerField(read_only=True)
    class_teacher_name = serializers.CharField(source="class_teacher.__str__", read_only=True, default="")

    class Meta:
        model = Section
        fields = [
            "id", "session", "session_name", "school_class", "class_name", "name", "capacity", "class_teacher",
            "class_teacher_name", "strength",
        ]


class EnrollmentSerializer(serializers.ModelSerializer):
    section_label = serializers.CharField(source="section.__str__", read_only=True)
    class_name = serializers.CharField(source="section.school_class.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "student", "session", "session_name", "section", "section_label", "class_name", "section_name",
                  "roll_number", "status", "enrolled_on"]


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name", "code", "order", "is_active"]


class TeachingAssignmentSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.__str__", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    section_label = serializers.CharField(source="section.__str__", read_only=True)

    class Meta:
        model = TeachingAssignment
        fields = ["id", "teacher", "teacher_name", "section", "section_label", "subject", "subject_name"]

    def validate_teacher(self, user):
        if user.role != "teacher" and user.role not in ("principal", "admin"):
            raise serializers.ValidationError("Only staff who teach can be given a subject.")
        return user


class PeriodSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodSlot
        fields = ["id", "number", "start_time", "end_time", "label"]

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return attrs


class TimetableEntrySerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.__str__", read_only=True, default="")
    section_label = serializers.CharField(source="section.__str__", read_only=True)
    period_number = serializers.IntegerField(source="period.number", read_only=True)
    start_time = serializers.TimeField(source="period.start_time", read_only=True)
    end_time = serializers.TimeField(source="period.end_time", read_only=True)

    class Meta:
        model = TimetableEntry
        fields = [
            "id", "section", "section_label", "weekday", "period", "period_number", "start_time", "end_time",
            "subject", "subject_name", "teacher", "teacher_name",
        ]

    def validate(self, attrs):
        teacher = attrs.get("teacher", getattr(self.instance, "teacher", None))
        weekday = attrs.get("weekday", getattr(self.instance, "weekday", None))
        period = attrs.get("period", getattr(self.instance, "period", None))
        section = attrs.get("section", getattr(self.instance, "section", None))
        if teacher and weekday and period:
            clash = TimetableEntry.objects.filter(
                teacher=teacher, weekday=weekday, period=period, section__session=section.session
            ).exclude(pk=getattr(self.instance, "pk", None)).exclude(section=section).first()
            if clash:
                raise serializers.ValidationError({"teacher": f"{teacher} already teaches {clash.section} in this period."})
        return attrs
