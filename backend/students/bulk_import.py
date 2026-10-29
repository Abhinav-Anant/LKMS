"""Bulk import of students (and their photos) from an Excel or CSV sheet.

For schools moving to LKMS with children already on the rolls. The sheet has
one row per student; `template_workbook()` builds a sample with this school's
own classes. `check()` reads every row and reports all problems at once;
`run()` imports only when there are none, so a sheet goes in whole or not at
all. Photos are matched to students by the sheet's Photo column, or else by
admission number (e.g. 0123.jpg).
"""

import csv
import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from academics.models import AcademicSession, Enrollment, SchoolClass, Section
from core import audit
from core.models import SchoolProfile
from core.storage import validate_upload

from .choices import BLOOD_GROUPS, Category, Gender, Relationship
from .models import Guardian, Student, StudentGuardian
from .validators import normalise_mobile

MAX_ROWS = 3000
MAX_PHOTO_MB = 5
MAX_ZIP_FILES = 5000
MAX_ZIP_TOTAL_MB = 800
PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png")


@dataclass(frozen=True)
class Column:
    key: str
    header: str
    required: bool = False
    help: str = ""
    example: str = ""


COLUMNS = [
    Column("admission_number", "Admission No", help="S.R. number from the admission register. Leave blank to give the next number automatically.", example="0101"),
    Column("admission_date", "Admission Date", help="DD-MM-YYYY. Blank means today.", example="01-04-2024"),
    Column("first_name", "First Name", True, example="Aarav"),
    Column("last_name", "Last Name", example="Sharma"),
    Column("date_of_birth", "Date of Birth", True, "DD-MM-YYYY", "10-05-2019"),
    Column("gender", "Gender", True, "Male, Female or Other", "Male"),
    Column("class", "Class", True, "Class name or code exactly as in LKMS (see the Lists sheet)."),
    Column("section", "Section", True, "e.g. A. A section missing in the current session is created.", "A"),
    Column("roll_number", "Roll No", help="Optional. Must be unique in the section.", example="1"),
    Column("admitted_in_class", "Admitted In Class", help="Class the child first joined. Blank means the same as Class."),
    Column("category", "Category", help="General, OBC, MBC, SC, ST or EWS. Blank means General.", example="General"),
    Column("religion", "Religion", example="Hindu"),
    Column("mother_tongue", "Mother Tongue", example="Hindi"),
    Column("nationality", "Nationality", help="Blank means Indian.", example="Indian"),
    Column("blood_group", "Blood Group", help="A+, A-, B+, B-, AB+, AB-, O+ or O-", example="B+"),
    Column("aadhaar_number", "Student Aadhaar", help="12 digits, optional.", example=""),
    Column("address_line", "Address", True, example="12 Gandhi Nagar"),
    Column("city", "City/Village", True, example="Jaipur"),
    Column("district", "District", True, example="Jaipur"),
    Column("state", "State", example="Rajasthan"),
    Column("pincode", "PIN Code", True, "6 digits", "302015"),
    Column("previous_school", "Previous School"),
    Column("father_name", "Father Name", example="Rohit Sharma"),
    Column("father_phone", "Father Mobile", help="10-digit mobile", example="9829012345"),
    Column("father_email", "Father Email"),
    Column("father_occupation", "Father Occupation", example="Business"),
    Column("father_qualification", "Father Qualification", example="B.Com"),
    Column("father_annual_income", "Father Annual Income", help="Rupees, numbers only"),
    Column("mother_name", "Mother Name", example="Neha Sharma"),
    Column("mother_phone", "Mother Mobile", example="9829054321"),
    Column("mother_email", "Mother Email"),
    Column("mother_occupation", "Mother Occupation", example="Homemaker"),
    Column("mother_qualification", "Mother Qualification", example="B.A."),
    Column("mother_annual_income", "Mother Annual Income"),
    Column("guardian_name", "Guardian Name", help="Only if someone other than the parents looks after the child."),
    Column("guardian_relationship", "Guardian Relationship", help="e.g. Uncle"),
    Column("guardian_phone", "Guardian Mobile"),
    Column("primary_contact", "Primary Contact", True, "Father, Mother or Guardian: who gets SMS/WhatsApp and the parent login.", "Father"),
    Column("parent_aadhaar_number", "Parent Aadhaar", True, "12-digit Aadhaar of the primary contact.", "234567890123"),
    Column("photo", "Photo File", help="File name of the photo, e.g. anaya.jpg. Blank means a photo named by admission number, e.g. 0101.jpg."),
]
COLUMN_BY_KEY = {c.key: c for c in COLUMNS}
PEOPLE = ("father", "mother", "guardian")


