
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from academics.models import Enrollment
from admissions.models import AdmissionApplication, DocumentType
from conftest import pdf_file, png_file
from core.models import AuditLog
from students.models import Guardian, Student

pytestmark = pytest.mark.django_db


def apply(public, data):
    response = public.post("/api/v1/admissions/public/apply/", data, format="json")
    assert response.status_code == 201, response.data
    return response.data


def upload(public, number, token, code, file):
    doc_type = DocumentType.objects.get(code=code)
    return public.post(
        f"/api/v1/admissions/public/{number}/documents/",
        {"document_type": doc_type.pk, "file": file},
        format="multipart",
        HTTP_X_APPLICATION_TOKEN=token,
    )


def upload_required(public, created):
    for doc in created["required_documents"]:
        file = png_file() if doc["code"] == "photo" else pdf_file()
        response = upload(public, created["application_number"], created["access_token"], doc["code"], file)
        assert response.status_code == 201, response.data


def verify_all(staff, application):
    for document in application.current_documents():
        response = staff.post(f"/api/v1/admissions/documents/{document.pk}/verify/", {"verification": "verified"}, format="json")
        assert response.status_code == 200, response.data


# ----- public form -----

def test_parent_can_apply_and_gets_number_and_code(public, application_data):
    created = apply(public, application_data)
    application = AdmissionApplication.objects.get()
    assert created["application_number"] == application.application_number
    assert application.application_number.startswith("SCH-2027-28-")
    assert application.father_phone == "9829012345"  # +91 and spaces stripped
    assert application.check_token(created["access_token"])
    assert application.consent_given_at is not None
    assert {d["code"] for d in created["required_documents"]} >= {"birth-certificate", "photo"}


def test_form_filled_by_a_bot_is_refused(public, application_data):
    response = public.post("/api/v1/admissions/public/apply/", {**application_data, "website": "http://spam.example"}, format="json")
    assert response.status_code == 400
    assert not AdmissionApplication.objects.exists()


def test_application_numbers_are_sequential(public, application_data):
    first = apply(public, application_data)["application_number"]
    second = apply(public, application_data)["application_number"]
    assert first.endswith("00001") and second.endswith("00002")


def test_declaration_is_required(public, application_data):
    application_data["declaration_accepted"] = False
    response = public.post("/api/v1/admissions/public/apply/", application_data, format="json")
    assert response.status_code == 400
    assert "declaration_accepted" in response.data


def test_closed_session_is_refused(public, application_data, seeded):
    seeded["open_session"].admissions_open = False
    seeded["open_session"].save()
    response = public.post("/api/v1/admissions/public/apply/", application_data, format="json")
    assert response.status_code == 400


def test_age_rule_for_nursery(public, application_data, seeded):
    application_data["class_applied"] = seeded["nursery"].pk
    application_data["date_of_birth"] = "2026-01-01"  # one year old on 1 April 2027
    response = public.post("/api/v1/admissions/public/apply/", application_data, format="json")
    assert response.status_code == 400
    assert "date_of_birth" in response.data


def test_bad_mobile_number_is_refused(public, application_data):
    application_data["father_phone"] = "12345"
    response = public.post("/api/v1/admissions/public/apply/", application_data, format="json")
    assert response.status_code == 400
    assert "father_phone" in response.data


# ----- documents -----

def test_upload_needs_the_access_code(public, application_data):
    created = apply(public, application_data)
    response = upload(public, created["application_number"], "wrong", "birth-certificate", pdf_file())
    assert response.status_code == 404


def test_upload_rejects_a_file_pretending_to_be_pdf(public, application_data):
    created = apply(public, application_data)
    fake = SimpleUploadedFile("cert.pdf", b"MZ\x90\x00 this is an exe", content_type="application/pdf")
    response = upload(public, created["application_number"], created["access_token"], "birth-certificate", fake)
    assert response.status_code == 400
    assert "file" in response.data


def test_photo_must_be_an_image(public, application_data):
    created = apply(public, application_data)
    response = upload(public, created["application_number"], created["access_token"], "photo", pdf_file())
    assert response.status_code == 400


def test_reupload_replaces_previous_document(public, application_data):
    created = apply(public, application_data)
    for _ in range(2):
        upload(public, created["application_number"], created["access_token"], "birth-certificate", pdf_file())
    application = AdmissionApplication.objects.get()
    assert application.documents.count() == 2
    assert application.current_documents().count() == 1


