import io
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image
from rest_framework.test import APIClient

from academics.models import AcademicSession, SchoolClass, Section
from users.models import User


@pytest.fixture(autouse=True)
def _isolated(settings, tmp_path):
    settings.PRIVATE_MEDIA_ROOT = tmp_path / "private"
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": []}
    from django.core.cache import cache

    cache.clear()


@pytest.fixture
def seeded(db):
    call_command("seed_lkms_defaults", stdout=io.StringIO())
    return {
        "open_session": AcademicSession.objects.get(admissions_open=True),
        "class1": SchoolClass.objects.get(code="1"),
        "nursery": SchoolClass.objects.get(code="NUR"),
    }


@pytest.fixture
def section(seeded):
    return Section.objects.get(session=seeded["open_session"], school_class=seeded["class1"], name="A")


def make_user(role, username=None):
    return User.objects.create_user(username=username or role, password="Correct-horse-9", role=role)


@pytest.fixture
def client_for(db):
    def _client(role):
        client = APIClient()
        client.force_authenticate(make_user(role, f"{role}-{User.objects.count()}"))
        return client
    return _client


@pytest.fixture
def public():
    return APIClient()


@pytest.fixture
def application_data(seeded):
    return {
        "session": seeded["open_session"].pk,
        "class_applied": seeded["class1"].pk,
        "first_name": "Aarav",
        "last_name": "Sharma",
        "date_of_birth": "2021-05-10",
        "gender": "M",
        "category": "general",
        "address_line": "12 Gandhi Nagar",
        "city": "Jaipur",
        "district": "Jaipur",
        "pincode": "302015",
        "father_name": "Rohit Sharma",
        "father_phone": "+91 98290 12345",
        "mother_name": "Neha Sharma",
        "mother_phone": "9829054321",
        "primary_contact": "father",
        "declaration_accepted": True,
    }


def pdf_file(name="doc.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4\n%test\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF", content_type="application/pdf")


def png_file(name="photo.png"):
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "red").save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")