def _norm_header(text):
    return re.sub(r"[^a-z0-9]", "", str(text or "").lower())


HEADER_LOOKUP = {}
for _c in COLUMNS:
    HEADER_LOOKUP[_norm_header(_c.header)] = _c.key
    HEADER_LOOKUP[_norm_header(_c.key)] = _c.key
HEADER_LOOKUP.update({_norm_header(k): v for k, v in {
    "SR No": "admission_number", "S.R. No": "admission_number", "Scholar No": "admission_number",
    "DOB": "date_of_birth", "Name": "first_name", "Student Name": "first_name", "Roll Number": "roll_number",
    "Aadhaar": "aadhaar_number", "Pincode": "pincode", "PIN": "pincode", "City": "city", "Village": "city",
    "Father Phone": "father_phone", "Mother Phone": "mother_phone", "Guardian Phone": "guardian_phone",
    "Parent Aadhaar Number": "parent_aadhaar_number", "Guardian Aadhaar": "parent_aadhaar_number", "Photo": "photo",
}.items()})


# ----- reading the sheet -----------------------------------------------------

def read_sheet(uploaded_file):
    """Return a list of (row_number, {column_key: raw value}) from an .xlsx or .csv file."""
    name = (getattr(uploaded_file, "name", "") or "").lower()
    uploaded_file.seek(0)
    head = uploaded_file.read(4)
    uploaded_file.seek(0)
    if head.startswith(b"PK"):
        table = _read_xlsx(uploaded_file)
    elif name.endswith(".xls") or head.startswith(b"\xd0\xcf\x11\xe0"):
        raise ValidationError("This is an old Excel (.xls) file. In Excel use File > Save As > Excel Workbook (.xlsx), then upload that.")
    else:
        table = _read_csv(uploaded_file)

    header_index = next((i for i, row in enumerate(table[:10]) if sum(_norm_header(v) in HEADER_LOOKUP for v in row) >= 3), None)
    if header_index is None:
        raise ValidationError("Could not find the heading row. Use the sample file: its first row must hold the column names.")
    keys = [HEADER_LOOKUP.get(_norm_header(v)) for v in table[header_index]]
    missing = [c.header for c in COLUMNS if c.required and c.key not in keys]
    if missing:
        raise ValidationError("These columns are missing: " + ", ".join(missing) + ".")

    rows = []
    for offset, values in enumerate(table[header_index + 1:], start=header_index + 2):
        record = {}
        for key, value in zip(keys, values):
            if key and key not in record:
                record[key] = value
        if any(_text(v) for v in record.values()):
            rows.append((offset, record))
    if not rows:
        raise ValidationError("The sheet has no students in it.")
    if len(rows) > MAX_ROWS:
        raise ValidationError(f"At most {MAX_ROWS} students can be imported at once; split the sheet.")
    return rows


def _read_xlsx(uploaded_file):
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(uploaded_file, read_only=True, data_only=True)
    except Exception as exc:
        raise ValidationError("The Excel file could not be read. Save it again as .xlsx and retry.") from exc
    sheet = workbook["Students"] if "Students" in workbook.sheetnames else workbook.worksheets[0]
    table = [list(row) for row in sheet.iter_rows(values_only=True)]
    workbook.close()
    return table


def _read_csv(uploaded_file):
    raw = uploaded_file.read()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValidationError("The CSV file is not plain text. Use the sample .xlsx file instead.")
    return [row for row in csv.reader(io.StringIO(text))]


# ----- cleaning values -------------------------------------------------------

def _text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return re.sub(r"\s+", " ", str(value)).strip()


