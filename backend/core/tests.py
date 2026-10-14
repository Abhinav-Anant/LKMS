import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from conftest import make_user, png_file
from core.models import AuditLog, SchoolProfile

BACKEND = Path(__file__).resolve().parent.parent


def test_production_refuses_to_start_without_secret_key():
    env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_") and k != "DATABASE_URL"}
    env["DJANGO_DEBUG"] = "false"
    result = subprocess.run(
        [sys.executable, "-c", "import django, os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; django.setup()"],
        cwd=BACKEND, env=env, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY must be set" in result.stderr


@pytest.mark.django_db
def test_health_and_public_school(public):
    assert public.get("/api/v1/health/").data == {"status": "ok"}
    school = public.get("/api/v1/school/").data
    assert school["name"] == "Your School Name"
    assert school["board_label"] == "State board" and school["has_logo"] is False


@pytest.mark.django_db
def test_upi_qr_is_made_from_the_upi_id(public):
    assert public.get("/api/v1/school/upi-qr/").status_code == 404
    SchoolProfile.objects.filter(pk=SchoolProfile.get().pk).update(upi_id="school@okaxis", upi_name="Green Valley")
    response = public.get("/api/v1/school/upi-qr/")
    assert response.status_code == 200 and response["Content-Type"] == "image/svg+xml"
    assert response.content.startswith(b"<svg")


@pytest.mark.django_db
def test_admin_sets_logo_qr_and_colour(client_for, public):
    admin_client = client_for("admin")
    url = "/api/v1/school/settings/"
    response = admin_client.patch(url, {"brand_colour": "#ad2972", "board": "state", "board_name": "RBSE",
                                        "logo": png_file("logo.png"), "upi_qr": png_file("qr.png")},
                                  format="multipart")
    assert response.status_code == 200, response.data
    assert response.data["has_logo"] and response.data["has_upi_qr"] and response.data["board_label"] == "RBSE"
    assert public.get("/api/v1/school/logo/")["Content-Type"] == "image/png"
    assert public.get("/api/v1/school/upi-qr/")["Content-Type"] == "image/png"
    assert admin_client.patch(url, {"brand_colour": "pink"}, format="json").status_code == 400
    bad = admin_client.patch(url, {"logo": SimpleUploadedFile("x.pdf", b"%PDF-1.4 x", content_type="application/pdf")}, format="multipart")
    assert bad.status_code == 400

    assert admin_client.patch(url, {"remove_logo": True}, format="json").data["has_logo"] is False
    assert public.get("/api/v1/school/logo/").status_code == 404


@pytest.mark.django_db
def test_office_collects_fees_only_when_the_school_allows(db):
    office_user = make_user("office")
    from core.permissions import has_capability

    assert not has_capability(office_user, "fees.collect")
    SchoolProfile.objects.filter(pk=SchoolProfile.get().pk).update(office_can_collect_fees=True)
    assert has_capability(office_user, "fees.collect")


@pytest.mark.django_db
def test_only_admin_can_change_school_settings(client_for):
    assert client_for("principal").patch("/api/v1/school/settings/", {"name": "X"}, format="json").status_code == 403
    response = client_for("admin").patch("/api/v1/school/settings/", {"udise_code": "08120100101"}, format="json")
    assert response.status_code == 200
    assert AuditLog.objects.filter(action="school.updated").exists()


@pytest.mark.django_db
def test_audit_entries_cannot_be_edited(client_for):
    client_for("admin").patch("/api/v1/school/settings/", {"phone": "0141000000"}, format="json")
    entry = AuditLog.objects.get()
    entry.action = "tampered"
    with pytest.raises(ValueError):
        entry.save()


@pytest.mark.django_db
def test_printed_documents_carry_the_logo(client_for):
    import io

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    from exams.pdf import draw_logo, school_header

    client_for("admin").patch("/api/v1/school/settings/", {"logo": png_file("logo.png")}, format="multipart")
    school = SchoolProfile.get()
    pdf = canvas.Canvas(io.BytesIO(), pagesize=A4)
    assert draw_logo(pdf, school, 10, 800, 50)
    school_header(pdf, school, A4[0], 800)
    pdf.save()

    school.logo.delete(save=False)  # file gone but still named: the header prints without it
    school.logo.name = "school/missing.png"
    assert draw_logo(pdf, school, 10, 800, 50) is False
