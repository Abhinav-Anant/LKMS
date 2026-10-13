from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.permissions import ReadOrManage

from .models import AcademicSession, Enrollment, SchoolClass, Section
from .serializers import AcademicSessionSerializer, SchoolClassSerializer, SectionSerializer


class _Managed(viewsets.ModelViewSet):
    permission_classes = [ReadOrManage]
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
        return Section.objects.select_related("session", "school_class").annotate(
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
