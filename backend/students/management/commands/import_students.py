"""Import students from the sample sheet on the server, e.g. when the photos are too many for the browser.

    manage.py import_students students.xlsx --photos photos.zip --check
    manage.py import_students students.xlsx --photos photos.zip
    manage.py import_students --sample student-import-sample.xlsx
"""

from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from students import bulk_import


class Command(BaseCommand):
    help = "Bulk import students (and photos) from an .xlsx or .csv sheet. Nothing is saved if any row has a problem."

    def add_arguments(self, parser):
        parser.add_argument("sheet", nargs="?", help="The filled-in .xlsx or .csv file")
        parser.add_argument("--photos", help="A ZIP file or a folder of photos")
        parser.add_argument("--check", action="store_true", help="Only check the sheet; save nothing")
        parser.add_argument("--sample", metavar="FILE", help="Write the sample sheet (with this school's classes) to FILE")

    def handle(self, *args, **options):
        if options["sample"]:
            Path(options["sample"]).write_bytes(bulk_import.template_workbook())
            self.stdout.write(f"Sample written to {options['sample']}")
            return
        if not options["sheet"]:
            raise CommandError("Give the sheet to import, or --sample FILE.")
        try:
            with open(options["sheet"], "rb") as fh:
                rows = bulk_import.read_sheet(File(fh, name=options["sheet"]))
            photos = self._photos(options["photos"]) if options["photos"] else None
            if options["check"]:
                report, _ = bulk_import.check(rows, photo_names=list(photos) if photos else None)
            else:
                report = bulk_import.run(None, rows, photos=photos)
        except (OSError, ValidationError) as exc:
            raise CommandError(" ".join(getattr(exc, "messages", [str(exc)]))) from exc

        for error in report.errors:
            self.stdout.write(f"Row {error['row']}, {error['column']}: {error['message']}")
        if report.new_sections:
            self.stdout.write("New sections: " + ", ".join(report.new_sections))
        if report.photos_unused:
            self.stdout.write(f"{len(report.photos_unused)} photos match no student: " + ", ".join(report.photos_unused[:20]))
        if report.errors:
            raise CommandError(f"{len(report.errors)} problems in {report.total} rows. Nothing was imported.")
        verb = "are ready to import" if options["check"] else "imported"
        self.stdout.write(self.style.SUCCESS(f"{report.total} students {verb}, {report.photos_matched} with photos."))

    def _photos(self, location):
        path = Path(location)
        if path.is_dir():
            return {p.name.lower(): p.read_bytes() for p in path.iterdir()
                    if p.is_file() and p.suffix.lower() in bulk_import.PHOTO_EXTENSIONS}
        with open(path, "rb") as fh:
            return bulk_import.photos_from_zip(fh)