def _digits(value):
    return re.sub(r"\D", "", _text(value))


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and 1 < value < 80000:  # an Excel serial date that lost its format
        return date(1899, 12, 30) + timedelta(days=int(value))
    text = _text(value)
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%m-%y", "%d/%m/%y", "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError("Write the date as DD-MM-YYYY, e.g. 10-05-2019.")


def _choice(value, choices, what):
    text = _text(value).lower()
    for code, label in choices:
        if text in (str(code).lower(), str(label).lower()):
            return code
    raise ValueError(f"Use one of: {', '.join(str(label) for _, label in choices)}.")


def _gender(value):
    text = _text(value).lower()
    aliases = {"boy": "M", "girl": "F", "b": "M", "g": "F"}
    if text in aliases:
        return aliases[text]
    return _choice(value, Gender.choices, "gender")


def _mobile(value):
    number = normalise_mobile(_text(value))
    if not re.fullmatch(r"[6-9]\d{9}", number):
        raise ValueError("Enter a 10-digit Indian mobile number.")
    return number


def _aadhaar(value):
    number = _digits(value)
    if not re.fullmatch(r"\d{12}", number):
        raise ValueError("Aadhaar number must be 12 digits.")
    return number


def _pincode(value):
    number = _digits(value)
    if not re.fullmatch(r"[1-9]\d{5}", number):
        raise ValueError("Enter a 6-digit PIN code.")
    return number


def _roll(value):
    text = _text(value)
    if not re.fullmatch(r"\d{1,3}", text) or int(text) == 0:
        raise ValueError("Roll number must be a whole number, e.g. 12.")
    return int(text)


def _money(value):
    text = _text(value).replace(",", "").replace("₹", "").strip()
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("Write the amount in numbers only, e.g. 250000.") from exc
    if amount < 0 or amount >= Decimal("1e10"):
        raise ValueError("Amount is not valid.")
    return amount


def _email(value):
    from django.core.validators import validate_email

    text = _text(value)
    try:
        validate_email(text)
    except ValidationError as exc:
        raise ValueError("Enter a valid email address.") from exc
    return text


# ----- checking --------------------------------------------------------------

@dataclass
class Report:
    session: AcademicSession | None = None
    total: int = 0
    errors: list = field(default_factory=list)
    students: list = field(default_factory=list)
    new_sections: list = field(default_factory=list)
    photos_matched: int = 0
    photos_unused: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.errors

    def error(self, row, column_key, message):
        header = COLUMN_BY_KEY[column_key].header if column_key in COLUMN_BY_KEY else column_key
        self.errors.append({"row": row, "column": header, "message": message})

    def as_dict(self):
        return {
            "session": self.session.name if self.session else None,
            "total": self.total,
            "ok": not self.errors,
            "errors": self.errors,
            "students": self.students,
            "new_sections": self.new_sections,
            "photos_matched": self.photos_matched,
            "photos_unused": self.photos_unused[:200],
        }


def _class_lookup():
    lookup = {}
    for school_class in SchoolClass.objects.all():
        lookup[_norm_header(school_class.name)] = school_class
        lookup.setdefault(_norm_header(school_class.code), school_class)
        # "Class 1" and "1", "1st" all find Class 1
        if school_class.name.lower().startswith("class "):
            lookup.setdefault(_norm_header(school_class.name[6:]), school_class)
    return lookup


def _photo_key(name):
    return PurePosixPath(str(name).replace("\\", "/")).name.lower()


def _photo_stem(name):
    return PurePosixPath(_photo_key(name)).stem


