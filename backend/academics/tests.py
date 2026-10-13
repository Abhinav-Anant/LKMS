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
