"""Database and uploaded-file backups, retention and restore.

A backup is one file, lkms-YYYYMMDD-HHMMSS.tar, holding:
  manifest.json    what is inside, with SHA-256 checksums
  database.dump    PostgreSQL custom-format dump (pg_dump -Fc), or
  database.sqlite3 a consistent copy of the SQLite file (development only)
  private_media/   student photos, documents and payment screenshots
"""

import hashlib
import io
import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone

PREFIX = "lkms-"
SUFFIX = ".tar"
FORMAT = 1


class BackupError(Exception):
    pass


def backup_dir():
    path = Path(settings.BACKUP_DIR)
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def _db():
    db = settings.DATABASES["default"]
    engine = db["ENGINE"].rsplit(".", 1)[-1]
    if engine not in ("postgresql", "sqlite3"):
        raise BackupError(f"Backups support PostgreSQL and SQLite, not {engine}.")
    return engine, db


def _pg_env(db):
    env = os.environ.copy()
    env.update({k: str(v) for k, v in {
        "PGHOST": db.get("HOST"), "PGPORT": db.get("PORT"), "PGUSER": db.get("USER"),
        "PGPASSWORD": db.get("PASSWORD"), "PGDATABASE": db.get("NAME"),
    }.items() if v})
    return env


def _run(cmd, env=None):
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise BackupError(f"{cmd[0]} failed: {result.stderr.strip()[:500]}")
    return result.stdout


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _dump_database(engine, db, target):
    if engine == "postgresql":
        _run(["pg_dump", "--format=custom", "--no-owner", "--no-privileges", f"--file={target}"], env=_pg_env(db))
    else:
        source = sqlite3.connect(db["NAME"])
        dest = sqlite3.connect(target)
        with dest:
            source.backup(dest)
        dest.close()
        source.close()


def _last_migrations():
    if MigrationRecorder.Migration._meta.db_table not in connection.introspection.table_names():
        return {}  # an empty database, e.g. a new server before its first restore
    rows = MigrationRecorder.Migration.objects.order_by("app", "applied").values_list("app", "name")
    return {app: name for app, name in rows}


def create_backup(label=""):
    """Write a new backup and return its path."""
    engine, db = _db()
    folder = backup_dir()
    stamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    name = f"{PREFIX}{stamp}{'-' + label if label else ''}{SUFFIX}"
    final = folder / name
    if final.exists():
        raise BackupError(f"{final} already exists.")
    media = Path(settings.PRIVATE_MEDIA_ROOT)

    with tempfile.TemporaryDirectory(dir=folder) as work:
        db_name = "database.dump" if engine == "postgresql" else "database.sqlite3"
        db_file = Path(work) / db_name
        _dump_database(engine, db, db_file)
        media_files = [p for p in media.rglob("*") if p.is_file()] if media.exists() else []
        manifest = {
            "format": FORMAT, "created_at": timezone.now().isoformat(), "engine": engine,
            "database_file": db_name, "database_sha256": _sha256(db_file),
            "media_files": len(media_files), "media_bytes": sum(p.stat().st_size for p in media_files),
            "migrations": _last_migrations(),
        }
        partial = Path(work) / (name + ".partial")
        with tarfile.open(partial, "w") as tar:
            data = json.dumps(manifest, indent=2).encode()
            info = tarfile.TarInfo("manifest.json")
            info.size, info.mtime = len(data), int(timezone.now().timestamp())
            tar.addfile(info, io.BytesIO(data))
            tar.add(db_file, arcname=db_name)
            for path in media_files:
                tar.add(path, arcname=f"private_media/{path.relative_to(media).as_posix()}")
        os.chmod(partial, 0o600)
        os.replace(partial, final)  # appears only once complete
    return final


def copy_offsite(path):
    """Run BACKUP_COPY_COMMAND for a new backup, if one is set."""
    command = settings.BACKUP_COPY_COMMAND.strip()
    if not command:
        return False
    _run([part.replace("{file}", str(path)) for part in shlex.split(command)])
    return True


# --- Listing and retention -------------------------------------------------

def _stamp(path):
    try:
        return datetime.strptime(path.name[len(PREFIX):len(PREFIX) + 15], "%Y%m%d-%H%M%S")
    except ValueError:
        return None


def list_backups():
    """Backups in BACKUP_DIR, newest first, as (path, taken_at) pairs."""
    folder = Path(settings.BACKUP_DIR)
    if not folder.exists():
        return []
    found = [(p, _stamp(p)) for p in folder.glob(f"{PREFIX}*{SUFFIX}") if p.is_file()]
    return sorted([(p, t) for p, t in found if t], key=lambda pt: pt[1], reverse=True)


def to_keep(stamps, daily, weekly, monthly):
    """Grandfather-father-son: the newest backup of each of the last `daily` days, `weekly` weeks and `monthly` months."""
    keep = set()
    for count, key in ((daily, lambda t: t.date()), (weekly, lambda t: t.isocalendar()[:2]),
                       (monthly, lambda t: (t.year, t.month))):
        seen = []
        for t in sorted(stamps, reverse=True):
            k = key(t)
            if k not in seen:
                if len(seen) == count:
                    break
                seen.append(k)
                keep.add(t)
    return keep