def check(rows, session=None, photo_names=None):
    """Clean and check every row. Returns (report, cleaned rows). Nothing is saved."""
    session = session or AcademicSession.current()
    report = Report(session=session, total=len(rows))
    if session is None:
        report.error(0, "class", "There is no current academic session. Set one up in Classes & sessions first.")
        return report, []

    classes = _class_lookup()
    sections = {(s.school_class_id, s.name.upper()): s for s in Section.objects.filter(session=session)}
    existing_numbers = set(Student.objects.values_list("admission_number", flat=True))
    taken_rolls = {
        (section_id, roll) for section_id, roll in
        Enrollment.objects.filter(session=session, roll_number__isnull=False).values_list("section_id", "roll_number")
    }
    photo_names = {_photo_key(n): n for n in (photo_names or [])}
    photo_stems = {}
    for key in photo_names:
        if key.endswith(PHOTO_EXTENSIONS):
            photo_stems.setdefault(_photo_stem(key), key)
    used_photos = set()
    seen_numbers, seen_rolls, seen_children, new_sections = {}, {}, {}, {}
    cleaned = []

    for row_number, raw in rows:
        data, problems = {}, []

        def fail(key, message):
            problems.append(key)
            report.error(row_number, key, message)

        def take(key, convert=_text, required=None):
            value = raw.get(key)
            if not _text(value) and not isinstance(value, (date, datetime)):
                if required if required is not None else COLUMN_BY_KEY[key].required:
                    fail(key, "This is required.")
                return None
            try:
                return convert(value)
            except ValueError as exc:
                fail(key, str(exc))
                return None

        number = take("admission_number")
        if number:
            if len(number) > 20:
                fail("admission_number", "At most 20 characters.")
            elif number in existing_numbers:
                fail("admission_number", f"A student with admission number {number} is already in LKMS.")
            elif number in seen_numbers:
                fail("admission_number", f"Same admission number as row {seen_numbers[number]}.")
            seen_numbers.setdefault(number, row_number)
        data["admission_number"] = number or ""
        data["admission_date"] = take("admission_date", _date) or timezone.localdate()
        for key, limit in (("first_name", 50), ("last_name", 50), ("religion", 50), ("mother_tongue", 50),
                           ("nationality", 50), ("address_line", 500), ("city", 100), ("district", 100), ("state", 100),
                           ("previous_school", 200)):
            value = take(key) or ""
            if len(value) > limit:
                fail(key, f"At most {limit} characters.")
            data[key] = value
        data["nationality"] = data["nationality"] or "Indian"
        data["date_of_birth"] = take("date_of_birth", _date)
        if data["date_of_birth"] and not (date(1990, 1, 1) <= data["date_of_birth"] <= timezone.localdate()):
            fail("date_of_birth", "Date of birth looks wrong. Write it as DD-MM-YYYY.")
        data["gender"] = take("gender", _gender)
        data["category"] = take("category", lambda v: _choice(v, Category.choices, "category")) or Category.GENERAL
        data["blood_group"] = take("blood_group", lambda v: _choice(v.upper().replace(" ", "") if isinstance(v, str) else v, BLOOD_GROUPS, "blood group")) or ""
        data["aadhaar_number"] = take("aadhaar_number", _aadhaar) or ""
        data["pincode"] = take("pincode", _pincode) or ""

        class_text = take("class")
        school_class = None
        if class_text:
            school_class = classes.get(_norm_header(class_text))
            if school_class is None:
                fail("class", f"No class called \"{class_text}\" in LKMS. See the Lists sheet for the names.")
        admitted_text = take("admitted_in_class")
        data["admitted_in_class"] = school_class
        if admitted_text:
            data["admitted_in_class"] = classes.get(_norm_header(admitted_text))
            if data["admitted_in_class"] is None:
                fail("admitted_in_class", f"No class called \"{admitted_text}\" in LKMS.")

        section_name = (take("section") or "").upper()
        if len(section_name) > 10:
            fail("section", "At most 10 characters, e.g. A.")
            section_name = ""
        data["section"] = None
        if school_class and section_name:
            section = sections.get((school_class.pk, section_name))
            if section is None:
                new_key = (school_class.pk, section_name)
                new_sections.setdefault(new_key, f"{school_class.name} {section_name}")
            data["section"] = section
            data["section_key"] = (school_class.pk, section_name)
            data["section_label"] = f"{school_class.name} {section_name}"

        roll = take("roll_number", _roll)
        data["roll_number"] = roll
        if roll and data.get("section_key"):
            section = data["section"]
            if section and (section.pk, roll) in taken_rolls:
                fail("roll_number", f"Roll number {roll} is already used in {data['section_label']}.")
            elif (data["section_key"], roll) in seen_rolls:
                fail("roll_number", f"Same roll number as row {seen_rolls[(data['section_key'], roll)]} in {data['section_label']}.")
            seen_rolls.setdefault((data["section_key"], roll), row_number)

        for person in PEOPLE:
            name = take(f"{person}_name") or ""
            phone = take(f"{person}_phone", _mobile)
            if len(name) > 100:
                fail(f"{person}_name", "At most 100 characters.")
            if phone and not name:
                fail(f"{person}_name", f"Give the {person}'s name with the mobile number.")
            data[f"{person}_name"], data[f"{person}_phone"] = name, phone or ""
            data[f"{person}_email"] = take(f"{person}_email", _email) or "" if person != "guardian" else ""
            if person != "guardian":
                data[f"{person}_occupation"] = (take(f"{person}_occupation") or "")[:100]
                data[f"{person}_qualification"] = (take(f"{person}_qualification") or "")[:100]
                data[f"{person}_annual_income"] = take(f"{person}_annual_income", _money)
        data["guardian_relationship"] = (take("guardian_relationship") or "")[:50]
        if not any(data[f"{p}_name"] for p in PEOPLE):
            fail("father_name", "Give at least one parent or guardian.")

        primary = take("primary_contact", lambda v: _choice(v, Relationship.choices, "primary contact"))
        data["primary_contact"] = primary
        if primary and not data[f"{primary}_phone"]:
            fail(f"{primary}_phone", f"The primary contact is the {primary}, so the {primary}'s mobile number is required.")
        data["parent_aadhaar_number"] = take("parent_aadhaar_number", _aadhaar)

        child = (data["first_name"].lower(), data["last_name"].lower(), data["date_of_birth"])
        if data["first_name"] and data["date_of_birth"]:
            if child in seen_children:
                fail("first_name", f"Same child (name and date of birth) as row {seen_children[child]}.")
            seen_children.setdefault(child, row_number)

        photo = take("photo") or ""
        data["photo"] = None
        if photo:
            key = _photo_key(photo)
            if key not in photo_names:  # "aarav" or "aarav.jpg" finds aarav.png too
                key = photo_stems.get(_photo_stem(key) if key.endswith(PHOTO_EXTENSIONS) else key, key)
            if photo_names and key in photo_names:
                data["photo"] = key
            elif photo_names is not None:
                fail("photo", f"No photo called {photo} among the photos uploaded.")
        elif number and photo_stems.get(number.lower()):
            data["photo"] = photo_stems[number.lower()]
        if data["photo"]:
            used_photos.add(data["photo"])

        data["row"] = row_number
        if not problems:
            cleaned.append(data)
        report.students.append({
            "row": row_number,
            "name": f"{data['first_name']} {data['last_name']}".strip(),
            "admission_number": number or "",
            "class": data.get("section_label", class_text or ""),
            "photo": photo_names.get(data["photo"], "") if data["photo"] else "",
            "photo_column": photo,
        })

    report.new_sections = sorted(new_sections.values())
    report.photos_matched = len(used_photos)
    report.photos_unused = sorted(photo_names[k] for k in photo_names if k not in used_photos and k.endswith(PHOTO_EXTENSIONS))
    return report, cleaned


