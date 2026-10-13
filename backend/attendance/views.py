import calendar
from collections import Counter
from datetime import date

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from academics.models import Section
from academics.scope import sees_all, teacher_sections
from core.permissions import Can, has_capability

from . import services
from .models import AttendanceRecord
from .serializers import AttendanceMarkSerializer, MonthSummaryRowSerializer, SheetQuerySerializer, SheetSerializer


def visible_section(user, section_id):
    try:
        section = Section.objects.select_related("school_class", "session").get(pk=section_id)
    except Section.DoesNotExist:
        raise NotFound("Section not found.")
    if sees_all(user) or user.role == "office":
        return section
    if not teacher_sections(user, section.session).filter(pk=section.pk).exists():
        raise PermissionDenied("You do not teach this section.")
    return section


def parse_month(value):
    try:
        year, month = (int(p) for p in (value or "").split("-"))
        return date(year, month, 1)
    except ValueError:
        raise ValidationError({"month": "Use YYYY-MM."})


class SheetView(APIView):
    """The attendance register for one section on one day."""

    permission_classes = [IsAuthenticated, Can("attendance.view")]

    @extend_schema(parameters=[SheetQuerySerializer], responses=SheetSerializer)
    def get(self, request):
        query = SheetQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        section = visible_section(request.user, query.validated_data["section"])
        day = query.validated_data["date"]
        return Response(self.sheet(request.user, section, day))

    @extend_schema(request=AttendanceMarkSerializer, responses=SheetSerializer)
    def post(self, request):
        if not has_capability(request.user, "attendance.mark"):
            raise PermissionDenied("You may not mark attendance.")
        data = AttendanceMarkSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        section = visible_section(request.user, data.validated_data["section"])
        day = data.validated_data["date"]
        services.mark(request, section, day, data.validated_data["records"])
        return Response(self.sheet(request.user, section, day))

    @staticmethod
    def sheet(user, section, day):
        records = {r.student_id: r for r in AttendanceRecord.objects.filter(section=section, date=day).select_related("marked_by")}
        rows = []
        for e in services.roster(section):
            r = records.get(e.student_id)
            rows.append({
                "student": e.student_id, "roll_number": e.roll_number, "name": e.student.full_name,
                "admission_number": e.student.admission_number,
                "status": r.status if r else None, "note": r.note if r else "",
            })
        marker = next((r.marked_by for r in records.values() if r.marked_by), None)
        return SheetSerializer({
            "section": section.pk, "section_label": f"{section.school_class.name} {section.name}", "date": day,
            "can_edit": has_capability(user, "attendance.mark") and services.can_edit(user, section, day),
            "marked": bool(records), "marked_by": str(marker) if marker else None, "rows": rows,
        }).data


class MonthSummaryView(APIView):
    """Per-student attendance totals for a section over one month."""

    permission_classes = [IsAuthenticated, Can("attendance.view")]

    @extend_schema(
        parameters=[OpenApiParameter("section", int, required=True), OpenApiParameter("month", str, required=True)],
        responses=MonthSummaryRowSerializer(many=True),
    )
    def get(self, request):
        section = visible_section(request.user, request.query_params.get("section"))
        start = parse_month(request.query_params.get("month"))
        end = start.replace(day=calendar.monthrange(start.year, start.month)[1])
        counts = {}
        for student_id, status in AttendanceRecord.objects.filter(
            section=section, date__range=(start, end)
        ).values_list("student_id", "status"):
            counts.setdefault(student_id, Counter())[status] += 1
        rows = []
        for e in services.roster(section):
            c = counts.get(e.student_id, Counter())
            marked = sum(c.values())
            present = c["present"] + c["late"]
            rows.append({
                "student": e.student_id, "roll_number": e.roll_number, "name": e.student.full_name,
                "present": c["present"], "absent": c["absent"], "late": c["late"], "leave": c["leave"],
                "marked_days": marked, "percentage": round(100 * present / marked, 1) if marked else None,
            })
        return Response(MonthSummaryRowSerializer(rows, many=True).data)
