"""Ask for the school's details one question at a time and save them.

Covers what the school needs before it can start: the school profile, the current
session, classes and sections, the fee structure and the administrator login. Run it
on its own or from deploy/setup_wizard.py:

    .venv/bin/python manage.py setup_school

Safe to run again: what is already saved becomes the default answer.
"""

import getpass
import re
import textwrap
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from academics.models import AcademicSession, SchoolClass, Section
from core.management.commands.seed_lkms_defaults import CLASSES, current_session_dates, seed_reference_data
from core.models import SchoolProfile
from fees.models import FeeAmount, FeeHead, Installment, Invoice
from students.models import Student
from users.models import User

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
PLANS = {"1": "once a year", "2": "twice a year", "4": "every quarter", "12": "every month"}
DEFAULT_CODES = {name.lower(): code for name, code, _, _ in CLASSES}
AGES = {code: (low, high) for _, code, low, high in CLASSES}


class Stop(Exception):
    pass


# ---------------------------------------------------------------- asking


def explain(text):
    for line in textwrap.wrap(text, width=84):
        print("  " + line)


def ask(question, help="", default="", check=None, required=True):
    print()
    print(question)
    if help:
        explain(help)
    while True:
        raw = input(f"> [{default}] " if default else "> ").strip()
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


def parse_amount(value):
    try:
        amount = Decimal(value.replace(",", "").replace("₹", "").strip())
    except InvalidOperation:
        return None
    if amount < 0 or amount != amount.quantize(Decimal("0.01")) or amount >= Decimal("10000000"):
        return None
    return amount


def check_amount(value):
    return None if parse_amount(value) is not None else "Type an amount in rupees, like 2500 (0 if none)."


def rupees(amount):
    return f"{amount:,.0f}" if amount == amount.to_integral() else f"{amount:,.2f}"


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


# ---------------------------------------------------------------- the questions