# ----- importing -------------------------------------------------------------

def run(request, rows, session=None, photos=None, photo_names=None):
    """Check, then import every student, all or none. `photos` maps file names to bytes.

    `photo_names` instead lists photos the browser holds and uploads itself afterwards, by the
    admission numbers in the report. Nothing is saved when any row has a problem (see report.errors).
    """
    photos = {_photo_key(k): v for k, v in (photos or {}).items()}
    names = list(photos) if photos else photo_names
    report, cleaned = check(rows, session, photo_names=names)
    if report.errors:
        return report
    processed = {}
    for row in cleaned:
        if row["photo"] and row["photo"] in photos and row["photo"] not in processed:
            try:
                processed[row["photo"]] = prepare_photo(photos[row["photo"]])
            except ValidationError as exc:
                report.error(row["row"], "photo", " ".join(exc.messages))
    if report.errors:
        return report

    with transaction.atomic():
        sections = {}
        for row in cleaned:
            key = row["section_key"]
            if key not in sections:
                section = row["section"]
                if section is None:
                    section, _ = Section.objects.get_or_create(session=report.session, school_class_id=key[0], name=key[1])
                sections[key] = section
        incoming = {}
        for row in cleaned:
            incoming[sections[row["section_key"]].pk] = incoming.get(sections[row["section_key"]].pk, 0) + 1
        for section_id, count in incoming.items():
            section = Section.objects.select_for_update().get(pk=section_id)
            active = section.enrollments.filter(status=Enrollment.Status.ACTIVE).count()
            if active + count > section.capacity:
                raise ValidationError(
                    f"{section.school_class.name} {section.name} holds {section.capacity} students; it already has {active} "
                    f"and the sheet adds {count}. Raise the section's capacity in Classes & sessions first."
                )

        for index, row in enumerate(cleaned):
            student = _create_student(row, sections[row["section_key"]], report.session)
            if row["photo"] in processed:
                student.photo.save("photo.jpg", ContentFile(processed[row["photo"]]), save=True)
            audit.record(request, "student.created", student, imported=True, sheet_row=row["row"])
            report.students[_index_of(report, row["row"])]["admission_number"] = student.admission_number
            report.students[_index_of(report, row["row"])]["id"] = student.pk
        audit.record(request, "students.imported", SchoolProfile.get(), count=len(cleaned),
                     photos=len(processed), new_sections=report.new_sections, session=report.session.name)
    return report


