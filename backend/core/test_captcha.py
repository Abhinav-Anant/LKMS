import pytest

from core import captcha
from core.models import SchoolProfile

pytestmark = [pytest.mark.captcha, pytest.mark.django_db]


@pytest.fixture
def readable(monkeypatch):
    """Pictures come back as their plain letters, so the test can 'read' them."""
    monkeypatch.setattr(captcha, "_picture", lambda text: text)


def solve(client, answer=None):
    challenge = client.get("/api/v1/captcha/").json()
    response = client.post("/api/v1/captcha/", {"challenge": challenge["challenge"],
                                                         "answer": answer or challenge["image"].lower()}, format="json")
    return response


def test_real_picture_is_a_png(public):
    body = public.get("/api/v1/captcha/").json()
    assert body["enabled"] is True and body["image"].startswith("data:image/png;base64,")


def test_right_answer_gives_a_pass_and_a_challenge_works_once(public, readable):
    challenge = public.get("/api/v1/captcha/").json()
    data = {"challenge": challenge["challenge"], "answer": challenge["image"]}
    assert public.post("/api/v1/captcha/", data, format="json").json()["pass"]
    assert public.post("/api/v1/captcha/", data, format="json").status_code == 400


def test_wrong_answer_burns_the_challenge(public, readable):
    challenge = public.get("/api/v1/captcha/").json()
    assert public.post("/api/v1/captcha/", {"challenge": challenge["challenge"], "answer": "nope"},
                       format="json").status_code == 400
    assert public.post("/api/v1/captcha/", {"challenge": challenge["challenge"], "answer": challenge["image"]},
                       format="json").status_code == 400


def test_forged_challenge_is_refused(public):
    assert public.post("/api/v1/captcha/", {"challenge": "x", "answer": "ABCDE"}, format="json").status_code == 400


def test_application_needs_a_pass_used_once(public, readable, application_data):
    assert public.post("/api/v1/admissions/public/apply/", application_data, format="json").status_code == 400
    token = solve(public).json()["pass"]
    typo = public.post("/api/v1/admissions/public/apply/", {**application_data, "first_name": "", "captcha": token},
                       format="json")
    assert "first_name" in typo.json()  # a field error does not use up the pass
    assert public.post("/api/v1/admissions/public/apply/", {**application_data, "captcha": token},
                       format="json").status_code == 201
    replay = public.post("/api/v1/admissions/public/apply/", {**application_data, "captcha": token}, format="json")
    assert replay.status_code == 400 and "captcha" in replay.json()


def test_tracking_and_parent_code_need_a_pass(public, seeded):
    track = public.post("/api/v1/admissions/public/track/", {"application_number": "X", "date_of_birth": "2021-05-10",
                                                             "phone": "9829011111"}, format="json")
    code = public.post("/api/v1/auth/parent/request-code/", {"phone": "9829011111"}, format="json")
    assert "captcha" in track.json() and "captcha" in code.json()


def test_switching_it_off(public, application_data):
    profile = SchoolProfile.get()
    profile.captcha_enabled = False
    profile.save()
    assert public.get("/api/v1/captcha/").json() == {"enabled": False}
    assert public.post("/api/v1/admissions/public/apply/", application_data, format="json").status_code == 201
