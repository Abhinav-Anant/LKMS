"""School-wide reports as plain tables. The staff app shows them and downloads them as CSV."""

import calendar
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from academics.models import AcademicSession, Enrollment, Section
from admissions.models import AdmissionApplication
from attendance.models import AttendanceRecord
from certificates.models import TransferCertificate
from core.permissions import Can
from exams import report as exam_report
from exams.grading import bands
from exams.models import ExamTerm
from fees.models import Invoice
from students.choices import Category, Gender

LOW_ATTENDANCE = 75


def _session(params):
    if params.get("session"):
        return get_object_or_404(AcademicSession, pk=params["session"])
    session = AcademicSession.current()
    if session is None:
        raise ValidationError({"session": "No current session is set."})
    return session


def _month(params):
    text = params.get("month") or timezone.localdate().strftime("%Y-%m")
    try:
        year, month = (int(p) for p in text.split("-"))
        start = date(year, month, 1)
    except ValueError:
        raise ValidationError({"month": "Use YYYY-MM."})
    return start, start.replace(day=calendar.monthrange(year, month)[1])


def _sections(session):
    return Section.objects.filter(session=session).select_related("school_class").order_by("school_class__order", "name")


def _label(section):
    return f"{section.school_class.name} {section.name}"


def _pct(part, whole):
    return round(100 * part / whole, 1) if whole else None


def strength(params):
    session = _session(params)
    active = Enrollment.objects.filter(session=session, status=Enrollment.Status.ACTIVE)
    by_section = defaultdict(Counter)
    for section_id, gender, category in active.values_list("section_id", "student__gender", "student__category"):
        by_section[section_id][gender] += 1
        by_section[section_id][category] += 1
        by_section[section_id]["total"] += 1
    rows = []
    for s in _sections(session):
        c = by_section[s.pk]
        rows.append({"class": _label(s), "boys": c[Gender.MALE], "girls": c[Gender.FEMALE], "other": c[Gender.OTHER],
                     "total": c["total"], **{cat.value: c[cat.value] for cat in Category}})
    columns = [("class", "Class"), ("boys", "Boys"), ("girls", "Girls"), ("other", "Other"), ("total", "Total")] + [
        (cat.value, cat.label) for cat in Category]
    return f"Student strength, {session.name}", columns, rows


def attendance(params):
    start, end = _month(params)
    records = AttendanceRecord.objects.filter(date__range=(start, end))
    per_student = defaultdict(Counter)
    per_section = defaultdict(lambda: {"days": set(), "counts": Counter()})
    for section_id, student_id, day, status in records.values_list("section_id", "student_id", "date", "status"):
        per_section[section_id]["days"].add(day)
        per_section[section_id]["counts"][status] += 1
        per_student[(section_id, student_id)][status] += 1
    low = Counter()
    for (section_id, _), c in per_student.items():
        if _pct(c["present"] + c["late"], sum(c.values())) < LOW_ATTENDANCE:
            low[section_id] += 1
    rows = []
    for s in Section.objects.filter(pk__in=per_section).select_related("school_class").order_by("school_class__order", "name"):
        c = per_section[s.pk]["counts"]
        rows.append({"class": _label(s), "days_marked": len(per_section[s.pk]["days"]), "present": c["present"] + c["late"],
                     "absent": c["absent"], "leave": c["leave"],
                     "percent": _pct(c["present"] + c["late"], sum(c.values())), "low": low[s.pk]})
    columns = [("class", "Class"), ("days_marked", "Days marked"), ("present", "Present"), ("absent", "Absent"),
               ("leave", "Leave"), ("percent", "Attendance %"), ("low", f"Students below {LOW_ATTENDANCE}%")]
    return f"Attendance by class, {start:%B %Y}", columns, rows


def low_attendance(params):
    start, end = _month(params)
    counts = defaultdict(Counter)
    for student_id, status in AttendanceRecord.objects.filter(date__range=(start, end)).values_list("student_id", "status"):
        counts[student_id][status] += 1
    low = {sid: c for sid, c in counts.items() if _pct(c["present"] + c["late"], sum(c.values())) < LOW_ATTENDANCE}
    enrollments = (Enrollment.objects.filter(student_id__in=low, session__start_date__lte=end, session__end_date__gte=start)
                   .select_related("student", "section__school_class")
                   .order_by("section__school_class__order", "section__name", "roll_number"))
    rows = []
    for e in enrollments:
        c = low[e.student_id]
        rows.append({"class": _label(e.section), "roll_number": e.roll_number, "name": e.student.full_name,
                     "admission_number": e.student.admission_number, "present": c["present"] + c["late"],
                     "marked": sum(c.values()), "percent": _pct(c["present"] + c["late"], sum(c.values()))})
    columns = [("class", "Class"), ("roll_number", "Roll"), ("name", "Student"), ("admission_number", "Adm. no."),
               ("present", "Days present"), ("marked", "Days marked"), ("percent", "Attendance %")]
    return f"Students below {LOW_ATTENDANCE}% attendance, {start:%B %Y}", columns, rows