def _index_of(report, row_number):
    for i, student in enumerate(report.students):
        if student["row"] == row_number:
            return i
    raise KeyError(row_number)


def _create_student(row, section, session):
    student = Student.objects.create(
        admission_number=row["admission_number"] or SchoolProfile.allocate_admission_number(),
        admission_date=row["admission_date"],
        admitted_in_class=row["admitted_in_class"],
        **{f: row[f] for f in (
            "first_name", "last_name", "date_of_birth", "gender", "category", "religion", "mother_tongue",
            "nationality", "blood_group", "aadhaar_number", "address_line", "city", "district", "state",
            "pincode", "previous_school",
        )},
    )
    full_address = ", ".join(p for p in (row["address_line"], row["city"], f"{row['district']} {row['pincode']}".strip()) if p)
    for person in PEOPLE:
        name, phone = row[f"{person}_name"], row[f"{person}_phone"]
        if not (name and phone):
            continue
        guardian = Guardian.objects.filter(phone=phone, full_name__iexact=name).first()
        if guardian is None:
            guardian = Guardian.objects.create(
                full_name=name, phone=phone, email=row[f"{person}_email"], address=full_address,
                occupation=row.get(f"{person}_occupation", "") or "",
                qualification=row.get(f"{person}_qualification", "") or "",
                annual_income=row.get(f"{person}_annual_income"),
            )
        else:  # a sibling's parent: fill in blanks only
            for f in ("email", "occupation", "qualification", "annual_income"):
                value = row.get(f"{person}_{f}")
                if value and not getattr(guardian, f):
                    setattr(guardian, f, value)
            guardian.save()
        is_primary = person == row["primary_contact"]
        if is_primary and not guardian.aadhaar_number:
            guardian.aadhaar_number = row["parent_aadhaar_number"]
            guardian.save(update_fields=["aadhaar_number", "updated_at"])
        StudentGuardian.objects.create(
            student=student, guardian=guardian, relationship=person, is_primary_contact=is_primary,
            relationship_detail=row["guardian_relationship"] if person == "guardian" else "",
        )
    Enrollment.objects.create(
        student=student, session=session, section=section, roll_number=row["roll_number"], enrolled_on=row["admission_date"],
    )
    return student


# ----- photos ----------------------------------------------------------------

def prepare_photo(content):
    """Check an uploaded photo and return it as a JPEG of at most 600 px, without camera details (GPS etc.)."""
    from PIL import Image, ImageOps

    if content is None:
        raise ValidationError(f"Photo is larger than {MAX_PHOTO_MB} MB.")
    upload = ContentFile(content, name="photo")
    validate_upload(upload, allowed=("jpg", "png"), max_mb=MAX_PHOTO_MB)
    with Image.open(upload) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((600, 600))
        out = io.BytesIO()
        img.save(out, "JPEG", quality=85)
    return out.getvalue()


