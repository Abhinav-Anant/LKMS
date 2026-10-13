import pytest

from academics.models import AcademicSession

pytestmark = pytest.mark.django_db


def test_admission_options_are_public(public, seeded):
    data = public.get("/api/v1/academics/admission-options/").data
    assert [s["name"] for s in data["sessions"]] == [seeded["open_session"].name]
    assert len(data["classes"]) == 11


def test_only_one_current_session(seeded):
    upcoming = seeded["open_session"]
    upcoming.is_current = True
    upcoming.save()
    assert list(AcademicSession.objects.filter(is_current=True)) == [upcoming]


def test_teacher_can_read_but_not_change_classes(client_for, seeded):
    teacher = client_for("teacher")
    assert teacher.get("/api/v1/academics/classes/").status_code == 200
    assert teacher.post("/api/v1/academics/classes/", {"name": "Class 9", "code": "9", "order": 20}, format="json").status_code == 403
    assert client_for("principal").post("/api/v1/academics/classes/", {"name": "Class 9", "code": "9", "order": 20}, format="json").status_code == 201


def test_section_strength_counts_active_students(client_for, seeded):
    response = client_for("office").get("/api/v1/academics/sections/", {"session": seeded["open_session"].pk})
    assert response.status_code == 200
    assert all(row["strength"] == 0 for row in response.data["results"])


def test_teacher_sees_only_own_sections_and_timetable(school):
    from academics.models import PeriodSlot, TimetableEntry
    from conftest import as_user, make_user

    TimetableEntry.objects.create(section=school["section"], weekday=1, period=PeriodSlot.objects.get(number=1),
                                  subject=school["maths"], teacher=school["maths_teacher"])
    maths = as_user(school["maths_teacher"])
    sections = maths.get("/api/v1/academics/my-sections/").data
    assert [s["label"] for s in sections] == ["Class 1 A"]
    assert sections[0]["subjects"] == [{"id": school["maths"].pk, "name": "Mathematics"}] and not sections[0]["is_class_teacher"]
    assert len(maths.get("/api/v1/academics/my-timetable/").data) == 1
    assert as_user(make_user("teacher", "new")).get("/api/v1/academics/my-sections/").data == []


def test_timetable_refuses_a_teacher_in_two_places_at_once(school, client_for):
    from academics.models import PeriodSlot, Section

    other = Section.objects.filter(session=school["session"]).exclude(pk=school["section"].pk).first()
    principal = client_for("principal")
    period = PeriodSlot.objects.get(number=2)
    first = {"section": school["section"].pk, "weekday": 2, "period": period.pk, "subject": school["maths"].pk,
             "teacher": school["maths_teacher"].pk}
    assert principal.post("/api/v1/academics/timetable/", first, format="json").status_code == 201
    clash = principal.post("/api/v1/academics/timetable/", {**first, "section": other.pk}, format="json")
    assert clash.status_code == 400
