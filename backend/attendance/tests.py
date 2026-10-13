from datetime import timedelta

import pytest
from django.utils import timezone

from attendance.models import AttendanceRecord
from conftest import as_user, make_user

pytestmark = pytest.mark.django_db


def school_day(days_back=0):
    day = timezone.localdate() - timedelta(days=days_back)
    while day.weekday() == 6:
        day -= timedelta(days=1)
    return day


def payload(school, day, status="present"):
    return {"section": school["section"].pk, "date": day.isoformat(),
            "records": [{"student": s.pk, "status": status} for s in school["students"]]}


def test_class_teacher_marks_and_corrects_attendance(school):
    client = as_user(school["class_teacher"])
    day = school_day()
    sheet = client.get("/api/v1/attendance/sheet/", {"section": school["section"].pk, "date": day.isoformat()}).data
    assert sheet["can_edit"] and not sheet["marked"] and [r["status"] for r in sheet["rows"]] == [None, None]

    response = client.post("/api/v1/attendance/sheet/", payload(school, day), format="json")
    assert response.status_code == 200, response.data
    assert response.data["marked"] and {r["status"] for r in response.data["rows"]} == {"present"}

    client.post("/api/v1/attendance/sheet/", payload(school, day, "absent"), format="json")
    assert AttendanceRecord.objects.filter(date=day, status="absent").count() == 2
    assert AttendanceRecord.objects.count() == 2


def test_subject_teacher_can_view_but_not_mark(school):
    client = as_user(school["maths_teacher"])
    day = school_day()
    sheet = client.get("/api/v1/attendance/sheet/", {"section": school["section"].pk, "date": day.isoformat()})
    assert sheet.status_code == 200 and not sheet.data["can_edit"]
    assert client.post("/api/v1/attendance/sheet/", payload(school, day), format="json").status_code == 403


def test_teacher_of_another_class_cannot_see_the_register(school):
    client = as_user(make_user("teacher", "other"))
    response = client.get("/api/v1/attendance/sheet/", {"section": school["section"].pk, "date": school_day().isoformat()})
    assert response.status_code == 403


def test_future_dates_and_old_dates_are_refused_for_teachers(school):
    client = as_user(school["class_teacher"])
    tomorrow = timezone.localdate() + timedelta(days=1)
    assert client.post("/api/v1/attendance/sheet/", payload(school, tomorrow), format="json").status_code == 400
    old = school_day(10)
    if old >= school["session"].start_date:
        assert client.post("/api/v1/attendance/sheet/", payload(school, old), format="json").status_code == 403
        principal = as_user(make_user("principal", "head"))
        assert principal.post("/api/v1/attendance/sheet/", payload(school, old), format="json").status_code == 200


def test_students_from_other_sections_are_refused(school):
    client = as_user(school["class_teacher"])
    body = payload(school, school_day())
    body["records"].append({"student": 999999, "status": "present"})
    assert client.post("/api/v1/attendance/sheet/", body, format="json").status_code == 400


def test_month_summary(school):
    client = as_user(school["class_teacher"])
    day = school_day()
    client.post("/api/v1/attendance/sheet/", payload(school, day), format="json")
    rows = client.get("/api/v1/attendance/month/", {"section": school["section"].pk, "month": day.strftime("%Y-%m")}).data
    assert rows[0]["present"] == 1 and rows[0]["percentage"] == 100.0
