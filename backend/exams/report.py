"""Work out what goes on a report card from the marks entered in Phase 3."""

from collections import Counter, defaultdict
from decimal import Decimal

from academics.models import Enrollment
from assessments.models import Assessment, Mark
from attendance.models import AttendanceRecord

from .grading import bands, grade_for, percent
from .models import ReportCardEntry


def num(value):
    """18.50 -> "18.5", 20.00 -> "20"."""
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def enrollment_for(term, student):
    return (Enrollment.objects.filter(student=student, session=term.session)
            .select_related("section__school_class", "section__class_teacher").first())


def term_assessments(term, section):
    return list(Assessment.objects.filter(term=term, section=section).select_related("subject")
                .order_by("subject__order", "date", "name"))


def _guardian_names(student):
    names = {"father": "", "mother": ""}
    for link in student.guardian_links.select_related("guardian"):
        if link.relationship in names and not names[link.relationship]:
            names[link.relationship] = link.guardian.full_name
    return names


def build(term, section, students=None, scale=None):
    """Report card data for every active student of `section` (or only `students`)."""
    scale = scale or bands()
    assessments = term_assessments(term, section)
    columns = []  # assessment names in date order, e.g. ["Unit Test 1", "Half-yearly"]
    for a in sorted(assessments, key=lambda a: (a.date, a.name)):
        if a.name not in columns:
            columns.append(a.name)

    enrollments = (Enrollment.objects.filter(section=section).select_related("student")
                   .order_by("roll_number", "student__first_name"))
    if students is None:
        enrollments = enrollments.exclude(status=Enrollment.Status.LEFT)
    else:  # a named student keeps their report card after leaving (e.g. a TC issued later)
        enrollments = enrollments.filter(student__in=students)

    marks = defaultdict(dict)
    for m in Mark.objects.filter(assessment__in=assessments):
        marks[m.student_id][m.assessment_id] = m
    attendance = defaultdict(Counter)
    for student_id, status in AttendanceRecord.objects.filter(
        section=section, date__range=(term.start_date, term.end_date)
    ).values_list("student_id", "status"):
        attendance[student_id][status] += 1
    entries = {e.student_id: e for e in ReportCardEntry.objects.filter(term=term)}

    cards = []
    for e in enrollments:
        student = e.student
        by_subject = {}
        for a in assessments:
            row = by_subject.setdefault(a.subject_id, {
                "subject": a.subject.name, "scores": {}, "obtained": Decimal("0"), "maximum": Decimal("0"), "entered": 0,
            })
            m = marks[student.pk].get(a.pk)
            if m and m.is_absent:
                row["scores"][a.name] = f"AB/{num(a.max_marks)}"
            elif m and m.marks is not None:
                row["scores"][a.name] = f"{num(m.marks)}/{num(a.max_marks)}"
                row["obtained"] += m.marks
            else:
                row["scores"][a.name] = "-"
                continue  # not entered yet: leave it out of the total
            row["maximum"] += a.max_marks
            row["entered"] += 1
        subjects = []
        for row in by_subject.values():
            row["percent"] = percent(row["obtained"], row["maximum"])
            row["grade"], row["is_pass"] = grade_for(row["percent"], scale)
            subjects.append(row)
        obtained = sum((s["obtained"] for s in subjects), Decimal("0"))
        maximum = sum((s["maximum"] for s in subjects), Decimal("0"))
        overall = percent(obtained, maximum)
        grade, is_pass = grade_for(overall, scale)
        failed = [s["subject"] for s in subjects if s["is_pass"] is False]
        counts = attendance[student.pk]
        marked = sum(counts.values())
        entry = entries.get(student.pk)
        cards.append({
            "student": student, "enrollment": e, "subjects": subjects, "columns": columns,
            "obtained": obtained, "maximum": maximum, "percent": overall, "grade": grade,
            "result": "" if overall is None else ("Pass" if is_pass and not failed else "Needs improvement"),
            "failed_subjects": failed,
            "attendance": {"present": counts["present"] + counts["late"], "marked": marked},
            "remark": entry.remark if entry else "", "co_scholastic": entry.co_scholastic if entry else {},
            "guardians": _guardian_names(student),
        })
    return cards


def summary_row(card):
    """The flat row the class result sheet and API show for one student."""
    e = card["enrollment"]
    return {
        "student": card["student"].pk, "roll_number": e.roll_number, "name": card["student"].full_name,
        "admission_number": card["student"].admission_number,
        "subjects": [{"subject": s["subject"], "percent": s["percent"], "grade": s["grade"]} for s in card["subjects"]],
        "obtained": card["obtained"], "maximum": card["maximum"], "percent": card["percent"], "grade": card["grade"],
        "result": card["result"], "attendance_present": card["attendance"]["present"],
        "attendance_marked": card["attendance"]["marked"], "remark": card["remark"], "co_scholastic": card["co_scholastic"],
    }