def photos_from_zip(uploaded_file):
    """Read the photos in a ZIP into {lower-case file name: bytes}. Folders inside the ZIP are ignored."""
    try:
        archive = zipfile.ZipFile(uploaded_file)
    except zipfile.BadZipFile as exc:
        raise ValidationError("The photos file is not a ZIP file.") from exc
    entries = [i for i in archive.infolist() if not i.is_dir() and not i.filename.startswith("__MACOSX/")
               and not _photo_key(i.filename).startswith(".") and _photo_key(i.filename).endswith(PHOTO_EXTENSIONS)]
    if len(entries) > MAX_ZIP_FILES:
        raise ValidationError(f"The ZIP has more than {MAX_ZIP_FILES} photos; split it.")
    if sum(i.file_size for i in entries) > MAX_ZIP_TOTAL_MB * 1024 * 1024:
        raise ValidationError(f"The photos add up to more than {MAX_ZIP_TOTAL_MB} MB; split the ZIP.")
    photos = {}
    for info in entries:
        if info.file_size > MAX_PHOTO_MB * 1024 * 1024:
            photos[_photo_key(info.filename)] = None  # reported as too big when used
            continue
        photos[_photo_key(info.filename)] = archive.read(info)
    return photos


def attach_photos(request, photos, replace=True):
    """Give existing students their photos. File names are admission numbers, e.g. 0101.jpg.

    Returns {"saved": [...], "skipped": [...], "unmatched": [...], "errors": [...]}.
    """
    result = {"saved": [], "skipped": [], "unmatched": [], "errors": []}
    students = {s.admission_number.lower(): s for s in Student.objects.all().only("id", "admission_number", "photo", "first_name", "last_name")}
    for name, content in sorted(photos.items()):
        student = students.get(_photo_stem(name))
        if student is None:
            result["unmatched"].append(name)
            continue
        if student.photo and not replace:
            result["skipped"].append(name)
            continue
        try:
            jpeg = prepare_photo(content)
        except ValidationError as exc:
            result["errors"].append({"file": name, "message": " ".join(exc.messages)})
            continue
        old = student.photo.name if student.photo else None
        student.photo.save("photo.jpg", ContentFile(jpeg), save=True)
        if old:
            student.photo.storage.delete(old)
        audit.record(request, "student.photo_uploaded", student, file=name, replaced=bool(old))
        result["saved"].append({"file": name, "admission_number": student.admission_number, "name": student.full_name})
    return result


# ----- the sample file -------------------------------------------------------

