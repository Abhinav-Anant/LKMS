import pytest

from academics.models import Subject
from conftest import as_user, make_user

pytestmark = pytest.mark.django_db


def create_test(client, school, subject=None, **extra):
    return client.post("/api/v1/assessments/", {
        "section": school["section"].pk, "subject": (subject or school["maths"]).pk, "name": "Unit Test 1",
        "date": school["session"].start_date.isoformat(), "max_marks": "20", **extra,
    }, format="json")


def test_subject_teacher_enters_and_publishes_marks(school):
    client = as_user(school["maths_teacher"])
    response = create_test(client, school)
    assert response.status_code == 201, response.data
    test_id = response.data["id"]
    riya, kabir = school["students"]
    saved = client.post(f"/api/v1/assessments/{test_id}/marks/", {"rows": [
        {"student": riya.pk, "marks": "18.5"}, {"student": kabir.pk, "is_absent": True},
    ]}, format="json")
    assert saved.status_code == 200, saved.data
    assert [r["marks"] for r in saved.data["rows"]] == ["18.50", None]
    assert client.post(f"/api/v1/assessments/{test_id}/publish/").data["is_published"]

    # Once published, only the principal can change marks.
    again = client.post(f"/api/v1/assessments/{test_id}/marks/", {"rows": [{"student": riya.pk, "marks": "19"}]}, format="json")
    assert again.status_code == 403


def test_marks_above_maximum_are_refused(school):
    client = as_user(school["maths_teacher"])
    test_id = create_test(client, school).data["id"]
    response = client.post(f"/api/v1/assessments/{test_id}/marks/",
                           {"rows": [{"student": school["students"][0].pk, "marks": "21"}]}, format="json")
    assert response.status_code == 400


def test_teacher_cannot_create_tests_for_subjects_they_do_not_teach(school):
    client = as_user(school["maths_teacher"])
    assert create_test(client, school, subject=Subject.objects.get(name="Hindi")).status_code == 400


def test_teachers_only_see_their_own_subjects(school):
    maths = as_user(school["maths_teacher"])
    create_test(maths, school)
    assert len(as_user(make_user("teacher", "stranger")).get("/api/v1/assessments/").data) == 0
    # The class teacher sees every subject of their class.
    assert len(as_user(school["class_teacher"]).get("/api/v1/assessments/").data) == 1


def test_office_staff_cannot_see_marks(school, client_for):
    assert client_for("office").get("/api/v1/assessments/").status_code == 403