class Command(BaseCommand):
    help = "Ask for the school's details (profile, session, classes, fees, administrator) one question at a time."

    def handle(self, *args, **options):
        print("School details")
        explain("Each question shows the current or suggested answer in [brackets]; press Enter to keep it. "
                "Each part is saved as soon as it is finished. Press Ctrl+C to stop.")
        done = []
        try:
            self.profile()
            done.append("school profile")
            session, next_session = self.sessions()
            done.append("sessions")
            classes = self.classes(session, next_session)
            done.append("classes and sections")
            seed_reference_data()
            if self.fees(session, classes):
                done.append("fees")
            self.administrator()
            done.append("administrator")
        except (KeyboardInterrupt, EOFError, Stop):
            print()
            print("Stopped. " + (f"Saved so far: {', '.join(done)}. " if done else "") + "Run it again to continue.")
            return
        print()
        self.stdout.write(self.style.SUCCESS("School details saved: " + ", ".join(done) + "."))
        explain("Still to do in the app: add the staff under Users, and check the subjects, periods, admission "
                "documents and grade scale under School setup (standard ones were filled in).")

    # -- 1. school profile

    def profile(self):
        print("\n-- 1. The school --")
        p = SchoolProfile.get()
        p.name = ask("School name?", "As printed on receipts, report cards and transfer certificates.", p.name)
        p.short_code = ask("Short code for application numbers?", "2 to 6 capital letters, e.g. LK gives LK-2026-0001.",
                           p.short_code, pattern(r"[A-Z]{1,6}", "Use 1 to 6 capital letters.")).upper()
        p.address = ask("Address?", "Street and town, on one line.", p.address)
        p.district = ask("District?", "", p.district)
        p.state = ask("State?", "", p.state)
        p.pincode = ask("PIN code?", "", p.pincode, pattern(r"\d{6}", "A PIN code is 6 digits."))
        p.phone = ask("School phone number?", "Shown to parents on receipts and messages.", p.phone,
                      pattern(r"[0-9+ -]{6,15}", "Type the number with digits only."))
        p.email = ask("School email? (optional)", "", p.email, pattern(r"[^@\s]+@[^@\s]+\.[^@\s]+", "Not an email."),
                      required=False)
        p.website = ask("School website? (optional)", "Like https://lotuskids.in", p.website,
                        pattern(r"https?://\S+", "Start it with https://"), required=False)
        p.udise_code = ask("UDISE+ code? (optional)", "The school's 11-digit code from the UDISE+ portal.",
                           p.udise_code, pattern(r"\d{11}", "A UDISE+ code is 11 digits."), required=False)
        boards = dict(SchoolProfile.BOARD_CHOICES)
        p.board = ask("Board? " + ", ".join(f"{key} = {label}" for key, label in boards.items()), "", p.board,
                      lambda v: None if v in boards else "Type one of: " + ", ".join(boards))
        p.affiliation_number = ask("Affiliation or recognition number? (optional)", "", p.affiliation_number,
                                   required=False)
        p.admission_number_prefix = ask(
            "Text before the admission (S.R.) number? (optional)",
            "For example 'LK/' gives LK/0001. Leave empty for plain numbers.", p.admission_number_prefix,
            pattern(r".{1,10}", "At most 10 characters."), required=False)
        p.admission_number_width = int(ask("How many digits in the admission number?",
                                           "4 gives 0001, 0002 and so on.", str(p.admission_number_width),
                                           whole_number(1, 8)))
        if Student.objects.exists():
            explain(f"The next admission number stays {p.next_admission_number}: students are already admitted.")
        else:
            p.next_admission_number = int(ask(
                "First admission number to give out?",
                "If the school's paper register already has numbers, continue from the next one.",
                str(p.next_admission_number), whole_number(1, 9999999)))
        p.save()

    # -- 2. sessions

    def sessions(self):
        print("\n-- 2. School year --")
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
        open_next = ask_yes(f"Accept online admission applications for next year ({session_name(end)})?",
                            "Parents apply on the website; the office reviews each application.",
                            default=True)
        with transaction.atomic():
            session = current or AcademicSession(name=session_name(start))
            if not current and AcademicSession.objects.filter(name=session.name).exists():
                session = AcademicSession.objects.get(name=session.name)
            session.start_date, session.end_date, session.is_current = start, end, True
            session.save()
            next_start = date(start.year + 1, start.month, start.day)
            next_session, _ = AcademicSession.objects.get_or_create(
                name=session_name(next_start),
                defaults={"start_date": next_start, "end_date": date(next_start.year + 1, end.month, end.day)},
            )
            next_session.admissions_open = open_next
            next_session.save()
        return session, next_session

    # -- 3. classes

    def classes(self, session, next_session):
        print("\n-- 3. Classes and sections --")
        existing = list(SchoolClass.objects.filter(is_active=True))
        names = [c.name for c in existing] or [name for name, _, _, _ in CLASSES]
        print("\nThe school's classes, youngest first:")
        explain(", ".join(names))
        if not ask_yes("Is this list right?", "Answer n to type the school's own list."):
            names = [n.strip() for n in ask(
                "Type the classes, youngest first, separated by commas.",
                "For example: Nursery, LKG, UKG, Class 1, Class 2, Class 3, Class 4, Class 5",
                check=lambda v: None if len({n.strip().lower() for n in v.split(",") if n.strip()}) ==
                len([n for n in v.split(",") if n.strip()]) else "A class appears twice.",
            ).split(",") if n.strip()]
        current_sections = sorted(set(Section.objects.filter(session=session).values_list("name", flat=True)))
        sections = [s.strip().upper() for s in ask(
            "Sections in each class, separated by commas?",
            "Most small schools have one section, A. Type A, B for two. You can give a class extra sections later "
            "in School setup.", ", ".join(current_sections) or "A",
            pattern(r"\s*[A-Za-z0-9]{1,10}\s*(,\s*[A-Za-z0-9]{1,10}\s*)*", "Like A or A, B"),
        ).split(",")]
        capacity = Section.objects.filter(session=session).values_list("capacity", flat=True).first() or 40
        capacity = int(ask("Most students in one section?", "Admissions warn when a section is full.", str(capacity),
                           whole_number(1, 200)))

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
            for s in (session, next_session):
                for school_class in chosen:
                    for section in sections:
                        row, created = Section.objects.get_or_create(
                            session=s, school_class=school_class, name=section, defaults={"capacity": capacity})
                        if not created and row.capacity != capacity:
                            row.capacity = capacity
                            row.save(update_fields=["capacity"])
        return chosen

    # -- 4. fees

    def fees(self, session, classes):
        print("\n-- 4. Fees --")
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
                    str(len(installments)) if str(len(installments)) in PLANS else "4",
                    lambda v: None if v in PLANS else "Type 1, 2, 4 or 12.")
        due_day = int(ask("On which day of the month is each installment due?",
                          "Parents get a WhatsApp reminder 3 days before.", "10", whole_number(1, 28)))
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
            amounts[code] = self.amounts_per_class(label, help_text, classes, code, old,
                                                   same_default=code != "tuition")
        extra = []
        while True:
            name = ask("Any other fee? Type its name, or press Enter if there are no more.",
                       "For example Transport fee or Computer fee.", required=False)
            if not name:
                break
            every = ask_yes(f"Is the {name} charged in every installment?",
                            "Answer n if it is charged once a year with the first installment.", default=False)
            code = slugify(name)[:30] or "fee"
            extra.append((code, name, False, "every" if every else "first", ""))
            amounts[code] = self.amounts_per_class(name, "", classes, code, old, same_default=True)

        with transaction.atomic():
            FeeAmount.objects.filter(installment__session=session).delete()
            Installment.objects.filter(session=session).delete()
            fee_heads = {}
            for order, (code, name, new_only, _, _) in enumerate(heads + extra, start=1):
                head, _ = FeeHead.objects.get_or_create(code=code, defaults={"name": name, "order": order})
                head.name, head.new_students_only, head.is_active = name, new_only, True
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
        return True

    def amounts_per_class(self, label, help_text, classes, code, old, same_default):
        olds = {old.get((code, c.pk)) for c in classes}
        if ask_yes(f"Is the {label.lower()} the same for every class?", help_text,
                   default=len(olds) == 1 if None not in olds else same_default):
            first = old.get((code, classes[0].pk)) if classes else None
            amount = parse_amount(ask(f"{label}, in rupees? (0 if none)", "",
                                      rupees(first) if first is not None else "", check_amount))
            return {c.pk: amount for c in classes}
        result = {}
        for c in classes:
            previous = old.get((code, c.pk))
            result[c.pk] = parse_amount(ask(f"{label} for {c.name}, in rupees? (0 if none)", "",
                                            rupees(previous) if previous is not None else "", check_amount))
        return result

    # -- 5. administrator

    def administrator(self):
        print("\n-- 5. Administrator login --")
        admins = User.objects.filter(role=User.Role.ADMIN, is_active=True)
        if admins.exists():
            explain("Administrators already set up: " + ", ".join(a.username for a in admins) + ".")
            if not ask_yes("Add or change an administrator login?", "", default=False):
                return
        explain("The administrator can do everything, including adding staff. Use it only for setup; the "
                "principal and staff get their own logins.")
        username = ask("Username?", "Small letters, no spaces. For example abhinav.", "",
                       pattern(r"[a-z0-9_.@+-]{3,30}", "3 to 30 small letters or digits, no spaces."))
        user = User.objects.filter(username=username).first()
        if user is None:
            user = User(username=username)
            user.first_name = ask("First name?", "", "")
            user.last_name = ask("Last name? (optional)", "", "", required=False)
            user.phone = ask("Mobile number? (optional)", "10 digits.", "",
                             pattern(r"[6-9]\d{9}", "Type the 10-digit mobile number."), required=False)
        elif not ask_yes(f"'{username}' already exists. Make it an administrator and set a new password?"):
            return
        while True:
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