def test_documents_are_not_publicly_reachable(public, client_for, application_data):
    created = apply(public, application_data)
    upload(public, created["application_number"], created["access_token"], "birth-certificate", pdf_file())
    document = AdmissionApplication.objects.get().documents.get()
    assert public.get(f"/api/v1/admissions/documents/{document.pk}/file/").status_code == 401
    assert client_for("teacher").get(f"/api/v1/admissions/documents/{document.pk}/file/").status_code == 403

    response = client_for("office").get(f"/api/v1/admissions/documents/{document.pk}/file/")
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert b"".join(response.streaming_content).startswith(b"%PDF")
    assert AuditLog.objects.filter(action="admission.document_viewed").exists()


# ----- tracking -----

def test_tracking_needs_matching_dob_and_phone(public, application_data):
    created = apply(public, application_data)
    number = created["application_number"]
    ok = public.post("/api/v1/admissions/public/track/", {"application_number": number, "date_of_birth": "2021-05-10", "phone": "98290 54321"}, format="json")
    assert ok.status_code == 200
    assert ok.data["status"] == "submitted"
    assert "father_name" not in ok.data and "address_line" not in ok.data

    wrong_phone = public.post("/api/v1/admissions/public/track/", {"application_number": number, "date_of_birth": "2021-05-10", "phone": "9000000000"}, format="json")
    wrong_dob = public.post("/api/v1/admissions/public/track/", {"application_number": number, "date_of_birth": "2021-05-11", "phone": "9829054321"}, format="json")
    assert wrong_phone.status_code == wrong_dob.status_code == 404


# ----- staff workflow -----

def test_teachers_cannot_see_applications(public, client_for, application_data):
    apply(public, application_data)
    assert client_for("teacher").get("/api/v1/admissions/applications/").status_code == 403
    assert client_for("office").get("/api/v1/admissions/applications/").data["count"] == 1


def test_aadhaar_is_masked_for_office_staff(public, client_for, application_data):
    application_data["aadhaar_number"] = "123456789012"
    apply(public, application_data)
    pk = AdmissionApplication.objects.get().pk
    assert client_for("office").get(f"/api/v1/admissions/applications/{pk}/").data["aadhaar_number"] == "XXXX-XXXX-9012"
    assert client_for("principal").get(f"/api/v1/admissions/applications/{pk}/").data["aadhaar_number"] == "123456789012"


def test_parent_aadhaar_is_required_12_digits_and_masked(public, client_for, application_data):
    for bad in ("", "12345", "1234 5678 901X"):
        response = public.post("/api/v1/admissions/public/apply/", {**application_data, "parent_aadhaar_number": bad}, format="json")
        assert response.status_code == 400 and "parent_aadhaar_number" in response.data, bad
    del application_data["parent_aadhaar_number"]
    response = public.post("/api/v1/admissions/public/apply/", application_data, format="json")
    assert "parent_aadhaar_number" in response.data

    apply(public, {**application_data, "parent_aadhaar_number": "2345-6789-0123"})
    pk = AdmissionApplication.objects.get().pk
    assert client_for("office").get(f"/api/v1/admissions/applications/{pk}/").data["parent_aadhaar_number"] == "XXXX-XXXX-0123"
    assert client_for("principal").get(f"/api/v1/admissions/applications/{pk}/").data["parent_aadhaar_number"] == "234567890123"
    assert "parent_aadhaar_number" not in client_for("office").get("/api/v1/admissions/applications/").data["results"][0]


def test_request_documents_needs_a_message(public, client_for, application_data):
    apply(public, application_data)
    pk = AdmissionApplication.objects.get().pk
    office = client_for("office")
    url = f"/api/v1/admissions/applications/{pk}/transition/"
    assert office.post(url, {"status": "documents_requested"}, format="json").status_code == 400
    response = office.post(url, {"status": "documents_requested", "message": "Please upload a clearer birth certificate."}, format="json")
    assert response.status_code == 200
    assert response.data["status"] == "documents_requested"


def test_office_cannot_reject_or_approve(public, client_for, application_data):
    apply(public, application_data)
    pk = AdmissionApplication.objects.get().pk
    office = client_for("office")
    assert office.post(f"/api/v1/admissions/applications/{pk}/transition/", {"status": "rejected", "message": "No seats"}, format="json").status_code == 403
    assert office.post(f"/api/v1/admissions/applications/{pk}/approve/", {}, format="json").status_code == 403


