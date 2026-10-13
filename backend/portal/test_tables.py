from datetime import timedelta

import pytest

from attendance.models import AttendanceRecord
from conftest import as_user

pytestmark = pytest.mark.django_db


def test_report_list_and_permissions(school, client_for):
    principal = client_for("principal")
    names = [r["name"] for r in principal.get("/api/v1/reports/tables/").data]
    assert {"strength", "attendance", "results", "fee-dues", "tc-register"} <= set(names)
    assert as_user(school["class_teacher"]).get("/api/v1/reports/tables/strength/").status_code == 403
    assert principal.get("/api/v1/reports/tables/nonsense/").status_code == 404


def test_every_report_runs(school, client_for):
    principal = client_for("principal")
    start = school["session"].start_date
    riya, kabir = school["students"]
    for i in range(4):
        day = start + timedelta(days=i)
        AttendanceRecord.objects.create(student=riya, section=school["section"], date=day, status="present")
        AttendanceRecord.objects.create(student=kabir, section=school["section"], date=day, status="absent" if i else "present")
    month = start.strftime("%Y-%m")
    for name in ["strength", "fee-dues", "admissions", "tc-register"]:
        assert principal.get(f"/api/v1/reports/tables/{name}/").status_code == 200, name

    strength = principal.get("/api/v1/reports/tables/strength/").data
    class1 = next(r for r in strength["rows"] if r["class"] == "Class 1 A")
    assert class1["total"] == 2 and class1["girls"] == 2 and class1["general"] == 2

    att = principal.get(f"/api/v1/reports/tables/attendance/?month={month}").data
    assert att["rows"] == [{"class": "Class 1 A", "days_marked": 4, "present": 5, "absent": 3, "leave": 0,
                            "percent": 62.5, "low": 1}]
    low = principal.get(f"/api/v1/reports/tables/low-attendance/?month={month}").data
    assert [r["name"] for r in low["rows"]] == ["Kabir Verma"]
    assert principal.get("/api/v1/reports/tables/attendance/?month=bad").status_code == 400
    assert principal.get("/api/v1/reports/tables/results/").status_code == 400


def test_dashboard_reports_backup_health(school, client_for, settings, tmp_path):
    settings.BACKUP_DIR = tmp_path / "none"
    data = client_for("principal").get("/api/v1/reports/dashboard/").data
    assert data["backups"]["healthy"] is False and data["backups"]["latest_at"] is None
