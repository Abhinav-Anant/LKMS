from datetime import timedelta

import pytest

from academics.models import Subject
from assessments.models import Assessment, Mark
from attendance.models import AttendanceRecord
from conftest import as_user, make_user
from exams.grading import grade_for
from exams.models import ExamTerm, GradeBand
from messaging.models import OutgoingMessage
from users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def term(school):
    s = school["session"]
    return ExamTerm.objects.create(session=s, name="Half-yearly", start_date=s.start_date,
                                   end_date=s.start_date + timedelta(days=180))


@pytest.fixture
def marked(school, term):
    """Maths: Unit Test (20) and Half-yearly (80); Hindi: Half-yearly (50). Riya does well, Kabir fails Hindi."""
    section, (riya, kabir) = school["section"], school["students"]
    hindi = Subject.objects.get(name="Hindi")
    tests = {}
    for subject, name, max_marks, day in [(school["maths"], "Unit Test 1", 20, 10), (school["maths"], "Half-yearly", 80, 150),
                                          (hindi, "Half-yearly", 50, 151)]:
        tests[(subject.name, name)] = Assessment.objects.create(
            section=section, subject=subject, term=term, name=name, max_marks=max_marks, is_published=True,
            date=school["session"].start_date + timedelta(days=day))
    for (subject, name), scores in {("Mathematics", "Unit Test 1"): (18, 10), ("Mathematics", "Half-yearly"): (72, 40),
                                    ("Hindi", "Half-yearly"): (45, 10)}.items():
        for student, score in zip((riya, kabir), scores):
            Mark.objects.create(assessment=tests[(subject, name)], student=student, marks=score)
    for i in range(4):
        day = school["session"].start_date + timedelta(days=i)
        AttendanceRecord.objects.create(student=riya, section=section, date=day, status="present")
        AttendanceRecord.objects.create(student=kabir, section=section, date=day, status="absent" if i else "present")
    return tests


def test_default_grade_scale():
    assert grade_for(91) == ("A+", True)
    assert grade_for(33) == ("D", True)
    assert grade_for(32.99) == ("E", False)
    assert grade_for(None) == ("", None)


def test_saved_grade_scale_replaces_the_default():
    GradeBand.objects.create(grade="P", min_percent=40, is_pass=True)
    GradeBand.objects.create(grade="F", min_percent=0, is_pass=False)
    assert grade_for(39) == ("F", False)


def test_class_result_sheet(school, term, marked):
    sheet = as_user(school["class_teacher"]).get(f"/api/v1/exams/terms/{term.pk}/results/?section={school['section'].pk}")
    assert sheet.status_code == 200, sheet.data
    riya, kabir = sheet.data["rows"]
    assert riya["percent"] == "90.00" and riya["grade"] == "A+" and riya["result"] == "Pass"
    assert riya["attendance_present"] == 4 and riya["attendance_marked"] == 4
    # Kabir: maths 50/100 (C), Hindi 10/50 = 20% (E): needs improvement.
    assert [(s["subject"], s["grade"]) for s in kabir["subjects"]] == [("Hindi", "E"), ("Mathematics", "C")]
    assert kabir["result"] == "Needs improvement" and kabir["attendance_present"] == 1


def test_only_teachers_of_the_section_see_its_results(school, term, marked):
    url = f"/api/v1/exams/terms/{term.pk}/results/?section={school['section'].pk}"
    assert as_user(school["maths_teacher"]).get(url).status_code == 200
    assert as_user(make_user("teacher", "stranger")).get(url).status_code == 403


def test_class_teacher_writes_remarks_but_subject_teacher_cannot(school, term, marked):
    riya = school["students"][0]
    url = f"/api/v1/exams/terms/{term.pk}/remarks/?section={school['section'].pk}"
    body = {"rows": [{"student": riya.pk, "remark": "Very attentive.", "co_scholastic": {"Discipline": "A"}}]}
    assert as_user(school["maths_teacher"]).post(url, body, format="json").status_code == 403
    saved = as_user(school["class_teacher"]).post(url, body, format="json")
    assert saved.status_code == 200, saved.data
    assert saved.data["rows"][0]["remark"] == "Very attentive."
    bad = as_user(school["class_teacher"]).post(url, {"rows": [{"student": riya.pk, "co_scholastic": {"Discipline": "Z"}}]},
                                                format="json")
    assert bad.status_code == 400


