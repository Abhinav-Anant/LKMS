"""deploy/setup_wizard.py, the server settings wizard (plain Python, loaded from its file)."""

import importlib.util
import shutil
import stat

import pytest
from django.conf import settings

SCRIPT = settings.BASE_DIR.parent / "deploy" / "setup_wizard.py"


@pytest.fixture
def wizard():
    spec = importlib.util.spec_from_file_location("setup_wizard", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "whatsapp-server").mkdir()
    shutil.copy(settings.BASE_DIR.parent / "whatsapp-server" / ".env.example", tmp_path / "whatsapp-server")
    return tmp_path


def answer(monkeypatch, wizard, answers, secrets=()):
    answers, secrets = iter(answers), iter(secrets)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr(wizard.getpass, "getpass", lambda prompt="": next(secrets))
    monkeypatch.setattr(wizard.os, "geteuid", lambda: 1000)  # not root: no database, services or HTTPS steps
    return answers


FIRST_RUN = [
    "https://LKMS.lotuskids.in/", "lkms.lotuskids.in",  # a full URL is refused, then the plain address
    "", "", "short", "", "", "",                        # database: a weak password is refused, then the suggestion
    "/srv/lkms-data/", "",                              # files
    "", "", "",                                         # UPI: keep ID, name and QR code
    "", "10", "", "22,6",                               # WhatsApp on, 10 a minute, quiet 10 pm to 6 am
    "", "", "", "rclone copy {file} gdrive:lkms",       # backups
    "",                                                 # save
    "n", "n",                                           # don't install or enter school details now
]


def test_first_run_writes_settings(monkeypatch, wizard, repo, capsys):
    left = answer(monkeypatch, wizard, FIRST_RUN)
    assert wizard.main(["--repo", str(repo)]) == 0
    assert next(left, None) is None

    env_file = repo / "backend" / ".env"
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    env = wizard.read_env(env_file)
    assert env["DJANGO_DEBUG"] == "false"
    assert len(env["DJANGO_SECRET_KEY"]) > 50
    assert env["DJANGO_ALLOWED_HOSTS"] == "lkms.lotuskids.in"
    assert env["DJANGO_CSRF_TRUSTED_ORIGINS"] == env["CORS_ALLOWED_ORIGINS"] == "https://lkms.lotuskids.in"
    assert env["FRONTEND_BASE_URL"] == "https://lkms.lotuskids.in"
    db = wizard.parse_database_url(env["DATABASE_URL"])
    assert (db["name"], db["user"], db["host"], db["port"]) == ("lkms", "lkms", "localhost", "5432")
    assert len(db["password"]) >= 16
    assert env["PRIVATE_MEDIA_ROOT"] == "/srv/lkms-data/private_media"
    assert env["BACKUP_DIR"] == "/srv/lkms-data/backups"
    assert env["SCHOOL_UPI_ID"] == "8619190956@SBI"
    assert env["WHATSAPP_ENABLED"] == "false"  # switched on once the WhatsApp server gives LKMS a key
    assert (env["WHATSAPP_RATE_PER_MINUTE"], env["WHATSAPP_QUIET_HOURS"]) == ("10", "22,6")
    assert env["BACKUP_COPY_COMMAND"] == "rclone copy {file} gdrive:lkms"

    wa = wizard.read_env(repo / "whatsapp-server" / ".env")
    assert all(len(wa[key]) >= 24 for key in ("JWT_SECRET", "COOKIE_SECRET", "ADMIN_PASSWORD"))
    assert wa["ADMIN_USERNAME"] == "lkms-admin" and wa["PORT"] == "3001"

    out = capsys.readouterr().out
    assert "Type only the address" in out and "at least 16 characters" in out


def test_running_again_keeps_secrets_and_other_settings(monkeypatch, wizard, repo):
    answer(monkeypatch, wizard, FIRST_RUN)
    wizard.main(["--repo", str(repo)])
    env_file = repo / "backend" / ".env"
    first = wizard.read_env(env_file)
    wa_first = wizard.read_env(repo / "whatsapp-server" / ".env")
    env_file.write_text(env_file.read_text() + "JWT_ACCESS_MINUTES=45\nWHATSAPP_API_KEY=lkms_key\n")

    # Enter everywhere (the database password is asked hidden and kept), new UPI ID, then save.
    rerun = [""] * 2 + [""] * 3 + [""] * 2 + ["school@okaxis", "", ""] + [""] * 4 + [""] * 4 + ["", "n", "n"]
    left = answer(monkeypatch, wizard, rerun, secrets=[""])
    assert wizard.main(["--repo", str(repo)]) == 0
    assert next(left, None) is None

    env = wizard.read_env(env_file)
    for key in ("DJANGO_SECRET_KEY", "DATABASE_URL", "DJANGO_ALLOWED_HOSTS", "WHATSAPP_QUIET_HOURS"):
        assert env[key] == first[key]
    assert env["SCHOOL_UPI_ID"] == "school@okaxis"
    assert env["JWT_ACCESS_MINUTES"] == "45"
    assert env["WHATSAPP_ENABLED"] == "true"  # it has a key now
    assert wizard.read_env(repo / "whatsapp-server" / ".env")["JWT_SECRET"] == wa_first["JWT_SECRET"]
    assert len(list((repo / "backend").glob(".env.bak-*"))) == 1


def test_not_saving_changes_nothing(monkeypatch, wizard, repo):
    answers = FIRST_RUN[:-3] + ["n"]
    answer(monkeypatch, wizard, answers)
    assert wizard.main(["--repo", str(repo)]) == 1
    assert not (repo / "backend" / ".env").exists()


def test_new_qr_code_must_be_a_jpeg(monkeypatch, wizard, repo, tmp_path, capsys):
    (repo / "frontend" / "public").mkdir(parents=True)
    png, jpeg = tmp_path / "qr.png", tmp_path / "qr.jpg"
    png.write_bytes(b"\x89PNG\r\n")
    jpeg.write_bytes(b"\xff\xd8\xff\xe0 qr")
    answers = FIRST_RUN[:10] + ["", "", str(png), str(jpeg)] + FIRST_RUN[13:]
    answer(monkeypatch, wizard, answers)
    assert wizard.main(["--repo", str(repo)]) == 0
    assert (repo / "frontend" / "public" / "school-upi-qr.jpeg").read_bytes() == jpeg.read_bytes()
    assert "not a JPEG" in capsys.readouterr().out


def test_dry_run_as_root_only_shows_commands(monkeypatch, wizard, repo, capsys):
    answers = FIRST_RUN[:-2] + ["y", "y", "y", "y"]  # database, WhatsApp, install, school details
    answer(monkeypatch, wizard, answers)
    monkeypatch.setattr(wizard.os, "geteuid", lambda: 0)
    monkeypatch.setattr(wizard.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(wizard.subprocess, "run", lambda *a, **k: pytest.fail("ran a command in a dry run"))
    assert wizard.main(["--repo", str(repo), "--dry-run"]) == 0
    assert not (repo / "backend" / ".env").exists()
    out = capsys.readouterr().out
    for command in ("runuser -u postgres -- psql", "docker compose up -d --build whatsapp",
                    "runuser -u lkms -- .venv/bin/python manage.py migrate", "manage.py setup_school"):
        assert command in out


def test_render_keeps_unknown_settings(wizard):
    text = wizard.render_env({"DJANGO_DEBUG": "false", "EXTRA": "1"}, wizard.BACKEND_LAYOUT, "LKMS settings")
    assert "# Website\nDJANGO_DEBUG=false" in text
    assert "# Other settings\nEXTRA=1" in text
