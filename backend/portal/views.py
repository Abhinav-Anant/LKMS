"""The parent portal: what a signed-in parent can see about their own children."""

import calendar
from collections import Counter
from datetime import date
from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from academics.models import TimetableEntry
from academics.serializers import TimetableEntrySerializer
from assessments.models import Mark
from attendance.models import AttendanceRecord
from core import audit
from exams import report as exam_report
from exams.models import ExamTerm
from exams.pdf import report_cards_pdf
from exams.views import PDF, pdf_download
from fees import upi
from fees.models import Invoice, Payment
from fees.views import pdf_response
from messaging.models import OptOut
from messaging.serializers import AlertsPreferenceSerializer
from notices.serializers import ParentNoticeSerializer
from notices.views import parent_notices
from users.parent_login import children_for_phone

from .serializers import (
    AttendanceMonthSerializer,
    ChildSerializer,
    ParentFeesSerializer,
    ParentInvoiceSerializer,
    ParentMarkSerializer,
    ParentPaymentSerializer,
    ParentReportCardSerializer,
)


class IsParent(BasePermission):
    message = "This page is for parents."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "parent" and request.user.phone)


PARENT = [IsAuthenticated, IsParent]


def my_children(user):
    return children_for_phone(user.phone)


def my_child(user, pk):
    child = my_children(user).filter(pk=pk).first()
    if child is None:
        raise NotFound("Child not found.")
    return child


def child_data(child):
    e = child.current_enrollment()
    teacher = e.section.class_teacher if e else None
    return {
        "id": child.pk, "full_name": child.full_name, "admission_number": child.admission_number,
        "class_label": f"{e.section.school_class.name} {e.section.name}" if e else None,
        "roll_number": e.roll_number if e else None,
        "class_teacher": (teacher.get_full_name() or teacher.username) if teacher else None,
    }


@extend_schema(responses=ChildSerializer(many=True))
@api_view(["GET"])
@permission_classes(PARENT)
def children(request):
    return Response([child_data(c) for c in my_children(request.user).order_by("first_name")])


@extend_schema(parameters=[OpenApiParameter("month", str, description="YYYY-MM, default this month")],
               responses=AttendanceMonthSerializer)
@api_view(["GET"])
@permission_classes(PARENT)
def child_attendance(request, pk):
    child = my_child(request.user, pk)
    month = request.query_params.get("month") or timezone.localdate().strftime("%Y-%m")
    try:
        year, mon = (int(p) for p in month.split("-"))
        start = date(year, mon, 1)
    except ValueError:
        raise ValidationError({"month": "Use YYYY-MM."})
    end = start.replace(day=calendar.monthrange(year, mon)[1])
    records = AttendanceRecord.objects.filter(student=child, date__range=(start, end)).order_by("date")
    counts = Counter(r.status for r in records)
    marked = sum(counts.values())
    return Response({
        "month": f"{year:04d}-{mon:02d}", "present": counts["present"], "absent": counts["absent"],
        "late": counts["late"], "leave": counts["leave"],
        "percentage": round(100 * (counts["present"] + counts["late"]) / marked, 1) if marked else None,
        "days": [{"date": r.date, "status": r.status, "note": r.note} for r in records],
    })


@extend_schema(responses=ParentFeesSerializer)
@api_view(["GET"])
@permission_classes(PARENT)
def child_fees(request, pk):
    child = my_child(request.user, pk)
    invoices = list(Invoice.objects.filter(student=child).exclude(status=Invoice.Status.CANCELLED).select_related("installment"))
    for inv in invoices:
        inv.pay_link = upi.pay_link(inv) if inv.balance > 0 else None
    payments = Payment.objects.filter(invoice__student=child, status=Payment.Status.COMPLETED).select_related("invoice")
    return Response({
        "invoices": ParentInvoiceSerializer(invoices, many=True).data,
        "payments": ParentPaymentSerializer(payments, many=True).data,
        "total_due": sum((i.balance for i in invoices), Decimal("0")),
    })


@extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
@api_view(["GET"])
@permission_classes(PARENT)
def child_receipt(request, pk, payment_id):
    child = my_child(request.user, pk)
    payment = get_object_or_404(Payment, pk=payment_id, invoice__student=child, status=Payment.Status.COMPLETED)
    return pdf_response(payment)


@extend_schema(responses=ParentMarkSerializer(many=True))
@api_view(["GET"])
@permission_classes(PARENT)
def child_marks(request, pk):
    child = my_child(request.user, pk)
    marks = Mark.objects.filter(student=child, assessment__is_published=True).select_related("assessment__subject")
    return Response(ParentMarkSerializer([{
        "assessment": m.assessment_id, "name": m.assessment.name, "subject": m.assessment.subject.name,
        "date": m.assessment.date, "max_marks": m.assessment.max_marks, "marks": m.marks, "is_absent": m.is_absent,
        "remark": m.remark,
    } for m in marks.order_by("-assessment__date", "assessment__subject__order")], many=True).data)


@extend_schema(responses=ParentReportCardSerializer(many=True))
@api_view(["GET"])
@permission_classes(PARENT)
def child_report_cards(request, pk):
    """Published report cards of a child, newest first."""
    child = my_child(request.user, pk)
    terms = ExamTerm.objects.filter(is_published=True, session__enrollments__student=child,
                                    assessments__section__enrollments__student=child).distinct().select_related("session")
    return Response(ParentReportCardSerializer([
        {"term": t.pk, "name": t.name, "session": t.session.name, "published_at": t.published_at} for t in terms
    ], many=True).data)


@extend_schema(responses=PDF)
@api_view(["GET"])
@permission_classes(PARENT)
def child_report_card(request, pk, term_id):
    child = my_child(request.user, pk)
    term = get_object_or_404(ExamTerm, pk=term_id, is_published=True)
    e = exam_report.enrollment_for(term, child)
    if e is None:
        raise NotFound("No report card for this term.")
    cards = exam_report.build(term, e.section, students=[child])
    if not cards:
        raise NotFound("No report card for this term.")
    return pdf_download(report_cards_pdf(term, cards), f"report-card-{child.admission_number}-{term.name}.pdf".replace(" ", "-"))


@extend_schema(responses=TimetableEntrySerializer(many=True))
@api_view(["GET"])
@permission_classes(PARENT)
def child_timetable(request, pk):
    e = my_child(request.user, pk).current_enrollment()
    if e is None:
        return Response([])
    entries = TimetableEntry.objects.filter(section=e.section).select_related(
        "subject", "teacher", "period", "section__school_class", "section__session"
    )
    return Response(TimetableEntrySerializer(entries, many=True).data)


@extend_schema(responses=ParentNoticeSerializer(many=True))
@api_view(["GET"])
@permission_classes(PARENT)
def notices(request):
    sections = [e.section_id for c in my_children(request.user) if (e := c.current_enrollment())]
    return Response(ParentNoticeSerializer(parent_notices(sections)[:50], many=True).data)


@extend_schema(methods=["GET"], responses=AlertsPreferenceSerializer)
@extend_schema(methods=["PUT"], request=AlertsPreferenceSerializer, responses=AlertsPreferenceSerializer)
@api_view(["GET", "PUT"])
@permission_classes(PARENT)
def whatsapp_alerts(request):
    """Parents can turn WhatsApp alerts off and on. Sign-in codes they ask for are always sent."""
    phone = request.user.phone
    if request.method == "PUT":
        data = AlertsPreferenceSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        if data.validated_data["whatsapp_alerts"]:
            for opt_out in OptOut.objects.filter(phone=phone):
                audit.record(request, "whatsapp.opted_in", opt_out)
                opt_out.delete()
        elif not OptOut.objects.filter(phone=phone).exists():
            opt_out = OptOut.objects.create(phone=phone, note="Turned off by the parent in the portal", created_by=request.user)
            audit.record(request, "whatsapp.opted_out", opt_out)
    return Response({"whatsapp_alerts": not OptOut.objects.filter(phone=phone).exists()})
