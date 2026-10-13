from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from academics.models import Enrollment, TeachingAssignment
from academics.scope import can_enter_marks, sees_all
from core import audit
from core.permissions import ReadOrManage

from .models import Assessment, Mark
from .serializers import AssessmentSerializer, MarkSheetSerializer, SaveMarksSerializer


def roster(section):
    return (
        Enrollment.objects.filter(section=section, status=Enrollment.Status.ACTIVE)
        .select_related("student")
        .order_by("roll_number", "student__first_name")
    )


class AssessmentViewSet(viewsets.ModelViewSet):
    """Tests and exams. A teacher sees and edits only the subjects they teach; admin and principal see all."""

    serializer_class = AssessmentSerializer
    permission_classes = [IsAuthenticated, ReadOrManage]
    view_capability = "marks.view"
    manage_capability = "marks.enter"
    filterset_fields = ["section", "subject", "term", "is_published", "section__session"]
    pagination_class = None

    queryset = Assessment.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Assessment.objects.none()
        qs = Assessment.objects.select_related("section__school_class", "subject", "term").annotate(
            marks_entered=Count("marks", filter=Q(marks__marks__isnull=False) | Q(marks__is_absent=True))
        )
        user = self.request.user
        if not sees_all(user):
            # Subject teachers see their own subjects; the class teacher sees every subject of their class.
            teaches = TeachingAssignment.objects.filter(teacher=user, section=OuterRef("section"), subject=OuterRef("subject"))
            qs = qs.filter(Q(Exists(teaches)) | Q(section__class_teacher=user))
        return qs

    def perform_create(self, serializer):
        assessment = serializer.save(created_by=self.request.user)
        audit.record(self.request, "assessment.created", assessment)

    def perform_update(self, serializer):
        if serializer.instance.is_published and not sees_all(self.request.user):
            raise PermissionDenied("Published results can only be changed by the principal.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.marks.exists():
            raise ValidationError("Marks have been entered for this test. Delete them first or keep the test.")
        audit.record(self.request, "assessment.deleted", instance)
        instance.delete()

    def _can_edit(self, assessment):
        user = self.request.user
        return can_enter_marks(user, assessment.section, assessment.subject) and (
            not assessment.is_published or sees_all(user)
        )

    def _sheet(self, assessment):
        marks = {m.student_id: m for m in assessment.marks.all()}
        rows = []
        for e in roster(assessment.section):
            m = marks.get(e.student_id)
            rows.append({
                "student": e.student_id, "roll_number": e.roll_number, "name": e.student.full_name,
                "admission_number": e.student.admission_number,
                "marks": m.marks if m else None, "is_absent": m.is_absent if m else False, "remark": m.remark if m else "",
            })
        return MarkSheetSerializer({"assessment": assessment, "can_edit": self._can_edit(assessment), "rows": rows},
                                   context=self.get_serializer_context()).data

    @extend_schema(request=SaveMarksSerializer, responses=MarkSheetSerializer, methods=["POST"])
    @extend_schema(responses=MarkSheetSerializer, methods=["GET"])
    @action(detail=True, methods=["get", "post"])
    def marks(self, request, pk=None):
        assessment = self.get_object()
        if request.method == "GET":
            return Response(self._sheet(assessment))
        if not self._can_edit(assessment):
            raise PermissionDenied("You cannot change marks for this test.")
        data = SaveMarksSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        allowed = {e.student_id for e in roster(assessment.section)}
        errors = {}
        for row in data.validated_data["rows"]:
            if row["student"] not in allowed:
                errors[str(row["student"])] = "Not in this section."
            elif row.get("marks") is not None and row["marks"] > assessment.max_marks:
                errors[str(row["student"])] = f"More than the maximum of {assessment.max_marks}."
            elif row.get("marks") is not None and row["is_absent"]:
                errors[str(row["student"])] = "A student marked absent cannot have marks."
        if errors:
            raise ValidationError({"rows": errors})
        with transaction.atomic():
            for row in data.validated_data["rows"]:
                Mark.objects.update_or_create(
                    assessment=assessment, student_id=row["student"],
                    defaults={"marks": row.get("marks"), "is_absent": row["is_absent"], "remark": row.get("remark", ""),
                              "entered_by": request.user},
                )
            audit.record(request, "marks.saved", assessment, rows=len(data.validated_data["rows"]))
        return Response(self._sheet(self.get_object()))

    @extend_schema(request=None, responses=AssessmentSerializer)
    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        assessment = self.get_object()
        if not can_enter_marks(request.user, assessment.section, assessment.subject):
            raise PermissionDenied("You do not teach this subject in this section.")
        if not assessment.marks.exists():
            raise ValidationError("Enter marks before publishing.")
        assessment.is_published, assessment.published_at = True, timezone.now()
        assessment.save(update_fields=["is_published", "published_at"])
        audit.record(request, "assessment.published", assessment)
        return Response(AssessmentSerializer(self.get_object(), context=self.get_serializer_context()).data)

    @extend_schema(request=None, responses=AssessmentSerializer)
    @action(detail=True, methods=["post"])
    def unpublish(self, request, pk=None):
        if not sees_all(request.user):
            raise PermissionDenied("Only the principal can withdraw published results.")
        assessment = self.get_object()
        assessment.is_published, assessment.published_at = False, None
        assessment.save(update_fields=["is_published", "published_at"])
        audit.record(request, "assessment.unpublished", assessment)
        return Response(AssessmentSerializer(self.get_object(), context=self.get_serializer_context()).data)
