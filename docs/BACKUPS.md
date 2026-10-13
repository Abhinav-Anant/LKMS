# Backups and restore (Phase 5)

Every night LKMS writes one backup file holding the whole database and every uploaded file (student photos,
admission documents, UPI payment screenshots). Old backups are deleted on a schedule. A restore puts the data back
exactly as it was when the backup was taken.

## What a backup is

`lkms-YYYYMMDD-HHMMSS.tar` in `BACKUP_DIR`, readable only by the server user (permissions 600). Inside:

| File | What |
| --- | --- |
| `manifest.json` | when it was taken, database type, SHA-256 checksum, number of uploaded files, LKMS version (migrations) |
| `database.dump` | PostgreSQL dump (`pg_dump --format=custom`) |
| `database.sqlite3` | instead of the above when the server uses SQLite (development only) |
| `private_media/...` | every uploaded file |

The file is first written under a temporary name and renamed only when complete, so a half-written backup is never
mistaken for a good one.

**Backups hold Aadhaar numbers, addresses and documents.** Keep them on the server's own disk and in an encrypted
off-site copy only. Never email them or put them in a shared folder.

Not in the backup: the WhatsApp link (re-scan the QR code after moving to a new server) and the `.env` file (keep a
copy of it in a password manager).

## Settings (`backend/.env`)

| Setting | Default | Meaning |
| --- | --- | --- |
| `BACKUP_DIR` | `backend/backups` | where backups are written. Put it on a disk with room for about 35 backups |
| `BACKUP_KEEP_DAILY` | 14 | keep the newest backup of each of the last 14 days |
| `BACKUP_KEEP_WEEKLY` | 8 | and of each of the last 8 weeks |
| `BACKUP_KEEP_MONTHLY` | 12 | and of each of the last 12 months |
| `BACKUP_COPY_COMMAND` | empty | command run after each backup to copy it off the server; `{file}` is the backup's path |
| `BACKUP_MAX_AGE_HOURS` | 36 | the principal's dashboard shows a red warning when the newest backup is older than this |

With the defaults about 30 backups are kept at any time (14 + 8 + 12, minus overlaps).

## Commands

```bash
cd backend
uv run python manage.py backup                 # take a backup now, copy it off-site, delete old ones
uv run python manage.py backup --list          # list the backups that exist
uv run python manage.py restore_backup FILE --check   # verify a backup without changing anything
uv run python manage.py restore_backup FILE           # restore (asks you to type "restore")
```

`backup` needs `pg_dump` on the server (`apt install postgresql-client-16`; it must be the same or a newer major
version than the database). `restore_backup` needs `pg_restore` from the same package.

## Running it every night

### Linux server (systemd, recommended)

The unit files are in `deploy/`. Adjust the paths and user in `lkms-backup.service` if LKMS is not in `/srv/lkms`, then:

```bash
sudo cp deploy/lkms-backup.service deploy/lkms-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lkms-backup.timer
sudo systemctl start lkms-backup.service        # take the first backup now
journalctl -u lkms-backup.service -n 20         # see what it did
```

`Persistent=true` means a backup missed while the server was off runs as soon as it starts again.

### Linux with cron instead

```
30 2 * * * cd /srv/lkms/backend && .venv/bin/python manage.py backup >> /var/log/lkms-backup.log 2>&1
```

### Windows (Task Scheduler)

1. Open Task Scheduler and choose **Create Basic Task**. Name it "LKMS backup" and choose **Daily** at 02:30.
2. Action: **Start a program**. Program: `C:\Projects\LKMS\backend\.venv\Scripts\python.exe`.
   Arguments: `manage.py backup`. Start in: `C:\Projects\LKMS\backend`.
3. In the task's properties tick **Run whether user is logged on or not** and, on the Settings tab,
   **Run task as soon as possible after a scheduled start is missed**.
4. With PostgreSQL on Windows, add its `bin` folder (for example `C:\Program Files\PostgreSQL\16\bin`) to the
   system PATH so `pg_dump` and `pg_restore` are found.

## Off-site copy

A backup on the same server is lost with the server. Copy each backup somewhere else, encrypted. One way is
[rclone](https://rclone.org) with an encrypted ("crypt") remote pointing at Google Drive or another cloud folder:

```bash
rclone config          # create a remote, then a "crypt" remote on top of it called lkms-offsite
# in backend/.env:
BACKUP_COPY_COMMAND=rclone copy {file} lkms-offsite:backups
```

If the copy fails, the backup is still kept on the server and the command exits with an error (visible in
`journalctl` or the cron log). Old copies off-site are not deleted by LKMS; set a lifecycle rule there, or run
`rclone delete --min-age 400d lkms-offsite:backups` monthly.

## Restoring

Use this after a mistake (data deleted or changed wrongly) or to move to a new server.

1. Stop the website and the WhatsApp worker so nobody changes data during the restore:
   `sudo systemctl stop lkms-gunicorn lkms-whatsapp` (use your service names).
2. Check the backup: `uv run python manage.py restore_backup /path/lkms-....tar --check`
3. Restore: `uv run python manage.py restore_backup /path/lkms-....tar`, then type `restore`.
   Before changing anything it takes a backup of the current state, named `...-before-restore.tar`, so a restore can
   itself be undone.
4. If it says the backup was made with a different version of LKMS, run `uv run python manage.py migrate`.
5. Start the services again.

On a **new server**: install LKMS, create the empty database and `.env`, copy the backup across, and run step 3
(no `migrate` needed first). Then link WhatsApp again by scanning the QR code.

`--skip-media` restores only the database and leaves uploaded files as they are.

## Tested

- Automatic tests (`core/test_backup.py`): backup contents and permissions, checksum catches a damaged file,
  entries that try to escape the folder are refused, retention, off-site command, `--check`.
- Real restores were run on 13 Oct 2026 against PostgreSQL 16 and SQLite: change data, delete an uploaded file,
  restore, and confirm the data and the file are back exactly; and a restore into a brand-new empty PostgreSQL
  database (the new-server case).

Test a restore yourself once a term: restore the newest backup onto a spare machine or a copy of the server with
`--check` at least, and ideally a full restore into a scratch database.
