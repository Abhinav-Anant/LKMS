# Importing students in bulk

For a school moving to LKMS with children already on the rolls. New admissions still go through the
admission form; this is for the existing list.

Who: the administrator and the principal (capability `students.import`).
Where: **Students > Import students** (`/staff/students/import`).

## Steps

1. **Download sample (.xlsx).** The sample is built from this school's own classes and sections. It has:
   - *Instructions*: what each column means.
   - *Students*: the sheet to fill, one row per student, with two example rows to delete. Required headings
     are yellow and marked `*`; hovering over a heading shows its help. Drop-downs for class, gender, category,
     blood group and primary contact.
   - *Lists*: the values the drop-downs use.
2. **Fill the sheet.** Required: first name, date of birth (DD-MM-YYYY), gender, class, section, address,
   city/village, district, PIN code, primary contact (Father, Mother or Guardian), that person's mobile, and the
   parent's Aadhaar (12 digits, of the primary contact). Leave *Admission No* blank to take the next number from
   the admission register (School settings), or fill in the school's existing S.R. numbers.
3. **Photos (optional).** JPEG or PNG, up to 5 MB each, in a ZIP or chosen together. Name each by admission
   number (`0101.jpg`), or write the file name in the *Photo File* column (needed when the admission number is
   left blank). Photos are cut down to 600 px and the camera details (such as location) removed.
4. **Check sheet.** Every problem in every row is listed with its Excel row number and column. Nothing is saved.
5. **Import.** Only when the check is clean. The import is all or nothing. Students join the current session
   in the given class and section; a section not yet in the session is created (the check lists these). Parents
   with the same name and mobile are shared between siblings. Each student gets an audit entry.

Photos for students already in LKMS can be added or replaced at the bottom of the same page, named by
admission number.

## What is refused

An admission number already in LKMS or repeated in the sheet; the same child (name and date of birth) twice;
a roll number already used in the section; an unknown class; a section that would go over its capacity; bad
dates, mobile numbers, Aadhaar or PIN codes; a Photo File name not among the chosen photos. Old `.xls` files
must be saved as `.xlsx` first. At most 3000 rows per sheet.

## On the server

For very large photo sets, copy the files to the server and run as the `lkms` user in `/srv/lkms/backend`:

    .venv/bin/python manage.py import_students --sample sample.xlsx           # write the sample
    .venv/bin/python manage.py import_students students.xlsx --photos photos.zip --check
    .venv/bin/python manage.py import_students students.xlsx --photos photos.zip

`--photos` takes a ZIP or a folder.
