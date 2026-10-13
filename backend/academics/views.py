from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.permissions import Can, ReadOrManage

from .models import AcademicSession, Enrollment, PeriodSlot, SchoolClass, Section, Subject, TeachingAssignment, TimetableEntry
from .scope import teacher_sections
from .serializers import (
    AcademicSessionSerializer,
    PeriodSlotSerializer,
    SchoolClassSerializer,
    SectionSerializer,
    SubjectSerializer,
    TeachingAssignmentSerializer,
    TimetableEntrySerializer,
)


class PageSizePagination(PageNumberPagination):
    """Default 25 a page; set-up screens ask for everything with ?page_size=500."""

    page_size_query_param = "page_size"
    max_page_size = 500


class _Managed(viewsets.ModelViewSet):
    permission_classes = [ReadOrManage]
    pagination_class = PageSizePagination
    view_capability = "academics.view"
    manage_capability = "academics.manage"


class AcademicSessionViewSet(_Managed):
    queryset = AcademicSession.objects.all()
    serializer_class = AcademicSessionSerializer


class SchoolClassViewSet(_Managed):
    queryset = SchoolClass.objects.all()
    serializer_class = SchoolClassSerializer
    filterset_fields = ["is_active"]


class SectionViewSet(_Managed):
    serializer_class = SectionSerializer
    filterset_fields = ["session", "school_class"]

    def get_queryset(self):
        return Section.objects.select_related("session", "school_class", "class_teacher").annotate(
            strength=Count("enrollments", filter=Q(enrollments__status=Enrollment.Status.ACTIVE))
        ).order_by("-session__start_date", "school_class__order", "name")


@extend_schema(responses=inline_serializer("AdmissionOptions", {
    "sessions": AcademicSessionSerializer(many=True), "classes": SchoolClassSerializer(many=True),
}))
@api_view(["GET"])
@permission_classes([AllowAny])
def admission_options(request):
    """What the public admission form needs: the open session and classes on offer."""
    sessions = AcademicSession.objects.filter(admissions_open=True)
    classes = SchoolClass.objects.filter(is_active=True)
    return Response({
        "sessions": AcademicSessionSerializer(sessions, many=True).data,
        "classes": SchoolClassSerializer(classes, many=True).data,
    })


class SubjectViewSet(_Managed):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    pagination_class = None
    filterset_fields = ["is_active"]


class TeachingAssignmentViewSet(_Managed):
    serializer_class = TeachingAssignmentSerializer
    pagination_class = None
    filterset_fields = ["teacher", "section", "section__session", "subject"]

    def get_queryset(self):
        return TeachingAssignment.objects.select_related("teacher", "subject", "section__school_class", "section__session")


class PeriodSlotViewSet(_Managed):
    queryset = PeriodSlot.objects.all()
    serializer_class = PeriodSlotSerializer
    pagination_class = None


class TimetableEntryViewSet(_Managed):
    serializer_class = TimetableEntrySerializer
    pagination_class = None
    filterset_fields = ["section", "teacher", "weekday", "section__session"]

    def get_queryset(self):
        return TimetableEntry.objects.select_related("subject", "teacher", "period", "section__school_class", "section__session")


class MySectionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    class_name = serializers.CharField()
    name = serializers.CharField()
    is_class_teacher = serializers.BooleanField()
    subjects = serializers.ListField(child=serializers.DictField())
    strength = serializers.IntegerField()


@extend_schema(responses=MySectionSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsAuthenticated, Can("academics.view")])
def my_sections(request):
    """The sections this staff member teaches in this session (all sections for admin and principal)."""
    sections = teacher_sections(request.user).annotate(
        strength=Count("enrollments", filter=Q(enrollments__status=Enrollment.Status.ACTIVE))
    ).order_by("school_class__order", "name")
    assignments = TeachingAssignment.objects.filter(section__in=sections).select_related("subject")
    by_section = {}
    for a in assignments:
        if a.teacher_id == request.user.pk or request.user.role in ("admin", "principal") or request.user.is_superuser:
            by_section.setdefault(a.section_id, []).append({"id": a.subject_id, "name": a.subject.name})
    data = [{
        "id": s.pk, "label": f"{s.school_class.name} {s.name}", "class_name": s.school_class.name, "name": s.name,
        "is_class_teacher": s.class_teacher_id == request.user.pk, "subjects": by_section.get(s.pk, []),
        "strength": s.strength,
    } for s in sections]
    return Response(data)


@extend_schema(responses=TimetableEntrySerializer(many=True))
@api_view(["GET"])
@permission_classes([IsAuthenticated, Can("academics.view")])
def my_timetable(request):
    """This teacher's periods for the week in the current session."""
    entries = TimetableEntry.objects.filter(teacher=request.user, section__session__is_current=True).select_related(
        "subject", "teacher", "period", "section__school_class", "section__session"
    )
    return Response(TimetableEntrySerializer(entries, many=True).data)