def prune():
    """Delete backups that fall outside the retention policy. Returns the deleted paths."""
    backups = list_backups()
    keep = to_keep([t for _, t in backups], settings.BACKUP_KEEP_DAILY, settings.BACKUP_KEEP_WEEKLY,
                   settings.BACKUP_KEEP_MONTHLY)
    deleted = []
    for path, taken in backups:
        if taken not in keep:
            path.unlink()
            deleted.append(path)
    return deleted


# --- Checking and restoring --------------------------------------------------

def _safe_members(tar):
    for member in tar.getmembers():
        name = Path(member.name)
        if name.is_absolute() or ".." in name.parts or not (member.isfile() or member.isdir()):
            raise BackupError(f"Unsafe entry in backup: {member.name}")
    return tar.getmembers()


def read_manifest(path):
    if not Path(path).is_file():
        raise BackupError(f"No backup file at {path}.")
    try:
        with tarfile.open(path) as tar:
            _safe_members(tar)
            manifest = json.load(tar.extractfile("manifest.json"))
    except (KeyError, tarfile.TarError, ValueError):
        raise BackupError("This file is not an LKMS backup, or it is damaged.")
    if manifest.get("format") != FORMAT:
        raise BackupError(f"Unknown backup format {manifest.get('format')}.")
    return manifest


def check(path, workdir):
    """Unpack `path` into `workdir` and verify it. Returns the manifest."""
    manifest = read_manifest(path)
    with tarfile.open(path) as tar:
        tar.extractall(workdir, members=_safe_members(tar), filter="data")
    db_file = Path(workdir) / manifest["database_file"]
    if _sha256(db_file) != manifest["database_sha256"]:
        raise BackupError("The database file is damaged (checksum does not match).")
    media = Path(workdir) / "private_media"
    count = sum(1 for p in media.rglob("*") if p.is_file()) if media.exists() else 0
    if count != manifest["media_files"]:
        raise BackupError(f"Expected {manifest['media_files']} uploaded files, found {count}.")
    if manifest["engine"] == "postgresql":
        _run(["pg_restore", "--list", str(db_file)])
    else:
        conn = sqlite3.connect(db_file)
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        conn.close()
        if ok != "ok":
            raise BackupError(f"The SQLite database is damaged: {ok}")
    return manifest


def restore(path, include_media=True):
    """Replace the database (and uploaded files) with the contents of a backup.

    Stop the web server and the WhatsApp worker first. Takes a safety backup of the
    current state before changing anything and returns its path.
    """
    engine, db = _db()
    folder = backup_dir()
    with tempfile.TemporaryDirectory(dir=folder) as work:
        manifest = check(path, work)
        if manifest["engine"] != engine:
            raise BackupError(f"This backup is from {manifest['engine']}, but the server uses {engine}.")
        safety = create_backup(label="before-restore")
        db_file = Path(work) / manifest["database_file"]
        connection.close()
        if engine == "postgresql":
            _run(["pg_restore", "--clean", "--if-exists", "--no-owner", "--no-privileges", "--single-transaction",
                  f"--dbname={db['NAME']}", str(db_file)], env=_pg_env(db))
        else:
            shutil.copyfile(db_file, db["NAME"])
        if include_media:
            media = Path(settings.PRIVATE_MEDIA_ROOT)
            media.parent.mkdir(parents=True, exist_ok=True)
            incoming = Path(work) / "private_media"
            staged = media.with_name(media.name + ".restoring")
            if staged.exists():
                shutil.rmtree(staged)
            if incoming.exists():
                shutil.copytree(incoming, staged)
            else:
                staged.mkdir()
            old = media.with_name(media.name + ".old")
            if old.exists():
                shutil.rmtree(old)
            if media.exists():
                media.rename(old)
            staged.rename(media)
            if old.exists():
                shutil.rmtree(old)  # the safety backup above holds the previous files
    return safety


def status():
    backups = list_backups()
    latest = backups[0][1] if backups else None
    if latest:
        latest = timezone.make_aware(latest)
    age_hours = (timezone.now() - latest).total_seconds() / 3600 if latest else None
    return {
        "directory": str(settings.BACKUP_DIR),
        "latest_at": latest,
        "healthy": age_hours is not None and age_hours <= settings.BACKUP_MAX_AGE_HOURS,
        "max_age_hours": settings.BACKUP_MAX_AGE_HOURS,
        "offsite_copy": bool(settings.BACKUP_COPY_COMMAND.strip()),
        "retention": {"daily": settings.BACKUP_KEEP_DAILY, "weekly": settings.BACKUP_KEEP_WEEKLY,
                      "monthly": settings.BACKUP_KEEP_MONTHLY},
        "backups": [{"name": p.name, "size": p.stat().st_size, "taken_at": timezone.make_aware(t)}
                    for p, t in backups[:60]],
    }
