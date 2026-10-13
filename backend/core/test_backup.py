import tarfile
from datetime import datetime, timedelta

import pytest
from django.core.management import CommandError, call_command

from core import backup

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def where(settings, tmp_path):
    settings.BACKUP_DIR = tmp_path / "backups"
    settings.BACKUP_COPY_COMMAND = ""
    media = tmp_path / "private"
    (media / "student-photos").mkdir(parents=True)
    (media / "student-photos" / "a.png").write_bytes(b"png-bytes")
    settings.PRIVATE_MEDIA_ROOT = media
    return tmp_path


def test_retention_keeps_daily_weekly_and_monthly():
    start = datetime(2026, 1, 1, 2, 0)
    stamps = [start + timedelta(days=i) for i in range(200)]
    keep = backup.to_keep(stamps, daily=14, weekly=8, monthly=12)
    newest = stamps[-1]
    assert all(t in keep for t in stamps[-14:])                       # last 14 days
    assert len({t.isocalendar()[:2] for t in keep}) >= 8              # 8 weeks
    assert {(t.year, t.month) for t in keep} == {(t.year, t.month) for t in stamps}  # 7 months, all kept
    assert newest in keep and len(keep) < 40


def test_backup_contains_manifest_database_and_files(where):
    path = backup.create_backup()
    assert path.name.startswith("lkms-") and oct(path.stat().st_mode)[-3:] == "600"
    with tarfile.open(path) as tar:
        names = tar.getnames()
    assert "manifest.json" in names and "private_media/student-photos/a.png" in names
    manifest = backup.check(path, where / "check")
    assert manifest["media_files"] == 1 and "students" in manifest["migrations"]


def test_damaged_backup_is_refused(where):
    path = backup.create_backup()
    bad = where / "lkms-20260101-000000.tar"
    with tarfile.open(path) as src, tarfile.open(bad, "w") as dst:
        for member in src.getmembers():
            data = src.extractfile(member)
            if member.name.startswith("database"):
                content = data.read()[:-10] + b"0123456789"
                import io
                member.size = len(content)
                dst.addfile(member, io.BytesIO(content))
            else:
                dst.addfile(member, data)
    with pytest.raises(backup.BackupError, match="damaged"):
        backup.check(bad, where / "check")


def test_unsafe_paths_are_refused(where):
    evil = where / "lkms-20260101-000001.tar"
    with tarfile.open(evil, "w") as tar:
        (where / "x").write_text("x")
        tar.add(where / "x", arcname="../escape")
    with pytest.raises(backup.BackupError, match="Unsafe"):
        backup.read_manifest(evil)


def test_prune_deletes_old_backups(where, settings):
    folder = backup.backup_dir()
    for days in range(30):
        (folder / f"lkms-{(datetime(2026, 9, 1) + timedelta(days=days)):%Y%m%d}-020000.tar").write_bytes(b"x")
    settings.BACKUP_KEEP_DAILY, settings.BACKUP_KEEP_WEEKLY, settings.BACKUP_KEEP_MONTHLY = 3, 2, 1
    deleted = backup.prune()
    assert len(list(folder.glob("lkms-*.tar"))) == 30 - len(deleted) <= 5


def test_offsite_copy_command(where, settings):
    settings.BACKUP_COPY_COMMAND = f"cp {{file}} {where}"
    path = backup.create_backup()
    assert backup.copy_offsite(path) and (where / path.name).exists()
    settings.BACKUP_COPY_COMMAND = "false {file}"
    with pytest.raises(backup.BackupError):
        backup.copy_offsite(path)


def test_backup_command_and_check_only_restore(where):
    call_command("backup")
    path = backup.list_backups()[0][0]
    call_command("restore_backup", str(path), "--check")
    with pytest.raises(CommandError):
        call_command("restore_backup", str(where / "missing.tar"), "--check")
