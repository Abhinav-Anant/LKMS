import os
import subprocess
import sys
from pathlib import Path

import pytest

from core.models import AuditLog

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
    assert public.get("/api/v1/school/").data["name"] == "Lotus Kids School"


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
