import pytest
from rest_framework.test import APIClient

from conftest import make_user

pytestmark = pytest.mark.django_db


def test_login_returns_tokens_and_capabilities():
    make_user("office", "clerk")
    response = APIClient().post("/api/v1/auth/login/", {"username": "clerk", "password": "Correct-horse-9"}, format="json")
    assert response.status_code == 200
    assert {"access", "refresh"} <= set(response.data)
    caps = response.data["user"]["capabilities"]
    assert "admissions.review" in caps and "admissions.decide" not in caps


def test_wrong_password_is_refused():
    make_user("office", "clerk")
    response = APIClient().post("/api/v1/auth/login/", {"username": "clerk", "password": "nope"}, format="json")
    assert response.status_code == 401


def test_logout_blacklists_refresh_token():
    make_user("office", "clerk")
    client = APIClient()
    tokens = client.post("/api/v1/auth/login/", {"username": "clerk", "password": "Correct-horse-9"}, format="json").data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]}, format="json").status_code == 205
    assert client.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json").status_code == 401


def test_role_cannot_be_changed_by_the_user(client_for):
    client = client_for("teacher")
    response = client.patch("/api/v1/auth/me/", {"role": "admin", "first_name": "Asha"}, format="json")
    assert response.status_code == 200
    assert response.data["role"] == "teacher" and response.data["first_name"] == "Asha"


def test_principal_creates_staff_with_temporary_password(client_for):
    principal = client_for("principal")
    response = principal.post("/api/v1/auth/users/", {
        "username": "sunita", "first_name": "Sunita", "last_name": "Rao", "role": "teacher", "phone": "9829000001",
    }, format="json")
    assert response.status_code == 201, response.data
    login = APIClient().post("/api/v1/auth/login/", {"username": "sunita", "password": response.data["temporary_password"]},
                             format="json")
    assert login.status_code == 200 and login.data["user"]["must_change_password"]


def test_principal_cannot_create_or_reset_administrators(client_for):
    from users.models import User

    principal = client_for("principal")
    assert principal.post("/api/v1/auth/users/", {"username": "boss", "role": "admin"}, format="json").status_code == 400
    admin = make_user("admin", "boss")
    assert principal.post(f"/api/v1/auth/users/{admin.pk}/reset-password/").status_code == 403
    assert User.objects.get(pk=admin.pk).check_password("Correct-horse-9")


def test_reset_password_forces_a_change(client_for):
    from users.models import User

    teacher = make_user("teacher", "asha")
    response = client_for("admin").post(f"/api/v1/auth/users/{teacher.pk}/reset-password/")
    assert response.status_code == 200
    teacher = User.objects.get(pk=teacher.pk)
    assert teacher.must_change_password and teacher.check_password(response.data["temporary_password"])


def test_staff_cannot_deactivate_themselves():
    admin = make_user("admin", "boss")
    client = APIClient()
    client.force_authenticate(admin)
    assert client.patch(f"/api/v1/auth/users/{admin.pk}/", {"is_active": False}, format="json").status_code == 400


def test_teachers_cannot_manage_users_and_matrix_is_readable(client_for):
    assert client_for("teacher").get("/api/v1/auth/users/").status_code == 403
    matrix = client_for("principal").get("/api/v1/auth/permissions/").data
    marks = next(c for c in matrix["capabilities"] if c["key"] == "marks.enter")
    assert "teacher" in marks["roles"] and "office" not in marks["roles"]
