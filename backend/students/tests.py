import pytest

from admissions.models import AdmissionApplication
from admissions.tests import approved_application
from core.models import AuditLog, SchoolProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def student(public, client_for, application_data, section):
    application_data["aadhaar_number"] = "123456789012"
    application = approved_application(public, client_for, application_data)
    client_for("principal").post(f"/api/v1/admissions/applications/{application.pk}/admit/", {"section": section.pk}, format="json")
    return AdmissionApplication.objects.get(pk=application.pk).student


def test_student_list_shows_current_class(client_for, student, section):
    response = client_for("office").get("/api/v1/students/")
    assert response.status_code == 200
    row = response.data["results"][0]
    assert row["admission_number"] == student.admission_number


def test_search_by_parent_phone(client_for, student):
    response = client_for("office").get("/api/v1/students/", {"search": "9829012345"})
    assert response.data["count"] == 1


def test_teacher_cannot_list_students_yet(client_for, student):
    assert client_for("teacher").get("/api/v1/students/").status_code == 403


def test_viewing_a_student_is_audited_and_aadhaar_masked(client_for, student):
    response = client_for("office").get(f"/api/v1/students/{student.pk}/")
    assert response.status_code == 200
    assert response.data["aadhaar_number"] == "XXXX-XXXX-9012"
    assert len(response.data["guardians"]) == 2
    assert AuditLog.objects.filter(action="student.viewed", object_id=str(student.pk)).exists()


def test_admission_number_is_read_only(client_for, student):
    response = client_for("office").patch(f"/api/v1/students/{student.pk}/", {"admission_number": "9999", "city": "Ajmer"}, format="json")
    assert response.status_code == 200
    student.refresh_from_db()
    assert student.admission_number == "0001" and student.city == "Ajmer"


def test_students_cannot_be_deleted(client_for, student):
    assert client_for("admin").delete(f"/api/v1/students/{student.pk}/").status_code == 405


def test_photo_is_served_privately(public, client_for, student):
    assert public.get(f"/api/v1/students/{student.pk}/photo/").status_code == 401
    response = client_for("office").get(f"/api/v1/students/{student.pk}/photo/")
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"


def test_admission_number_format_is_configurable(db):
    profile = SchoolProfile.get()
    profile.admission_number_prefix = "LK/"
    profile.next_admission_number = 250
    profile.save()
    assert SchoolProfile.allocate_admission_number() == "LK/0250"
    assert SchoolProfile.allocate_admission_number() == "LK/0251"