def test_report_card_pdfs(school, term, marked):
    client = as_user(school["class_teacher"])
    one = client.get(f"/api/v1/exams/terms/{term.pk}/report-cards/?section={school['section'].pk}&student={school['students'][0].pk}")
    assert one.status_code == 200 and one["Content-Type"] == "application/pdf"
    assert one.content.startswith(b"%PDF")
    everyone = client.get(f"/api/v1/exams/terms/{term.pk}/report-cards/?section={school['section'].pk}")
    pages = lambda pdf: pdf.content.count(b"/Type /Page") - pdf.content.count(b"/Type /Pages")  # noqa: E731
    assert pages(one) == 1 and pages(everyone) == 2


def test_publishing_needs_every_test_published_then_tells_parents(school, term, marked, client_for, settings):
    settings.WHATSAPP_ENABLED = True
    principal = client_for("principal")
    marked[("Hindi", "Half-yearly")].is_published = False
    marked[("Hindi", "Half-yearly")].save()
    assert principal.post(f"/api/v1/exams/terms/{term.pk}/publish/").status_code == 400
    marked[("Hindi", "Half-yearly")].is_published = True
    marked[("Hindi", "Half-yearly")].save()
    published = principal.post(f"/api/v1/exams/terms/{term.pk}/publish/")
    assert published.status_code == 200 and published.data["is_published"]
    messages = OutgoingMessage.objects.filter(event="report_card.published")
    assert messages.count() == 2 and "Half-yearly" in messages.first().text
    # Withdrawing and publishing again does not message the families twice.
    principal.post(f"/api/v1/exams/terms/{term.pk}/unpublish/")
    principal.post(f"/api/v1/exams/terms/{term.pk}/publish/")
    assert messages.count() == 2


def test_teachers_cannot_create_or_publish_terms(school, term):
    teacher = as_user(school["class_teacher"])
    assert teacher.get("/api/v1/exams/terms/").status_code == 200
    assert teacher.post(f"/api/v1/exams/terms/{term.pk}/publish/").status_code == 403
    assert teacher.post("/api/v1/exams/terms/", {}, format="json").status_code == 403


def test_term_dates_must_fit_the_session(school, client_for):
    s = school["session"]
    response = client_for("principal").post("/api/v1/exams/terms/", {
        "session": s.pk, "name": "Annual", "start_date": s.start_date.isoformat(),
        "end_date": (s.end_date + timedelta(days=5)).isoformat(),
    }, format="json")
    assert response.status_code == 400


def test_test_and_term_must_share_a_session(school, term, seeded):
    from academics.models import AcademicSession

    other = AcademicSession.objects.exclude(pk=school["session"].pk).first()
    wrong = ExamTerm.objects.create(session=other, name="Annual", start_date=other.start_date, end_date=other.end_date)
    response = as_user(school["maths_teacher"]).post("/api/v1/assessments/", {
        "section": school["section"].pk, "subject": school["maths"].pk, "term": wrong.pk, "name": "UT",
        "date": school["session"].start_date.isoformat(), "max_marks": "20",
    }, format="json")
    assert response.status_code == 400 and "term" in response.data


def test_parent_sees_only_published_report_cards(school, term, marked):
    parent = User.objects.create_user(username="parent-9829011111", role="parent", phone="9829011111")
    client = as_user(parent)
    riya = school["students"][0]
    assert client.get(f"/api/v1/parent/children/{riya.pk}/report-cards/").data == []
    assert client.get(f"/api/v1/parent/children/{riya.pk}/report-cards/{term.pk}/").status_code == 404
    term.is_published = True
    term.save()
    cards = client.get(f"/api/v1/parent/children/{riya.pk}/report-cards/").data
    assert [c["name"] for c in cards] == ["Half-yearly"]
    pdf = client.get(f"/api/v1/parent/children/{riya.pk}/report-cards/{term.pk}/")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")



def test_report_card_stays_available_after_the_student_leaves(school, term, marked):
    from academics.models import Enrollment

    riya = school["students"][0]
    Enrollment.objects.filter(student=riya).update(status=Enrollment.Status.LEFT)
    client = as_user(school["class_teacher"])
    sheet = client.get(f"/api/v1/exams/terms/{term.pk}/results/?section={school['section'].pk}")
    assert [r["name"] for r in sheet.data["rows"]] == ["Kabir Verma"]
    one = client.get(f"/api/v1/exams/terms/{term.pk}/report-cards/?section={school['section'].pk}&student={riya.pk}")
    assert one.status_code == 200
