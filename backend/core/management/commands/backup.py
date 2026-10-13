"""Nightly backup: database + uploaded files, then retention. Run from cron or a systemd timer."""

import logging

from django.core.management.base import BaseCommand, CommandError

from core import backup

logger = logging.getLogger("lkms.backup")


class Command(BaseCommand):
    help = "Back up the database and uploaded files to BACKUP_DIR, copy off-site if set, and delete old backups."

    def add_arguments(self, parser):
        parser.add_argument("--no-prune", action="store_true", help="Keep every old backup this time")
        parser.add_argument("--list", action="store_true", help="Only list the backups that exist")

    def handle(self, *args, **options):
        if options["list"]:
            for path, taken in backup.list_backups():
                self.stdout.write(f"{taken:%Y-%m-%d %H:%M}  {path.stat().st_size / 1e6:8.1f} MB  {path.name}")
            return
        try:
            path = backup.create_backup()
            self.stdout.write(f"Backup written: {path} ({path.stat().st_size / 1e6:.1f} MB)")
            logger.info("backup written %s", path)
            if backup.copy_offsite(path):
                self.stdout.write("Copied off-site.")
            if not options["no_prune"]:
                for old in backup.prune():
                    self.stdout.write(f"Deleted old backup {old.name}")
        except backup.BackupError as e:
            logger.error("backup failed: %s", e)
            raise CommandError(str(e))