def template_workbook(with_examples=True):
    """An .xlsx sample with this school's classes: a Students sheet, Instructions and Lists (for the drop-downs)."""
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    school = SchoolProfile.get()
    classes = list(SchoolClass.objects.filter(is_active=True).order_by("order"))
    session = AcademicSession.current()
    sections = sorted({s.name for s in Section.objects.filter(session=session)} or {"A"}) if session else ["A"]

    book = Workbook()
    sheet = book.active
    sheet.title = "Students"
    required_fill = PatternFill("solid", fgColor="FDE68A")
    optional_fill = PatternFill("solid", fgColor="E5E7EB")
    for index, column in enumerate(COLUMNS, start=1):
        cell = sheet.cell(row=1, column=index, value=column.header + (" *" if column.required else ""))
        cell.font = Font(bold=True)
        cell.fill = required_fill if column.required else optional_fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        if column.help:
            cell.comment = Comment(column.help, "LKMS")
        sheet.column_dimensions[get_column_letter(index)].width = max(12, min(28, len(column.header) + 4))
    sheet.freeze_panes = "C2"
    sheet.row_dimensions[1].height = 32

    # Text cells, so Excel keeps leading zeros in numbers, phones and Aadhaar.
    text_keys = {"admission_number", "aadhaar_number", "pincode", "father_phone", "mother_phone", "guardian_phone",
                 "parent_aadhaar_number", "admission_date", "date_of_birth"}
    for index, column in enumerate(COLUMNS, start=1):
        if column.key in text_keys:
            for row in range(2, 1002):
                sheet.cell(row=row, column=index).number_format = "@"

    if with_examples:
        first = classes[0].name if classes else "Class 1"
        second = classes[(len(classes) - 1) // 2].name if classes else "Class 2"
        examples = [
            {**{c.key: c.example for c in COLUMNS}, "class": second},
            {**{c.key: c.example for c in COLUMNS}, "class": first, "admission_number": "", "first_name": "Anaya",
             "gender": "Female", "date_of_birth": "15-06-2023", "roll_number": "", "admitted_in_class": "", "blood_group": "",
             "photo": "anaya.jpg", "primary_contact": "Mother", "parent_aadhaar_number": "345678901234",
             "father_occupation": "", "father_qualification": "", "mother_occupation": "Teacher"},
        ]
        for r, example in enumerate(examples, start=2):
            for index, column in enumerate(COLUMNS, start=1):
                sheet.cell(row=r, column=index, value=example.get(column.key) or None)

    lists = book.create_sheet("Lists")
    columns = {
        "Class": [c.name for c in classes],
        "Section": sections,
        "Gender": [label for _, label in Gender.choices],
        "Category": [label for _, label in Category.choices],
        "Blood Group": [g for g, _ in BLOOD_GROUPS],
        "Primary Contact": [label for _, label in Relationship.choices],
    }
    for index, (title, values) in enumerate(columns.items(), start=1):
        lists.cell(row=1, column=index, value=title).font = Font(bold=True)
        for r, value in enumerate(values, start=2):
            lists.cell(row=r, column=index, value=value)
        lists.column_dimensions[get_column_letter(index)].width = 20
        target = {"Class": ["class", "admitted_in_class"], "Gender": ["gender"], "Category": ["category"],
                  "Blood Group": ["blood_group"], "Primary Contact": ["primary_contact"]}.get(title, [])
        if values and target:
            letter = get_column_letter(index)
            validation = DataValidation(type="list", formula1=f"=Lists!${letter}$2:${letter}${len(values) + 1}", allow_blank=True)
            validation.error = "Pick a value from the list."
            sheet.add_data_validation(validation)
            for key in target:
                col = get_column_letter([c.key for c in COLUMNS].index(key) + 1)
                validation.add(f"{col}2:{col}3000")

    guide = book.create_sheet("Instructions", 0)
    guide.column_dimensions["A"].width = 26
    guide.column_dimensions["B"].width = 100
    lines = [
        (f"Student import for {school.name or 'your school'}", ""),
        ("", ""),
        ("How to use", "1. Fill the Students sheet, one row per student. Delete the two example rows first."),
        ("", "2. Columns marked * (yellow) are required. Hover over a heading for help."),
        ("", "3. Dates as DD-MM-YYYY. Mobile numbers as 10 digits. Aadhaar as 12 digits."),
        ("", "4. In LKMS go to Students > Import students, choose this file (and the photos), press Check, fix any errors, then Import."),
        ("", f"5. Students join the current session{f' ({session.name})' if session else ''}. Nothing is saved if any row has a problem."),
        ("", ""),
        ("Photos", "Put the photos in one folder or ZIP file (JPEG or PNG, up to 5 MB each)."),
        ("", "Either name each photo by the admission number (0101.jpg), or write the photo's file name in the Photo File column."),
        ("", "Photos are resized and the camera details (such as location) are removed."),
        ("", ""),
        ("Columns", "Help"),
    ]
    for column in COLUMNS:
        lines.append((column.header + (" *" if column.required else ""), column.help or ""))
    for r, (a, b) in enumerate(lines, start=1):
        guide.cell(row=r, column=1, value=a).font = Font(bold=bool(a))
        guide.cell(row=r, column=2, value=b).alignment = Alignment(wrap_text=True)
    guide["A1"].font = Font(bold=True, size=14)
    book.active = 1

    out = io.BytesIO()
    book.save(out)
    return out.getvalue()
