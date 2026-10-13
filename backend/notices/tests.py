import pytest

from conftest import as_user
from notices.models import Notice

pytestmark = pytest.mark.django_db


def test_principal_posts_to_everyone(client_for):
    response = client_for("principal").post("/api/v1/notices/", {"title": "Holiday", "body": "School closed on Friday."}, format="json")
    assert response.status_code == 201, response.data
    assert response.data["published_at"]


def test_teacher_posts_only_to_parents_of_own_sections(school):
    client = as_user(school["class_teacher"])
    assert client.post("/api/v1/notices/", {"title": "Hi", "body": "x"}, format="json").status_code == 400
    ok = client.post("/api/v1/notices/", {"title": "Bring crayons", "body": "Art class tomorrow.", "audience": "parents",
                                          "sections": [school["section"].pk]}, format="json")
    assert ok.status_code == 201, ok.data


def test_teacher_cannot_edit_someone_elses_notice(school, client_for):
    notice = Notice.objects.create(title="Fees", body="Due", audience="everyone")
    response = as_user(school["class_teacher"]).patch(f"/api/v1/notices/{notice.pk}/", {"title": "x"}, format="json")
    assert response.status_code == 403


def test_accountant_cannot_post(client_for):
    assert client_for("accountant").post("/api/v1/notices/", {"title": "x", "body": "y"}, format="json").status_code == 403
