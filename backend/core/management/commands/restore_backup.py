"""Restore a backup made by `manage.py backup`. Stop the web server and WhatsApp worker first."""

import tempfile

from django.core.management.base import BaseCommand, CommandError

from core import backup


class Command(BaseCommand):
    help = "Check a backup, or restore it over the current database and uploaded files."

    def add_arguments(self, parser):
        parser.add_argument("file", help="Path to an lkms-*.tar backup")
        parser.add_argument("--check", action="store_true", help="Only verify the backup; change nothing")
        parser.add_argument("--skip-media", action="store_true", help="Restore the database only")
        parser.add_argument("--yes", action="store_true", help="Do not ask for confirmation")

    def handle(self, *args, **options):
        path = options["file"]
        try:
            with tempfile.TemporaryDirectory() as work:
                manifest = backup.check(path, work)
            self.stdout.write(
                f"Backup OK: taken {manifest['created_at']}, {manifest['engine']} database, "
                f"{manifest['media_files']} uploaded files."
            )
            current = backup._last_migrations()
            differ = sorted(app for app in set(current) | set(manifest["migrations"])
                            if current.get(app) != manifest["migrations"].get(app))
            if differ and current:  # an empty database (a new server) has nothing to compare
                self.stdout.write(self.style.WARNING(
                    "The backup was made with a different version of LKMS (apps: " + ", ".join(differ) + "). "
                    "After restoring, run `python manage.py migrate`."
                ))
            if options["check"]:
                return
            if not options["yes"]:
                answer = input("This REPLACES all current data with the backup. Type 'restore' to continue: ")
                if answer.strip() != "restore":
                    raise CommandError("Cancelled.")
            safety = backup.restore(path, include_media=not options["skip_media"])
        except backup.BackupError as e:
            raise CommandError(str(e))
        self.stdout.write(self.style.SUCCESS(f"Restored. The data from before the restore is saved in {safety}."))
