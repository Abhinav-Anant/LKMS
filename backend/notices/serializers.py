from rest_framework import serializers

from academics.models import Section
from academics.scope import teacher_sections
from core.permissions import has_capability

from .models import Notice


class NoticeSerializer(serializers.ModelSerializer):
    sections = serializers.PrimaryKeyRelatedField(many=True, queryset=Section.objects.all(), required=False)
    section_labels = serializers.SerializerMethodField()
    audience_label = serializers.CharField(source="get_audience_display", read_only=True)
    created_by_name = serializers.CharField(source="created_by", read_only=True, default=None)

    class Meta:
        model = Notice
        fields = [
            "id", "title", "body", "audience", "audience_label", "sections", "section_labels", "is_published",
            "published_at", "created_by", "created_by_name", "created_at",
        ]
        read_only_fields = ["published_at", "created_by", "created_at"]

    def get_section_labels(self, obj) -> list[str]:
        return [f"{s.school_class.name} {s.name}" for s in obj.sections.all()]

    def validate(self, attrs):
        user = self.context["request"].user
        if has_capability(user, "notices.manage"):
            return attrs
        # Teachers post only to parents of the sections they teach.
        sections = attrs.get("sections", list(self.instance.sections.all()) if self.instance else [])
        if attrs.get("audience", getattr(self.instance, "audience", None)) != Notice.Audience.PARENTS or not sections:
            raise serializers.ValidationError("Teachers can post notices to parents of their own sections only.")
        mine = set(teacher_sections(user).values_list("pk", flat=True))
        if any(s.pk not in mine for s in sections):
            raise serializers.ValidationError({"sections": "You can only post to sections you teach."})
        return attrs


class ParentNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ["id", "title", "body", "published_at"]
