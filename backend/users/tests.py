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
