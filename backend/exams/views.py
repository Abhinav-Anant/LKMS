from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from academics.models import Enrollment, Section
from academics.scope import sees_all, teacher_sections
from core import audit
from core.notify import notify
from core.permissions import ReadOrManage
from students.models import Student

from . import report
from .grading import CO_SCHOLASTIC_AREAS, CO_SCHOLASTIC_GRADES
from .models import ExamTerm, GradeBand, ReportCardEntry
from .pdf import report_cards_pdf
from .serializers import (
    ExamTermSerializer,
    GradeBandSerializer,
    ResultSheetSerializer,
    SaveRemarksSerializer,
)

SECTION_PARAM = OpenApiParameter("section", int, required=True)
PDF = {(200, "application/pdf"): OpenApiTypes.BINARY}


def pdf_download(content, filename):
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def can_see_section(user, section):
    return sees_all(user) or teacher_sections(user, section.session).filter(pk=section.pk).exists()


def can_edit_remarks(user, section):
    return sees_all(user) or section.class_teacher_id == user.pk


class ExamTermViewSet(viewsets.ModelViewSet):
    """Exam terms (Half-yearly, Annual). Each groups tests into one report card."""

    serializer_class = ExamTermSerializer
    permission_classes = [IsAuthenticated, ReadOrManage]
    view_capability = "marks.view"
    manage_capability = "academics.manage"
    filterset_fields = ["session", "is_published"]
    pagination_class = None
    queryset = ExamTerm.objects.none()

    def get_queryset(self):
        return ExamTerm.objects.select_related("session").annotate(
            assessments_count=Count("assessments"),
            unpublished_count=Count("assessments", filter=Q(assessments__is_published=False)),
        )

    def perform_create(self, serializer):
        audit.record(self.request, "exam_term.created", serializer.save())

    def perform_destroy(self, instance):
        if instance.assessments.exists():
            raise ValidationError("Tests belong to this term. Move or delete them first.")
        audit.record(self.request, "exam_term.deleted", instance)
        instance.delete()

    def _section(self, request, term):
        section_id = request.query_params.get("section")
        if not section_id:
            raise ValidationError({"section": "Choose a section."})
        section = get_object_or_404(Section.objects.select_related("school_class", "session"), pk=section_id)
        if section.session_id != term.session_id:
            raise ValidationError({"section": "This section is from a different session."})
        if not can_see_section(request.user, section):
            raise PermissionDenied("You do not teach this section.")
        return section

    def _sheet(self, request, term, section):
        cards = report.build(term, section)
        return ResultSheetSerializer({
            "term": term, "section": section.pk, "section_label": f"{section.school_class.name} {section.name}",
            "can_edit_remarks": can_edit_remarks(request.user, section) and (not term.is_published or sees_all(request.user)),
            "co_scholastic_areas": CO_SCHOLASTIC_AREAS, "co_scholastic_grades": CO_SCHOLASTIC_GRADES,
            "rows": [report.summary_row(c) for c in cards],
        }).data

    @extend_schema(parameters=[SECTION_PARAM], responses=ResultSheetSerializer)
    @action(detail=True, methods=["get"])
    def results(self, request, pk=None):
        """The class result sheet: every student's subject percentages, grade, attendance and remark."""
        term = self.get_object()
        return Response(self._sheet(request, term, self._section(request, term)))

    @extend_schema(parameters=[SECTION_PARAM], request=SaveRemarksSerializer, responses=ResultSheetSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def remarks(self, request, pk=None):
        """The class teacher saves remarks and co-scholastic grades."""
        term = self.get_object()
        section = self._section(request, term)
        if not can_edit_remarks(request.user, section):
            raise PermissionDenied("Only the class teacher or the principal can write report card remarks.")
        if term.is_published and not sees_all(request.user):
            raise PermissionDenied("Report cards are published. Ask the principal to make changes.")
        data = SaveRemarksSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        allowed = set(Enrollment.objects.filter(section=section).values_list("student_id", flat=True))
        bad = [str(r["student"]) for r in data.validated_data["rows"] if r["student"] not in allowed]
        if bad:
            raise ValidationError({"rows": {s: "Not in this section." for s in bad}})
        with transaction.atomic():
            for row in data.validated_data["rows"]:
                ReportCardEntry.objects.update_or_create(term=term, student_id=row["student"], defaults={
                    "remark": row["remark"], "co_scholastic": row["co_scholastic"], "updated_by": request.user,
                })
            audit.record(request, "report_card.remarks_saved", term, section=section.pk,
                         rows=len(data.validated_data["rows"]))
        return Response(self._sheet(request, term, section))

    @extend_schema(parameters=[SECTION_PARAM, OpenApiParameter("student", int)], responses=PDF)
    @action(detail=True, methods=["get"], url_path="report-cards")
    def report_cards(self, request, pk=None):
        """Report cards as one PDF: the whole section, or one student with ?student=."""
        term = self.get_object()
        section = self._section(request, term)
        students = None
        if request.query_params.get("student"):
            students = [get_object_or_404(Student, pk=request.query_params["student"])]
        cards = report.build(term, section, students=students)
        if students and not cards:
            raise ValidationError({"student": "This student is not in the section."})
        name = (f"report-card-{cards[0]['student'].admission_number}" if students
                else f"report-cards-{section.school_class.code}{section.name}")
        return pdf_download(report_cards_pdf(term, cards), f"{name}-{term.name}.pdf".replace(" ", "-"))

    @extend_schema(request=None, responses=ExamTermSerializer)
    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Show report cards to parents and send each family a WhatsApp message."""
        term = self.get_object()
        if not term.assessments.exists():
            raise ValidationError("No tests are linked to this term yet.")
        waiting = term.assessments.filter(is_published=False).count()
        if waiting:
            raise ValidationError(f"{waiting} test(s) in this term still have unpublished marks. Publish them first.")
        term.is_published, term.published_at = True, timezone.now()
        term.save(update_fields=["is_published", "published_at"])
        audit.record(request, "exam_term.published", term)
        sections = term.assessments.values_list("section", flat=True).distinct()
        students = Student.objects.filter(enrollments__section__in=sections, status=Student.Status.ACTIVE).distinct()
        for student in students:
            notify("report_card.published", student=student, term=term)
        return Response(self.get_serializer(self.get_queryset().get(pk=term.pk)).data)

    @extend_schema(request=None, responses=ExamTermSerializer)
    @action(detail=True, methods=["post"])
    def unpublish(self, request, pk=None):
        term = self.get_object()
        term.is_published, term.published_at = False, None
        term.save(update_fields=["is_published", "published_at"])
        audit.record(request, "exam_term.unpublished", term)
        return Response(self.get_serializer(self.get_queryset().get(pk=term.pk)).data)


class GradeBandViewSet(viewsets.ModelViewSet):
    """The grading scale. PLACEHOLDER bands until the school confirms its scale."""

    serializer_class = GradeBandSerializer
    permission_classes = [IsAuthenticated, ReadOrManage]
    view_capability = "marks.view"
    manage_capability = "academics.manage"
    pagination_class = None
    queryset = GradeBand.objects.all()

    def perform_create(self, serializer):
        audit.record(self.request, "grade_band.created", serializer.save())

    def perform_update(self, serializer):
        audit.record(self.request, "grade_band.updated", serializer.save())

    def perform_destroy(self, instance):
        audit.record(self.request, "grade_band.deleted", instance)
        instance.delete()
