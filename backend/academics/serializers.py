from rest_framework import serializers

from .models import AcademicSession, Enrollment, SchoolClass, Section


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

    class Meta:
        model = Section
        fields = ["id", "session", "session_name", "school_class", "class_name", "name", "capacity", "class_teacher", "strength"]


class EnrollmentSerializer(serializers.ModelSerializer):
    section_label = serializers.CharField(source="section.__str__", read_only=True)
    class_name = serializers.CharField(source="section.school_class.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "student", "session", "session_name", "section", "section_label", "class_name", "section_name",
                  "roll_number", "status", "enrolled_on"]
