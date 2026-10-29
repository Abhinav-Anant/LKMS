"""Admission workflow. Views stay thin; every state change goes through here."""

import secrets

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from academics.models import Enrollment, Section
from core import audit
from core.models import SchoolProfile
from core.notify import notify
from core.permissions import has_capability
from students.models import Guardian, Student, StudentGuardian

from .models import AdmissionApplication, ApplicationDocument, ApplicationStatusChange, hash_token

S = AdmissionApplication.Status

# Moves made with `transition()`. Approval and admission have their own functions
# because they carry extra checks.
TRANSITIONS = {
    S.SUBMITTED: {S.UNDER_REVIEW, S.DOCUMENTS_REQUESTED, S.REJECTED, S.WITHDRAWN},
    S.UNDER_REVIEW: {S.DOCUMENTS_REQUESTED, S.REJECTED, S.WITHDRAWN},
    S.DOCUMENTS_REQUESTED: {S.UNDER_REVIEW, S.REJECTED, S.WITHDRAWN},
    S.APPROVED: {S.REJECTED, S.WITHDRAWN},
}
DECISION_STATUSES = {S.REJECTED}


def age_on(date_of_birth, on_date):
    return on_date.year - date_of_birth.year - ((on_date.month, on_date.day) < (date_of_birth.month, date_of_birth.day))


def check_age(session, school_class, date_of_birth):
    age = age_on(date_of_birth, session.effective_age_cutoff)
    cutoff = session.effective_age_cutoff.strftime("%d %b %Y")
    if school_class.min_age_years is not None and age < school_class.min_age_years:
        raise ValidationError({"date_of_birth": f"{school_class.name} needs the child to be at least {school_class.min_age_years} on {cutoff}."})
    if school_class.max_age_years is not None and age > school_class.max_age_years:
        raise ValidationError({"date_of_birth": f"{school_class.name} is for children up to {school_class.max_age_years} on {cutoff}."})


def _log(application, from_status, to_status, user=None, message=""):
    ApplicationStatusChange.objects.create(
        application=application,
        from_status=from_status,
        to_status=to_status,
        changed_by=user if user is not None and user.is_authenticated else None,
        message=message,
    )


@transaction.atomic
def create_application(request, data):
    """Create an application from validated data. Returns (application, access_token)."""
    session = data["session"]
    if not session.admissions_open:
        raise ValidationError({"session": "Admissions are not open for this session."})
    if not data["class_applied"].is_active:
        raise ValidationError({"class_applied": "This class is not open for admission."})
    if not data.get("declaration_accepted"):
        raise ValidationError({"declaration_accepted": "The parent must accept the declaration and consent."})
    if not data.get(f"{data['primary_contact']}_phone"):
        raise ValidationError({"primary_contact": "Give a mobile number for the primary contact."})
    check_age(session, data["class_applied"], data["date_of_birth"])

    token = secrets.token_urlsafe(24)
    application = AdmissionApplication.objects.create(
        **data,
        application_number=AdmissionApplication.next_number(session),
        access_token_hash=hash_token(token),
        consent_given_at=timezone.now(),
    )
    _log(application, "", S.SUBMITTED, request.user, "Application submitted")
    audit.record(request, "admission.submitted", application)
    notify("admission.submitted", application=application)
    return application, token


@transaction.atomic
def add_document(request, application, document_type, uploaded_file, file_info):
    if application.status not in AdmissionApplication.OPEN_STATUSES:
        raise ValidationError("Documents can no longer be changed for this application.")
    ext, mime, digest = file_info
    if ext not in document_type.allowed_formats:
        raise ValidationError({"file": f"{document_type.name} must be " + " or ".join(f.upper() for f in document_type.allowed_formats) + "."})
    application.documents.filter(document_type=document_type, is_current=True).update(is_current=False)
    document = ApplicationDocument.objects.create(
        application=application,
        document_type=document_type,
        file=uploaded_file,
        content_type=mime,
        size=uploaded_file.size,
        sha256=digest,
    )
    audit.record(request, "admission.document_uploaded", application, document=document_type.code, sha256=digest)
    return document


@transaction.atomic
def verify_document(request, document, verification, note=""):
    if document.application.status not in AdmissionApplication.OPEN_STATUSES:
        raise ValidationError("This application is already decided.")
    if verification == ApplicationDocument.Verification.REJECTED and not note:
        raise ValidationError({"note": "Say why the document is not acceptable; the parent will see this."})
    document.verification = verification
    document.verification_note = note
    document.verified_by = request.user
    document.verified_at = timezone.now()
    document.save(update_fields=["verification", "verification_note", "verified_by", "verified_at"])
    audit.record(request, f"admission.document_{verification}", document.application, document=document.document_type.code)
    return document


def missing_or_unverified(application):
    """Names of required documents that are not uploaded and verified."""
    verified = set(
        application.current_documents()
        .filter(verification=ApplicationDocument.Verification.VERIFIED)
        .values_list("document_type_id", flat=True)
    )
    return [dt.name for dt in application.required_document_types() if dt.pk not in verified]