def test_approval_waits_for_verified_documents(public, client_for, application_data):
    created = apply(public, application_data)
    pk = AdmissionApplication.objects.get().pk
    principal = client_for("principal")
    response = principal.post(f"/api/v1/admissions/applications/{pk}/approve/", {}, format="json")
    assert response.status_code == 400
    assert "Birth certificate" in str(response.data)

    upload_required(public, created)
    verify_all(client_for("office"), AdmissionApplication.objects.get())
    response = principal.post(f"/api/v1/admissions/applications/{pk}/approve/", {}, format="json")
    assert response.status_code == 200
    assert response.data["status"] == "approved"


def test_rejecting_a_document_needs_a_reason(public, client_for, application_data):
    created = apply(public, application_data)
    upload(public, created["application_number"], created["access_token"], "birth-certificate", pdf_file())
    document = AdmissionApplication.objects.get().documents.get()
    office = client_for("office")
    url = f"/api/v1/admissions/documents/{document.pk}/verify/"
    assert office.post(url, {"verification": "rejected"}, format="json").status_code == 400
    assert office.post(url, {"verification": "rejected", "note": "Photo is blurred"}, format="json").status_code == 200


def approved_application(public, client_for, data):
    created = apply(public, data)
    upload_required(public, created)
    application = AdmissionApplication.objects.get(application_number=created["application_number"])
    verify_all(client_for("office"), application)
    client_for("principal").post(f"/api/v1/admissions/applications/{application.pk}/approve/", {}, format="json")
    return application


def test_admit_creates_student_guardians_and_enrollment(public, client_for, application_data, section):
    application = approved_application(public, client_for, application_data)
    principal = client_for("principal")
    response = principal.post(f"/api/v1/admissions/applications/{application.pk}/admit/", {"section": section.pk}, format="json")
    assert response.status_code == 201, response.data

    student = Student.objects.get()
    assert student.admission_number == "0001"
    assert student.application == application
    assert bool(student.photo)  # copied from the uploaded photo
    assert {link.relationship for link in student.guardian_links.all()} == {"father", "mother"}
    assert student.guardian_links.get(is_primary_contact=True).relationship == "father"
    enrollment = Enrollment.objects.get(student=student)
    assert enrollment.section == section and enrollment.session == section.session

    application.refresh_from_db()
    assert application.status == "admitted"
    assert "0001" in application.status_message
    assert list(application.history.values_list("to_status", flat=True)) == ["submitted", "approved", "admitted"]

    # cannot admit twice
    again = principal.post(f"/api/v1/admissions/applications/{application.pk}/admit/", {"section": section.pk}, format="json")
    assert again.status_code == 400


def test_siblings_share_parent_records(public, client_for, application_data, section):
    first = approved_application(public, client_for, application_data)
    principal = client_for("principal")
    principal.post(f"/api/v1/admissions/applications/{first.pk}/admit/", {"section": section.pk}, format="json")

    sibling = {**application_data, "first_name": "Diya", "gender": "F", "date_of_birth": "2021-08-01"}
    second = approved_application(public, client_for, sibling)
    principal.post(f"/api/v1/admissions/applications/{second.pk}/admit/", {"section": section.pk}, format="json")

    assert Student.objects.count() == 2
    assert Guardian.objects.count() == 2  # same father and mother, not four records
    father = Guardian.objects.get(full_name="Rohit Sharma")
    assert father.students.count() == 2
    assert sorted(Student.objects.values_list("admission_number", flat=True)) == ["0001", "0002"]


def test_admit_checks_section_class_and_capacity(public, client_for, application_data, section, seeded):
    application = approved_application(public, client_for, application_data)
    principal = client_for("principal")
    from academics.models import Section

    wrong = Section.objects.get(session=seeded["open_session"], school_class=seeded["nursery"])
    assert principal.post(f"/api/v1/admissions/applications/{application.pk}/admit/", {"section": wrong.pk}, format="json").status_code == 400

    section.capacity = 0
    section.save()
    response = principal.post(f"/api/v1/admissions/applications/{application.pk}/admit/", {"section": section.pk}, format="json")
    assert response.status_code == 400
    assert "full" in str(response.data)


def test_decided_application_cannot_be_edited_or_receive_documents(public, client_for, application_data):
    created = apply(public, application_data)
    pk = AdmissionApplication.objects.get().pk
    principal = client_for("principal")
    principal.post(f"/api/v1/admissions/applications/{pk}/transition/", {"status": "rejected", "message": "Class is full"}, format="json")
    assert principal.patch(f"/api/v1/admissions/applications/{pk}/", {"city": "Ajmer"}, format="json").status_code == 400
    assert upload(public, created["application_number"], created["access_token"], "birth-certificate", pdf_file()).status_code == 400