def results(params):
    if not params.get("term"):
        raise ValidationError({"term": "Choose an exam term."})
    term = get_object_or_404(ExamTerm.objects.select_related("session"), pk=params["term"])
    scale = bands()
    rows = []
    sections = Section.objects.filter(assessments__term=term).distinct().select_related("school_class")
    for s in sections.order_by("school_class__order", "name"):
        cards = [c for c in exam_report.build(term, s, scale=scale) if c["percent"] is not None]
        grades = Counter(c["grade"] for c in cards)
        rows.append({
            "class": _label(s), "students": len(cards),
            "passed": sum(1 for c in cards if c["result"] == "Pass"),
            "needs_improvement": sum(1 for c in cards if c["result"] == "Needs improvement"),
            "average": round(sum(c["percent"] for c in cards) / len(cards), 1) if cards else None,
            "highest": max((c["percent"] for c in cards), default=None),
            "grades": ", ".join(f"{g}: {grades[g]}" for g, *_ in scale if grades[g]),
        })
    columns = [("class", "Class"), ("students", "Students with marks"), ("passed", "Passed"),
               ("needs_improvement", "Needs improvement"), ("average", "Average %"), ("highest", "Highest %"),
               ("grades", "Grades")]
    return f"Results, {term}", columns, rows


def fee_dues(params):
    session = _session(params)
    invoices = Invoice.objects.filter(session=session).exclude(status=Invoice.Status.CANCELLED).select_related("school_class")
    per_class = defaultdict(lambda: {"students": set(), "with_dues": set(), "billed": Decimal("0"),
                                     "concession": Decimal("0"), "paid": Decimal("0"), "due": Decimal("0"),
                                     "order": 0})
    for inv in invoices:
        row = per_class[inv.school_class.name]
        row["order"] = inv.school_class.order
        row["students"].add(inv.student_id)
        row["billed"] += inv.gross_amount
        row["concession"] += inv.concession_amount
        row["paid"] += inv.amount_paid
        row["due"] += inv.balance
        if inv.balance > 0:
            row["with_dues"].add(inv.student_id)
    rows = [{"class": name, "students": len(r["students"]), "billed": r["billed"], "concession": r["concession"],
             "collected": r["paid"], "outstanding": r["due"], "students_with_dues": len(r["with_dues"])}
            for name, r in sorted(per_class.items(), key=lambda kv: kv[1]["order"])]
    columns = [("class", "Class"), ("students", "Students billed"), ("billed", "Billed (Rs)"),
               ("concession", "Concession (Rs)"), ("collected", "Collected (Rs)"), ("outstanding", "Outstanding (Rs)"),
               ("students_with_dues", "Students with dues")]
    return f"Fees by class, {session.name}", columns, rows


def admissions(params):
    session = _session(params)
    counts = defaultdict(Counter)
    qs = AdmissionApplication.objects.filter(session=session).values_list("class_applied__name", "class_applied__order",
                                                                          "status")
    order = {}
    for name, position, status in qs:
        counts[name][status] += 1
        order[name] = position
    statuses = list(AdmissionApplication.Status)
    rows = [{"class": name, **{s.value: counts[name][s.value] for s in statuses}, "total": sum(counts[name].values())}
            for name in sorted(counts, key=order.get)]
    columns = [("class", "Class")] + [(s.value, s.label) for s in statuses] + [("total", "Total")]
    return f"Admission applications, {session.name}", columns, rows


def tc_register(params):
    session = _session(params)
    tcs = (TransferCertificate.objects.filter(number__isnull=False)
           .filter(Q(issued_on__range=(session.start_date, session.end_date)))
           .select_related("student").order_by("number"))
    rows = [{"number": tc.number, "issued_on": tc.issued_on, "name": tc.details.get("name", tc.student.full_name),
             "admission_number": tc.student.admission_number, "class": tc.details.get("last_class", ""),
             "reason": tc.reason, "status": tc.get_status_display()} for tc in tcs]
    columns = [("number", "TC no."), ("issued_on", "Issued on"), ("name", "Student"), ("admission_number", "Adm. no."),
               ("class", "Last class"), ("reason", "Reason"), ("status", "Status")]
    return f"Transfer certificate register, {session.name}", columns, rows


REPORTS = {
    # name: (title in the list, parameters, builder)
    "strength": ("Student strength by class, gender and category", ["session"], strength),
    "attendance": ("Attendance by class for a month", ["month"], attendance),
    "low-attendance": (f"Students below {LOW_ATTENDANCE}% attendance in a month", ["month"], low_attendance),
    "results": ("Exam results by class", ["term"], results),
    "fee-dues": ("Fees billed, collected and outstanding by class", ["session"], fee_dues),
    "admissions": ("Admission applications by class and status", ["session"], admissions),
    "tc-register": ("Transfer certificate register", ["session"], tc_register),
}


class ReportInfoSerializer(serializers.Serializer):
    name = serializers.CharField()
    title = serializers.CharField()
    params = serializers.ListField(child=serializers.CharField())


class ColumnSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()


class ReportTableSerializer(serializers.Serializer):
    name = serializers.CharField()
    title = serializers.CharField()
    columns = ColumnSerializer(many=True)
    rows = serializers.ListField(child=serializers.DictField())


def _plain(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


@extend_schema(responses=ReportInfoSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsAuthenticated, Can("reports.view")])
def report_list(request):
    return Response([{"name": k, "title": title, "params": p} for k, (title, p, _) in REPORTS.items()])


@extend_schema(parameters=[OpenApiParameter("session", int), OpenApiParameter("month", str, description="YYYY-MM"),
                           OpenApiParameter("term", int)], responses=ReportTableSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated, Can("reports.view")])
def report_table(request, name):
    if name not in REPORTS:
        raise NotFound("No such report.")
    title, columns, rows = REPORTS[name][2](request.query_params)
    return Response({
        "name": name, "title": title, "columns": [{"key": k, "label": label} for k, label in columns],
        "rows": [{k: _plain(v) for k, v in row.items()} for row in rows],
    })


urlpatterns = [
    path("tables/", report_list, name="report-list"),
    path("tables/<slug:name>/", report_table, name="report-table"),
]
