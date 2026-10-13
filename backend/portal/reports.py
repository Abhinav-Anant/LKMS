"""School-wide figures for the principal's dashboard."""

from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.urls import path
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from academics.models import AcademicSession, Enrollment, Section
from admissions.models import AdmissionApplication
from attendance.models import AttendanceRecord
from core.permissions import Can
from fees.models import Concession, Invoice, Payment, UpiSubmission


class DashboardSerializer(serializers.Serializer):
    session = serializers.CharField(allow_null=True)
    date = serializers.DateField()
    students_total = serializers.IntegerField()
    students_by_class = serializers.ListField(child=serializers.DictField())
    attendance_today = serializers.DictField()
    fees = serializers.DictField()
    pending = serializers.DictField()


@extend_schema(responses=DashboardSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated, Can("reports.view")])
def dashboard(request):
    session = AcademicSession.current()
    today = timezone.localdate()
    active = Enrollment.objects.filter(session=session, status=Enrollment.Status.ACTIVE)
    by_class = list(
        active.values(name=F("section__school_class__name"), order=F("section__school_class__order"))
        .annotate(students=Count("id")).order_by("order")
    )

    sections = Section.objects.filter(session=session).select_related("school_class").annotate(
        strength=Count("enrollments", filter=Q(enrollments__status=Enrollment.Status.ACTIVE))
    ).filter(strength__gt=0)
    marked = set(AttendanceRecord.objects.filter(date=today, section__session=session).values_list("section_id", flat=True))
    counts = dict(
        AttendanceRecord.objects.filter(date=today, section__session=session).values_list("status").annotate(n=Count("id"))
    )

    invoices = Invoice.objects.filter(session=session).exclude(status=Invoice.Status.CANCELLED)
    totals = invoices.aggregate(gross=Sum("gross_amount"), concession=Sum("concession_amount"), paid=Sum("amount_paid"))
    billed = (totals["gross"] or Decimal("0")) - (totals["concession"] or Decimal("0"))
    paid = totals["paid"] or Decimal("0")
    month_collected = Payment.objects.filter(
        status=Payment.Status.COMPLETED, paid_on__year=today.year, paid_on__month=today.month
    ).aggregate(s=Sum("amount"))["s"] or Decimal("0")

    return Response({
        "session": session.name if session else None,
        "date": today,
        "students_total": active.count(),
        "students_by_class": [{"name": r["name"], "students": r["students"]} for r in by_class],
        "attendance_today": {
            "present": counts.get("present", 0) + counts.get("late", 0),
            "absent": counts.get("absent", 0),
            "leave": counts.get("leave", 0),
            "sections_marked": len(marked),
            "sections_total": len(sections),
            "sections_not_marked": [f"{s.school_class.name} {s.name}" for s in sections if s.pk not in marked],
        },
        "fees": {
            "billed": str(billed), "collected": str(paid), "outstanding": str(billed - paid),
            "collected_this_month": str(month_collected),
            "overdue_invoices": invoices.filter(due_date__lt=today, status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTLY_PAID]).count(),
        },
        "pending": {
            "admissions": AdmissionApplication.objects.filter(status__in=AdmissionApplication.OPEN_STATUSES).count(),
            "upi_payments": UpiSubmission.objects.filter(status=UpiSubmission.Status.PENDING).count(),
            "concessions": Concession.objects.filter(status=Concession.Status.PENDING).count(),
        },
    })


urlpatterns = [path("dashboard/", dashboard, name="reports-dashboard")]
