"""Ask for everything a new school needs, one question at a time, and save it.

Covers the school's details, logo and colour, board, admission numbers, school year,
classes and sections, subjects, bell times, admission documents, grade scale, fees and
UPI payments, the administrator and the first staff logins. Run it on its own or from
deploy/setup_wizard.py:

    .venv/bin/python manage.py setup_school
    .venv/bin/python manage.py setup_school --answers examples/lotus-kids/school.json

With --answers, the file's values are offered as the suggested answers (see
examples/README.md). Safe to run again: what is already saved is suggested otherwise.
"""

import getpass
import json
import os
import re
import secrets
import textwrap
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from academics.models import AcademicSession, PeriodSlot, SchoolClass, Section, Subject, TimetableEntry
from admissions.models import DocumentType
from core.management.commands.seed_lkms_defaults import (
    CLASSES,
    DOCUMENTS,
    SUBJECTS,
    current_session_dates,
)
from core.models import SchoolProfile
from core.storage import validate_upload
from exams.grading import GRADE_SCALES
from exams.models import GradeBand
from fees.models import FeeAmount, FeeHead, Installment, Invoice
from students.models import Student
from users.models import User

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
PLANS = {"1": "once a year", "2": "twice a year", "4": "every quarter", "12": "every month"}
DEFAULT_CODES = {name.lower(): code for name, code, _, _ in CLASSES}
AGES = {code: (low, high) for _, code, low, high in CLASSES}
COLOURS = {"blue": "#1d4ed8", "green": "#15803d", "red": "#b91c1c", "pink": "#ad2972", "purple": "#6d28d9",
           "orange": "#c2410c", "teal": "#0f766e", "maroon": "#7f1d1d", "navy": "#1e3a8a"}
STAFF_ROLES = {"principal": "Principal", "office": "Office staff", "accountant": "Accountant", "teacher": "Teacher"}


# ---------------------------------------------------------------- asking

# Set by --accept-defaults: take every suggested answer without asking.
AUTO = {"on": False}


def explain(text):
    for line in textwrap.wrap(text, width=84):
        print("  " + line)


def ask(question, help="", default="", check=None, required=True):
    """One question. Enter takes the default; for an optional question, '-' clears it."""
    print()
    print(question)
    if help:
        explain(help)
    if AUTO["on"]:
        error = (check(default) if check and default else None) or (
            "no suggested answer" if required and not default else None)
        if error:
            raise CommandError(f"{question} {error} (add it to the answers file)")
        print(f"> {default}")
        return default
    while True:
        raw = input(f"> [{default}] " if default else "> ").strip()
        if raw == "-" and not required:
            return ""
        value = raw or default
        if not value and required:
            print("  ! Please type an answer.")
            continue
        error = check(value) if check and value else None
        if error:
            print(f"  ! {error}")
            continue
        return value


def ask_yes(question, help="", default=True):
    print()
    print(question)
    if help:
        explain(help)
    if AUTO["on"]:
        print("> " + ("yes" if default else "no"))
        return default
    while True:
        raw = input("> [Y/n] " if default else "> [y/N] ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes", "n", "no"):
            return raw.startswith("y")
        print("  ! Please answer y or n.")


def pattern(regex, message):
    return lambda value: None if re.fullmatch(regex, value) else message


def whole_number(low, high):
    return lambda value: None if value.isdigit() and low <= int(value) <= high else (
        f"Type a whole number from {low} to {high}.")


def choice(options):
    return lambda value: None if value in options else "Type one of: " + ", ".join(options)


def parse_date(value):
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def check_date(value):
    return None if parse_date(value) else "Type the date as day-month-year, like 01-04-2026."


def show_date(value):
    return value.strftime("%d-%m-%Y")