@transaction.atomic
def transition(request, application, to_status, message="", internal_notes=None):
    application = AdmissionApplication.objects.select_for_update().get(pk=application.pk)
    allowed = TRANSITIONS.get(application.status, set())
    if to_status not in allowed:
        raise ValidationError({"status": f"Cannot move from {application.get_status_display()} to {S(to_status).label}."})
    needed = "admissions.decide" if to_status in DECISION_STATUSES or application.status == S.APPROVED else "admissions.review"
    if not has_capability(request.user, needed):
        raise PermissionDenied("Only the principal or an administrator can do this.")
    if to_status in (S.DOCUMENTS_REQUESTED, S.REJECTED) and not message:
        raise ValidationError({"message": "Add a message for the parent explaining this."})

    previous = application.status
    application.status = to_status
    application.status_message = message
    application.reviewed_by = request.user
    if internal_notes is not None:
        application.internal_notes = internal_notes
    if to_status in (S.REJECTED, S.WITHDRAWN):
        application.decided_at = timezone.now()
    application.save()
    _log(application, previous, to_status, request.user, message)
    audit.record(request, f"admission.{to_status}", application, from_status=previous)
    notify("admission.status_changed", application=application)
    return application


@transaction.atomic
def approve(request, application, message=""):
    application = AdmissionApplication.objects.select_for_update().get(pk=application.pk)
    if application.status not in AdmissionApplication.OPEN_STATUSES:
        raise ValidationError({"status": f"An application that is {application.get_status_display().lower()} cannot be approved."})
    missing = missing_or_unverified(application)
    if missing:
        raise ValidationError({"documents": ["Verify these documents first: " + ", ".join(missing)]})
    previous = application.status
    application.status = S.APPROVED
    application.status_message = message or "Your application is approved. The school office will contact you to complete admission."
    application.reviewed_by = request.user
    application.decided_at = timezone.now()
    application.save()
    _log(application, previous, S.APPROVED, request.user, application.status_message)
    audit.record(request, "admission.approved", application, from_status=previous)
    notify("admission.status_changed", application=application)
    return application


def _find_or_create_guardian(name, phone, email, occupation, qualification, income, address):
    guardian = Guardian.objects.filter(phone=phone, full_name__iexact=name.strip()).first()
    if guardian:
        # A sibling's parent: keep what we have, fill in blanks only.
        for field, value in (("email", email), ("occupation", occupation), ("qualification", qualification), ("annual_income", income)):
            if value and not getattr(guardian, field):
                setattr(guardian, field, value)
        guardian.save()
        return guardian
    return Guardian.objects.create(
        full_name=name.strip(), phone=phone, email=email, occupation=occupation,
        qualification=qualification, annual_income=income, address=address,
    )


@transaction.atomic
def admit(request, application, section, admission_date=None, roll_number=None):
    """Turn an approved application into a student with an admission number and a section."""
    application = AdmissionApplication.objects.select_for_update().get(pk=application.pk)
    if application.status != S.APPROVED:
        raise ValidationError({"status": "Only approved applications can be admitted."})
    section = Section.objects.select_for_update().get(pk=section.pk)
    if section.session_id != application.session_id or section.school_class_id != application.class_applied_id:
        raise ValidationError({"section": f"Choose a section of {application.class_applied} for {application.session}."})
    active = section.enrollments.filter(status=Enrollment.Status.ACTIVE).count()
    if active >= section.capacity:
        raise ValidationError({"section": f"Section {section.name} is full ({section.capacity} students)."})

    admission_date = admission_date or timezone.localdate()
    student = Student.objects.create(
        admission_number=SchoolProfile.allocate_admission_number(),
        admission_date=admission_date,
        admitted_in_class=application.class_applied,
        application=application,
        **{f: getattr(application, f) for f in (
            "first_name", "last_name", "date_of_birth", "gender", "category", "religion", "mother_tongue",
            "nationality", "blood_group", "aadhaar_number", "address_line", "city", "district", "state",
            "pincode", "previous_school",
        )},
    )

    full_address = f"{application.address_line}, {application.city}, {application.district} {application.pincode}"
    people = [
        ("father", application.father_name, application.father_phone, application.father_email,
         application.father_occupation, application.father_qualification, application.father_annual_income, ""),
        ("mother", application.mother_name, application.mother_phone, application.mother_email,
         application.mother_occupation, application.mother_qualification, application.mother_annual_income, ""),
        ("guardian", application.guardian_name, application.guardian_phone, application.guardian_email,
         application.guardian_occupation, "", None, application.guardian_relationship),
    ]
    for relationship, name, phone, email, occupation, qualification, income, detail in people:
        if not (name and phone):
            continue
        guardian = _find_or_create_guardian(name, phone, email, occupation, qualification, income, full_address)
        if relationship == application.primary_contact and application.parent_aadhaar_number and not guardian.aadhaar_number:
            guardian.aadhaar_number = application.parent_aadhaar_number
            guardian.save(update_fields=["aadhaar_number", "updated_at"])
        StudentGuardian.objects.create(
            student=student, guardian=guardian, relationship=relationship, relationship_detail=detail,
            is_primary_contact=(relationship == application.primary_contact),
        )

    Enrollment.objects.create(
        student=student, session=application.session, section=section,
        roll_number=roll_number, enrolled_on=admission_date,
    )

    photo = application.current_documents().filter(document_type__code="photo", content_type__startswith="image/").first()
    if photo:
        with photo.file.open("rb") as fh:
            student.photo.save(f"photo.{photo.extension}", ContentFile(fh.read()), save=True)

    previous = application.status
    application.status = S.ADMITTED
    application.status_message = f"Admitted to {section.school_class.name} {section.name}. Admission number {student.admission_number}."
    application.save()
    _log(application, previous, S.ADMITTED, request.user, application.status_message)
    audit.record(request, "admission.admitted", application, student_id=student.pk, admission_number=student.admission_number)
    audit.record(request, "student.created", student, application=application.application_number)
    notify("admission.status_changed", application=application)
    return student