def parse_time(value):
    for fmt in ("%H:%M", "%H.%M", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(value.upper(), fmt).time()
        except ValueError:
            continue
    return None


def check_time(value):
    return None if parse_time(value) else "Type the time on the 24-hour clock, like 08:00."


def parse_amount(value):
    try:
        amount = Decimal(str(value).replace(",", "").replace("₹", "").strip())
    except InvalidOperation:
        return None
    if amount < 0 or amount != amount.quantize(Decimal("0.01")) or amount >= Decimal("10000000"):
        return None
    return amount


def check_amount(value):
    return None if parse_amount(value) is not None else "Type an amount in rupees, like 2500 (0 if none)."


def rupees(amount):
    amount = Decimal(amount)
    return f"{amount:,.0f}" if amount == amount.to_integral() else f"{amount:,.2f}"


def split_list(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def check_list(value):
    items = [item.lower() for item in split_list(value)]
    if not items:
        return "Type at least one, separated by commas."
    return None if len(set(items)) == len(items) else "Something appears twice."


def check_colour(value):
    return None if value.lower() in COLOURS or re.fullmatch(r"#[0-9a-fA-F]{6}", value) else (
        "Type a colour name (" + ", ".join(COLOURS) + ") or a code like #1d4ed8.")


def class_code(name, taken):
    code = DEFAULT_CODES.get(name.lower())
    if not code:
        number = re.fullmatch(r"(?:class|grade|std\.?)\s*(\d{1,2})", name.strip(), re.IGNORECASE)
        code = number.group(1) if number else re.sub(r"[^A-Za-z0-9]", "", name).upper()[:10] or "C"
    base, n = code, 2
    while code in taken:
        code = f"{base[:8]}{n}"
        n += 1
    return code


def session_name(start):
    return f"{start.year}-{str(start.year + 1)[-2:]}"


def installment_plan(count, start, due_day):
    """(name, due date) for each installment of a session starting on `start`."""
    if count == 1:
        return [("Annual fee", date(start.year, start.month, due_day))]
    step = 12 // count
    plan = []
    for i in range(count):
        month_index = start.month - 1 + i * step
        year, month = start.year + month_index // 12, month_index % 12 + 1
        name = MONTHS[month - 1] if count == 12 else (f"Half {i + 1}" if count == 2 else f"Quarter {i + 1}")
        plan.append((name, date(year, month, due_day)))
    return plan


def bell_times(first, minutes, count, break_after, break_minutes):
    """(number, start, end) for each period, with one break after period `break_after`."""
    clock = datetime.combine(date.today(), first)
    slots = []
    for number in range(1, count + 1):
        end = clock + timedelta(minutes=minutes)
        slots.append((number, clock.time(), end.time()))
        clock = end + timedelta(minutes=break_minutes if number == break_after else 0)
    return slots


class Answers:
    """Suggested answers from a JSON file (examples/<school>/school.json)."""

    def __init__(self, path=None):
        self.data, self.folder = {}, Path(".")
        if path:
            file = Path(path)
            try:
                self.data = json.loads(file.read_text())
            except (OSError, ValueError) as error:
                raise CommandError(f"Could not read {path}: {error}") from error
            self.folder = file.resolve().parent

    def __contains__(self, key):
        return key in self.data

    def get(self, key, fallback=""):
        value = self.data.get(key)
        if value is None:
            return fallback
        if isinstance(value, bool):
            return value
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            return ", ".join(value)
        if isinstance(value, (int, float)):
            return str(value)
        return value

    def path(self, key, fallback=""):
        value = self.data.get(key)
        return str((self.folder / value).resolve()) if value else fallback


# ---------------------------------------------------------------- the questions


class Command(BaseCommand):
    help = "Ask for everything a new school needs (details, classes, fees, logins) one question at a time."

    def add_arguments(self, parser):
        parser.add_argument("--answers", help="JSON file whose values are offered as the suggested answers")
        parser.add_argument("--accept-defaults", action="store_true",
                            help="take every suggested answer without asking (needs --answers; the administrator "
                                 "password comes from the LKMS_ADMIN_PASSWORD environment variable)")

    def handle(self, *args, **options):
        self.a = Answers(options.get("answers"))
        AUTO["on"] = bool(options.get("accept_defaults"))
        try:
            self.run()
        finally:
            AUTO["on"] = False

    def run(self):
        print("School details")
        explain("Each question shows the current or suggested answer in [brackets]; press Enter to keep it. For an "
                "optional question, type - to leave it empty. Each part is saved as soon as it is finished, and you "
                "can change everything later in the app. Press Ctrl+C to stop.")
        steps = [
            ("school", self.profile), ("look", self.look), ("school year", self.sessions),
            ("classes and sections", self.classes), ("subjects", self.subjects), ("bell times", self.periods),
            ("admission documents", self.documents), ("grade scale", self.grades), ("UPI payments", self.payments),
            ("fees", self.fees), ("administrator", self.administrator), ("staff logins", self.staff),
        ]
        done = []
        self.session = self.next_session = None
        self.chosen_classes = []
        try:
            for label, step in steps:
                if step() is not False:
                    done.append(label)
        except (KeyboardInterrupt, EOFError):
            print()
            print("Stopped. " + (f"Saved so far: {', '.join(done)}. " if done else "") + "Run it again to continue.")
            return
        print()
        self.stdout.write(self.style.SUCCESS("School details saved: " + ", ".join(done) + "."))

    def d(self, key, current):
        """The suggested answer: the answers file wins, then what is saved."""
        value = self.a.get(key, None)
        return current if value is None else value

    # -- the school

    def profile(self):
        print("\n-- 1. The school --")
        p = SchoolProfile.get()
        placeholder = SchoolProfile._meta.get_field("name").default
        p.name = ask("School name?", "As printed on receipts, report cards and transfer certificates.",
                     self.d("name", "" if p.name == placeholder else p.name))
        suggested = "".join(word[0] for word in p.name.split() if word[:1].isalpha()).upper()[:6] or "SCH"
        p.short_code = ask("Short code for application numbers?", "1 to 6 capital letters, e.g. GVS gives "
                           "GVS-2026-27-00001.", self.d("short_code", p.short_code if p.short_code != "SCH"
                                                       else suggested),
                           pattern(r"[A-Za-z]{1,6}", "Use 1 to 6 letters.")).upper()
        p.address = ask("Address?", "Street and town, on one line.", self.d("address", p.address))
        p.district = ask("District?", "", self.d("district", p.district))
        p.state = ask("State?", "Also the state filled in for parents on the admission form.",
                      self.d("state", p.state))
        p.pincode = ask("PIN code?", "", self.d("pincode", p.pincode), pattern(r"\d{6}", "A PIN code is 6 digits."))
        p.phone = ask("School phone number?", "Shown to parents on the website, receipts and messages.",
                      self.d("phone", p.phone), pattern(r"[0-9+ -]{6,15}", "Type the number with digits only."))
        p.email = ask("School email? (optional)", "", self.d("email", p.email),
                      pattern(r"[^@\s]+@[^@\s]+\.[^@\s]+", "Not an email address."), required=False)
        p.website = ask("School website? (optional)", "Like https://myschool.in", self.d("website", p.website),
                        pattern(r"https?://\S+", "Start it with https://"), required=False)
        p.udise_code = ask("UDISE+ code? (optional)", "The school's 11-digit code from the UDISE+ portal.",
                           self.d("udise_code", p.udise_code), pattern(r"\d{11}", "A UDISE+ code is 11 digits."),
                           required=False)
        boards = dict(SchoolProfile.BOARD_CHOICES)
        p.board = ask("Board? " + ", ".join(f"{key} = {label}" for key, label in boards.items()), "",
                      self.d("board", p.board), choice(boards))
        if p.board in ("state", "other"):
            p.board_name = ask("Full name of the board?", "Printed on report cards and transfer certificates, e.g. "
                               "Rajasthan Board of Secondary Education (RBSE).", self.d("board_name", p.board_name),
                               required=p.board == "state")
        else:
            p.board_name = ""
        p.affiliation_number = ask("Affiliation or recognition number? (optional)", "",
                                   self.d("affiliation_number", p.affiliation_number), required=False)

        print("\nAdmission (S.R.) numbers")
        p.admission_number_prefix = ask(
            "Text before the admission number? (optional)",
            "For example 'GVS/' gives GVS/0001. Leave empty for plain numbers.",
            self.d("admission_number_prefix", p.admission_number_prefix),
            pattern(r".{1,10}", "At most 10 characters."), required=False)
        p.admission_number_width = int(ask("How many digits in the admission number?", "4 gives 0001, 0002 and so on.",
                                           self.d("admission_number_width", str(p.admission_number_width)),
                                           whole_number(1, 8)))
        if Student.objects.exists():
            explain(f"The next admission number stays {p.next_admission_number}: students are already admitted.")
        else:
            p.next_admission_number = int(ask(
                "First admission number to give out?",
                "If the school's paper register already has numbers, continue from the next one.",
                self.d("next_admission_number", str(p.next_admission_number)), whole_number(1, 9999999)))
        p.save()

    def look(self):
        print("\n-- 2. Logo and colour --")
        p = SchoolProfile.get()
        logo = ask("Logo picture? (optional)",
                   "Full path of a PNG or JPEG on this server. It shows on the website, receipts, report cards and "
                   "certificates. Press Enter to " + ("keep the current logo." if p.logo else "skip."),
                   self.a.path("logo"), self.check_picture, required=False)
        colour = ask("Main colour of the website?", "A colour name (" + ", ".join(COLOURS) + ") or a code like "
                     "#1d4ed8, ideally the school's own colour.", self.d("brand_colour", p.brand_colour),
                     check_colour)
        p.brand_colour = COLOURS.get(colour.lower(), colour.lower())
        if logo:
            self.save_picture(p, "logo", logo)
        p.save()

    @staticmethod
    def check_picture(value):
        path = Path(value).expanduser()
        if not path.is_file():
            return "No file there. Type the full path, or press Enter to skip."
        with path.open("rb") as handle:
            try:
                validate_upload(File(handle, name=path.name), allowed=("jpg", "png"))
            except ValidationError as error:
                return " ".join(error.messages)
        return None

    @staticmethod
    def save_picture(profile, field, path):
        path = Path(path).expanduser()
        old = getattr(profile, field)
        with path.open("rb") as handle:
            upload = File(handle, name=path.name)
            ext, _, _ = validate_upload(upload, allowed=("jpg", "png"))
            if old:
                old.delete(save=False)
            getattr(profile, field).save(f"{field}.{ext}", upload, save=False)

    # -- school year

    def sessions(self):
        print("\n-- 3. School year --")
        current = AcademicSession.current()
        if current:
            start, end = current.start_date, current.end_date
        else:
            _, start, end = current_session_dates(date.today())
        start = parse_date(ask("First day of the current school year?", "Usually 1 April. Day-month-year.",
                               show_date(start), check_date))
        end = parse_date(ask("Last day of the current school year?", "Usually 31 March.",
                             show_date(end if end > start else date(start.year + 1, start.month, 1)),
                             lambda v: check_date(v) or (None if parse_date(v) > start else
                                                         "It must be after the first day.")))
        next_start = date(start.year + 1, start.month, start.day)
        cutoff = current.age_cutoff_date if current and current.age_cutoff_date else None
        cutoff = parse_date(ask(
            "Date on which a child's age is checked for admission?",
            "Admission age limits are checked on this date each year. Many schools use 31 March or 1 April.",
            self.d("age_cutoff", show_date(cutoff or start)), check_date))
        open_next = ask_yes(f"Accept online admission applications for next year ({session_name(next_start)})?",
                            "Parents apply on the website; the office reviews each application.",
                            default=self.d("admissions_open", True))
        with transaction.atomic():
            session = current or AcademicSession.objects.filter(name=session_name(start)).first() or \
                AcademicSession(name=session_name(start))
            session.start_date, session.end_date, session.is_current = start, end, True
            session.age_cutoff_date = cutoff
            session.save()
            next_session, _ = AcademicSession.objects.get_or_create(
                name=session_name(next_start),
                defaults={"start_date": next_start, "end_date": date(next_start.year + 1, end.month, end.day)},
            )
            next_session.admissions_open = open_next
            next_session.age_cutoff_date = date(cutoff.year + 1, cutoff.month, min(cutoff.day, 28)) \
                if (cutoff.month, cutoff.day) == (2, 29) else date(cutoff.year + 1, cutoff.month, cutoff.day)
            next_session.save()
        self.session, self.next_session = session, next_session

    # -- classes

    def classes(self):
        print("\n-- 4. Classes and sections --")
        existing = list(SchoolClass.objects.filter(is_active=True))
        names = split_list(self.a.get("classes", "")) or [c.name for c in existing] or [n for n, _, _, _ in CLASSES]
        print("\nThe school's classes, youngest first:")
        explain(", ".join(names))
        if not ask_yes("Is this list right?", "Answer n to type the school's own list."):
            names = split_list(ask("Type the classes, youngest first, separated by commas.",
                                   "For example: Nursery, LKG, UKG, Class 1, Class 2, Class 3, Class 4, Class 5",
                                   check=check_list))
        current_sections = sorted(set(Section.objects.filter(session=self.session).values_list("name", flat=True)))
        sections = [s.upper() for s in split_list(ask(
            "Sections in each class, separated by commas?",
            "Most small schools have one section, A. Type A, B for two. A class can get extra sections later in "
            "School setup.", self.d("sections", ", ".join(current_sections) or "A"),
            pattern(r"\s*[A-Za-z0-9]{1,10}\s*(,\s*[A-Za-z0-9]{1,10}\s*)*", "Like A or A, B"),
        ))]
        capacity = Section.objects.filter(session=self.session).values_list("capacity", flat=True).first() or 40
        capacity = int(ask("Most students in one section?", "Admissions warn when a section is full.",
                           self.d("capacity", str(capacity)), whole_number(1, 200)))

        with transaction.atomic():
            for c in SchoolClass.objects.all():  # free the order numbers before renumbering
                c.order += 1000
                c.save(update_fields=["order"])
            by_name = {c.name.lower(): c for c in SchoolClass.objects.all()}
            by_code = {c.code: c for c in SchoolClass.objects.all()}
            taken = set(by_code)
            chosen = []
            for order, name in enumerate(names, start=1):
                school_class = by_name.get(name.lower())
                if school_class is None:
                    code = DEFAULT_CODES.get(name.lower())
                    school_class = by_code.get(code) if code and by_code.get(code) not in chosen else None
                if school_class is None:
                    code = class_code(name, taken)
                    taken.add(code)
                    low, high = AGES.get(code, (None, None))
                    school_class = SchoolClass(code=code, min_age_years=low, max_age_years=high)
                school_class.name, school_class.order, school_class.is_active = name, order, True
                school_class.save()
                chosen.append(school_class)
            SchoolClass.objects.exclude(pk__in=[c.pk for c in chosen]).update(is_active=False)
            for s in (self.session, self.next_session):
                for school_class in chosen:
                    for section in sections:
                        row, created = Section.objects.get_or_create(
                            session=s, school_class=school_class, name=section, defaults={"capacity": capacity})
                        if not created and row.capacity != capacity:
                            row.capacity = capacity
                            row.save(update_fields=["capacity"])
        self.chosen_classes = chosen
        self.age_limits(chosen)

    def age_limits(self, classes):
        ages = self.a.get("age_limits", {})
        if isinstance(ages, dict) and ages:
            for c in classes:
                if c.name in ages:
                    c.min_age_years, c.max_age_years = ages[c.name]
                    c.save(update_fields=["min_age_years", "max_age_years"])
        limited = [c for c in classes if c.min_age_years is not None or c.max_age_years is not None]
        print("\nAdmission age limits (age on the check date):")
        explain("; ".join(f"{c.name} {c.min_age_years}-{c.max_age_years} years" for c in limited)
                if limited else "none")
        if ask_yes("Are these right?", "Classes not listed have no age limit. Answer n to set them class by class.",
                   default=True):
            return
        for c in classes:
            value = ask(f"Age limits for {c.name}, as lowest-highest? (optional)", "For example 3-4. Type - for "
                        "no limit.", f"{c.min_age_years}-{c.max_age_years}" if c.min_age_years is not None else "",
                        pattern(r"\d{1,2}-\d{1,2}", "Type two ages like 3-4."), required=False)
            low, high = (int(v) for v in value.split("-")) if value else (None, None)
            c.min_age_years, c.max_age_years = low, high
            c.save(update_fields=["min_age_years", "max_age_years"])

    # -- subjects, bell times, documents, grades

    def subjects(self):
        print("\n-- 5. Subjects --")
        existing = [s.name for s in Subject.objects.filter(is_active=True)]
        names = split_list(self.a.get("subjects", "")) or existing or SUBJECTS
        names = split_list(ask("Subjects taught, separated by commas?",
                               "Used for marks, report cards and the timetable. Edit the list or press Enter.",
                               ", ".join(names), check_list))
        with transaction.atomic():
            by_name = {s.name.lower(): s for s in Subject.objects.all()}
            codes = set(Subject.objects.values_list("code", flat=True))
            kept = []
            for order, name in enumerate(names, start=1):
                subject = by_name.get(name.lower())
                if subject is None:
                    code, n = slugify(name)[:20] or "subject", 2
                    while code in codes:
                        code = f"{slugify(name)[:17]}-{n}"
                        n += 1
                    codes.add(code)
                    subject = Subject(code=code)
                subject.name, subject.order, subject.is_active = name, order, True
                subject.save()
                kept.append(subject.pk)
            Subject.objects.exclude(pk__in=kept).update(is_active=False)

    def periods(self):
        print("\n-- 6. Bell times --")
        if TimetableEntry.objects.exists():
            explain("The timetable already uses the bell times, so they are not changed here. Use School setup > "
                    "Bell times in the app.")
            return False
        slots = list(PeriodSlot.objects.all())
        first = slots[0] if slots else None
        length = (datetime.combine(date.today(), first.end_time) - datetime.combine(date.today(), first.start_time)) \
            .seconds // 60 if first else 40
        start = parse_time(ask("When does the first period start?", "On the 24-hour clock.",
                               self.d("first_period", first.start_time.strftime("%H:%M") if first else "08:00"),
                               check_time))
        minutes = int(ask("How long is a period, in minutes?", "", self.d("period_minutes", str(length)),
                          whole_number(10, 120)))
        count = int(ask("How many periods in a day?", "", self.d("periods", str(len(slots) or 8)),
                        whole_number(1, 14)))
        break_after = int(ask("Break after which period? (0 for none)", "", self.d("break_after", str(min(4, count))),
                              whole_number(0, count)))
        break_minutes = int(ask("How long is the break, in minutes?", "", self.d("break_minutes", "20"),
                                whole_number(0, 120))) if break_after else 0
        times = bell_times(start, minutes, count, break_after, break_minutes)
        explain("Periods: " + ", ".join(f"{n}) {a:%H:%M}-{b:%H:%M}" for n, a, b in times))
        with transaction.atomic():
            PeriodSlot.objects.all().delete()
            PeriodSlot.objects.bulk_create(PeriodSlot(number=n, start_time=a, end_time=b) for n, a, b in times)

    def documents(self):
        print("\n-- 7. Documents asked for at admission --")
        current = list(DocumentType.objects.filter(is_active=True))
        wanted = self.a.get("documents", None)
        if isinstance(wanted, list) and wanted and isinstance(wanted[0], dict):
            rows = [(d["name"], bool(d.get("required", True))) for d in wanted]
        elif current:
            rows = [(d.name, d.is_required) for d in current]
        else:
            rows = [(name, required) for _, name, required, *_ in DOCUMENTS]
        for name, required in rows:
            explain(f"{name} ({'required' if required else 'optional'})")
        if not ask_yes("Is this list right?", "Parents upload these with the online application. Answer n to type "
                       "your own list.", default=True):
            names = split_list(ask("Type the documents, separated by commas.",
                                   "For example: Birth certificate, Photo, Aadhaar card, Transfer certificate",
                                   check=check_list))
            rows = [(name, ask_yes(f"Is the {name.lower()} required?", "", default=True)) for name in names]
        with transaction.atomic():
            by_name = {d.name.lower(): d for d in DocumentType.objects.all()}
            standard = {name.lower(): (code, description, pdf, image)
                        for code, name, _, description, pdf, image in DOCUMENTS}
            kept = []
            for order, (name, required) in enumerate(rows, start=1):
                doc = by_name.get(name.lower())
                if doc is None:
                    code, description, pdf, image = standard.get(name.lower(), (slugify(name)[:40], "", True, True))
                    doc = DocumentType(code=code, description=description, allow_pdf=pdf, allow_image=image)
                    if DocumentType.objects.filter(code=doc.code).exists():
                        doc.code = f"{doc.code[:32]}-{secrets.token_hex(3)}"
                doc.name, doc.is_required, doc.order, doc.is_active = name, required, order, True
                doc.save()
                kept.append(doc.pk)
            DocumentType.objects.exclude(pk__in=kept).update(is_active=False)

    def grades(self):
        print("\n-- 8. Grade scale --")
        keys = list(GRADE_SCALES)
        explain("; ".join(f"{i} = {label}" for i, (label, _) in enumerate(GRADE_SCALES.values(), start=1))
                + "; 0 = keep the current scale")
        current = "0" if GradeBand.objects.exists() else "1"
        default = self.a.get("grade_scale", None)
        default = str(keys.index(default) + 1) if default in keys else current
        picked = ask("Which grade scale?", "Used on report cards. It can be edited in the app (Exams > Grade scale).",
                     default, choice([str(i) for i in range(len(keys) + 1)]))
        if picked == "0":
            return False
        with transaction.atomic():
            GradeBand.objects.all().delete()
            for grade, minimum, description, is_pass in GRADE_SCALES[keys[int(picked) - 1]][1]:
                GradeBand.objects.create(grade=grade, min_percent=minimum, description=description, is_pass=is_pass)

    # -- fees

    def payments(self):
        print("\n-- 9. Fee payments --")
        p = SchoolProfile.get()
        p.upi_id = ask("The school's UPI ID?", "Parents pay fees by scanning a QR code for this UPI ID. It looks like "
                       "name@bank, for example 9876543210@SBI.", self.d("upi_id", p.payment_upi_id),
                       pattern(r"[A-Za-z0-9._-]{2,}@[A-Za-z]{2,}", "A UPI ID looks like name@bank."))
        p.upi_name = ask("Name on that UPI account?", "Parents see this to check they are paying the school.",
                         self.d("upi_name", p.payment_upi_name))
        qr = ask("The bank's QR code picture? (optional)",
                 "Full path of a PNG or JPEG of the school's printed QR code. Press Enter to " +
                 ("keep the current one." if p.upi_qr else "let LKMS make the QR code from the UPI ID."),
                 self.a.path("upi_qr"), self.check_picture, required=False)
        if qr:
            self.save_picture(p, "upi_qr", qr)
        p.office_can_collect_fees = ask_yes(
            "May office staff record fees paid at the school office (cash or cheque)?",
            "The principal, accountant and administrator always can.",
            default=self.d("office_can_collect_fees", p.office_can_collect_fees))
        p.fee_reminder_days_before = int(ask(
            "Send a WhatsApp fee reminder how many days before the due date?", "",
            self.d("fee_reminder_days_before", str(p.fee_reminder_days_before)), whole_number(0, 30)))
        p.fee_reminder_every_days = int(ask(
            "While a fee is overdue, remind again every how many days?", "",
            self.d("fee_reminder_every_days", str(p.fee_reminder_every_days)), whole_number(1, 60)))
        p.save()

    def fees(self):
        print("\n-- 10. Fees --")
        session, classes = self.session, self.chosen_classes
        if Invoice.objects.filter(session=session).exists():
            explain(f"Fees for {session} are already billed to students, so they are not changed here. "
                    "Use Fees > Setup in the app.")
            return False
        installments = list(Installment.objects.filter(session=session))
        if installments and not ask_yes(
                f"Fees for {session} are already set ({len(installments)} installments). Enter them again?",
                "Answer n to keep them as they are.", default=False):
            return False

        old = {(a.fee_head.code, a.school_class_id): a.amount for a in
               FeeAmount.objects.filter(installment__session=session).select_related("fee_head")}
        count = ask("How often are fees collected? " + ", ".join(f"{k} = {v}" for k, v in PLANS.items()),
                    "The year's tuition fee is split into this many installments.",
                    self.d("installments", str(len(installments)) if str(len(installments)) in PLANS else "4"),
                    choice(PLANS))
        due_day = int(ask("On which day of the month is each installment due?",
                          "Parents get a WhatsApp reminder before it.", self.d("due_day", "10"), whole_number(1, 28)))
        plan = installment_plan(int(count), session.start_date, due_day)
        explain("Installments: " + "; ".join(f"{name} due {show_date(due)}" for name, due in plan))

        heads = [
            ("tuition", "Tuition fee", False, "every", f"Charged in every installment ({PLANS[count]})."),
            ("admission", "Admission fee", True, "first", "Charged once, with the first installment, and only to "
                                                          "students newly admitted that year."),
            ("annual", "Annual charges", False, "first", "Charged once a year, with the first installment."),
            ("exam", "Examination fee", False, "first", "For the whole year, charged with the first installment."),
        ]
        amounts = {}
        for code, label, _, _, help_text in heads:
            amounts[code] = self.amounts_per_class(label, help_text, classes, code, old, f"fee.{code}",
                                                   same_default=code != "tuition")
        extra = []
        suggestions = list(self.a.get("fee.extra", []) or [])
        while True:
            suggestion = suggestions.pop(0) if suggestions else {}
            name = ask("Any other fee? Type its name, or press Enter if there are no more.",
                       "For example Transport fee or Computer fee.", suggestion.get("name", ""), required=False)
            if not name:
                break
            every = ask_yes(f"Is the {name} charged in every installment?",
                            "Answer n if it is charged once a year with the first installment.",
                            default=bool(suggestion.get("every", False)))
            code = slugify(name)[:30] or "fee"
            extra.append((code, name, False, "every" if every else "first", ""))
            self.a.data[f"fee.{code}"] = suggestion.get("amount")
            amounts[code] = self.amounts_per_class(name, "", classes, code, old, f"fee.{code}", same_default=True)

        with transaction.atomic():
            FeeAmount.objects.filter(installment__session=session).delete()
            Installment.objects.filter(session=session).delete()
            fee_heads = {}
            for order, (code, name, new_only, _, _) in enumerate(heads + extra, start=1):
                head, _ = FeeHead.objects.get_or_create(code=code, defaults={"name": name, "order": order})
                head.name, head.new_students_only, head.is_active, head.order = name, new_only, True, order
                head.save()
                fee_heads[code] = head
            for order, (name, due) in enumerate(plan, start=1):
                installment = Installment.objects.create(session=session, name=name, due_date=due, order=order)
                for code, _, _, when, _ in heads + extra:
                    if when == "first" and order != 1:
                        continue
                    for school_class in classes:
                        amount = amounts[code][school_class.pk]
                        if amount:
                            FeeAmount.objects.create(installment=installment, school_class=school_class,
                                                     fee_head=fee_heads[code], amount=amount)
        times = {code: len(plan) if when == "every" else 1 for code, _, _, when, _ in heads + extra}
        print("\nSaved. A returning student's fees for the year (new students also pay the admission fee):")
        for c in classes:
            total = sum(amounts[code][c.pk] * times[code] for code in amounts if code != "admission")
            print(f"  {c.name}: ₹{rupees(total)}")

    def amounts_per_class(self, label, help_text, classes, code, old, key, same_default):
        suggested = self.a.data.get(key)
        if isinstance(suggested, dict):
            olds = {c.pk: suggested.get(c.name) for c in classes}
            same = False
        elif suggested is not None:
            olds = {c.pk: suggested for c in classes}
            same = True
        else:
            olds = {c.pk: old.get((code, c.pk)) for c in classes}
            values = set(olds.values())
            same = len(values) == 1 if None not in values else same_default
        if ask_yes(f"Is the {label.lower()} the same for every class?", help_text, default=same):
            first = olds.get(classes[0].pk) if classes else None
            amount = parse_amount(ask(f"{label}, in rupees? (0 if none)", "",
                                      rupees(first) if first is not None else "", check_amount))
            return {c.pk: amount for c in classes}
        result = {}
        for c in classes:
            previous = olds.get(c.pk)
            result[c.pk] = parse_amount(ask(f"{label} for {c.name}, in rupees? (0 if none)", "",
                                            rupees(previous) if previous is not None else "", check_amount))
        return result

    # -- logins

    def administrator(self):
        print("\n-- 11. Administrator login --")
        admins = User.objects.filter(role=User.Role.ADMIN, is_active=True)
        if admins.exists():
            explain("Administrators already set up: " + ", ".join(a.username for a in admins) + ".")
            if not ask_yes("Add or change an administrator login?", "", default=False):
                return False
        explain("The administrator can do everything, including adding staff and changing these settings.")
        username = ask("Username?", "Small letters, no spaces. For example the owner's first name.",
                       self.d("admin.username", ""),
                       pattern(r"[a-z0-9_.@+-]{3,30}", "3 to 30 small letters or digits, no spaces."))
        user = User.objects.filter(username=username).first()
        if user is None:
            user = User(username=username)
            user.first_name = ask("First name?", "", self.d("admin.first_name", ""))
            user.last_name = ask("Last name? (optional)", "", self.d("admin.last_name", ""), required=False)
            user.phone = ask("Mobile number? (optional)", "10 digits.", self.d("admin.phone", ""),
                             pattern(r"[6-9]\d{9}", "Type the 10-digit mobile number."), required=False)
        elif not ask_yes(f"'{username}' already exists. Make it an administrator and set a new password?"):
            return False
        while True:
            if AUTO["on"]:
                password = os.environ.get("LKMS_ADMIN_PASSWORD", "")
                try:
                    validate_password(password, user)
                except ValidationError as error:
                    raise CommandError("Set LKMS_ADMIN_PASSWORD to the administrator's password: "
                                       + " ".join(error.messages)) from error
                break
            password = getpass.getpass("\nPassword (at least 10 characters, not shown as you type)\n> ")
            try:
                validate_password(password, user)
            except ValidationError as error:
                print("  ! " + " ".join(error.messages))
                continue
            if getpass.getpass("Type it again\n> ") != password:
                print("  ! The two did not match.")
                continue
            break
        user.set_password(password)
        user.role = User.Role.ADMIN
        user.is_staff = user.is_superuser = user.is_active = True
        user.must_change_password = False
        user.save()
        explain(f"'{username}' can now sign in at /staff/login.")

    def staff(self):
        from users.views import temporary_password

        print("\n-- 12. Staff logins --")
        explain("Add the principal, office staff, accountant and teachers now, or later under Users in the app. Each "
                "gets a temporary password, shown once here, and must change it at first sign-in.")
        suggestions = list(self.a.get("staff", []) or [])
        added = []
        while True:
            suggestion = suggestions.pop(0) if suggestions else {}
            name = ask("Name of a staff member to add? Press Enter when there are no more.", "",
                       suggestion.get("name", ""), required=False)
            if not name:
                break
            role = ask("Their role? " + ", ".join(STAFF_ROLES), "", suggestion.get("role", "teacher"),
                       choice(STAFF_ROLES))
            phone = ask("Their mobile number? (optional)", "", suggestion.get("phone", ""),
                        pattern(r"[6-9]\d{9}", "Type the 10-digit mobile number."), required=False)
            base = slugify(name.split()[0]).replace("-", "") or "staff"
            username, n = base, 2
            while User.objects.filter(username=username).exists():
                username, n = f"{base}{n}", n + 1
            username = ask("Their username?", "", username,
                           pattern(r"[a-z0-9_.@+-]{3,30}", "3 to 30 small letters or digits."))
            if User.objects.filter(username=username).exists():
                print(f"  ! '{username}' is taken; skipped.")
                continue
            first, _, last = name.partition(" ")
            password = temporary_password()
            User.objects.create_user(username=username, password=password, first_name=first, last_name=last,
                                     phone=phone, role=role, must_change_password=True)
            added.append((name, STAFF_ROLES[role], username, password))
        if added:
            print("\nWrite these down and give each person their own (shown only now):")
            for name, role, username, password in added:
                print(f"  {name} ({role}): username {username}, temporary password {password}")
        return bool(added) or False
