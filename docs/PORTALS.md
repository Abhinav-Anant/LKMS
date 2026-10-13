# Portals: teachers, parents and the school office (Phase 3)

## Signing in

| Who | How | Where |
| --- | --- | --- |
| Staff | Username and password. New accounts and resets get a temporary password; the person must choose their own at first sign-in. | `/staff/login` |
| Parents | Mobile number and a one-time 6-digit code. | `/parent/login` (the **Parents** link on the public site) |

### Parent codes

A parent account is the guardian mobile number on the student record. Every studying child whose guardian has that
number appears under the one sign-in, so brothers and sisters show together.

There are two ways to get a code:

1. **The parent asks for one** on the sign-in page. The code is valid for 10 minutes. It is meant to go out on
   WhatsApp, which arrives in Phase 4. **Until then the code is only written to the server log** (and hidden there
   when `DJANGO_DEBUG` is off), so parents cannot actually receive it yet.
2. **The school office issues one** from the student's page: **Parent sign-in code** under a parent's details.
   It is valid for 24 hours, is shown once and is recorded in the audit log. The parent opens the sign-in page,
   chooses *I already have a code from the school office*, and enters it. This works today.

Safety rules: only a keyed hash of each code is stored; a new code cancels the old one; five wrong tries lock the
code; at most 3 requested codes per number per 15 minutes; the request page gives the same answer whether or not
the number is registered, so numbers cannot be checked one by one.

Parent accounts have no password and cannot use the staff sign-in or any staff page.

## Teachers

**My classes** lists the sections the teacher is class teacher of or teaches a subject in, and their week's timetable.

- **Attendance:** the class teacher marks each child Present, Absent, Late or On leave for the day
  (*Mark the rest present* fills in the rest). Teachers can correct up to 7 days back; older days and other
  classes need the principal. No future dates, no Sundays. Subject teachers can view the register but not change it.
  *Monthly summary* shows each child's totals; late counts as present, under 75% is shown in red.
- **Tests and marks:** a subject teacher creates a test (name, date, maximum marks) for a subject they teach in that
  section and enters marks, absences and remarks. Marks stay a draft until **Show to parents**. After that only the
  principal can change or withdraw them. The class teacher can see every subject's tests for their class.
- **Notices:** teachers post to parents of their own classes.

## Parents

After signing in, a parent sees each child, and for each child:

- **Attendance** for any month, with the percentage.
- **Fees:** bills, what is due, a **Pay** button that opens the existing UPI QR payment page (see `FEES.md`), and
  receipts to download.
- **Marks** that teachers have shown to parents.
- **Timetable** for the child's class.

**Notices** shows school-wide notices for parents and notices for their children's classes.

## Principal and administrator

- **Dashboard:** students by class, today's attendance and which registers are not marked, fees billed, collected
  and outstanding, and what is waiting (admissions, UPI payments to check, concession requests).
- **School setup:** class teachers and section capacity, subject teachers per section, the timetable grid,
  bell times, subjects and academic sessions (make current, open or close admissions). A teacher cannot be put in two
  classes in the same period.
- **Users:** add staff with a temporary password, change role, deactivate, reset password. Only an administrator can
  create or change administrator accounts. Nobody can deactivate themselves. The page also shows which role can do
  what. Changing those rules is a code change in `backend/core/permissions.py`.
- **Notices:** office staff, principal and administrator post to everyone, staff only, or parents, for the whole
  school or chosen classes.

## Placeholders to confirm with the school

`seed_lkms_defaults` adds 10 subjects and 6 periods (8:00 to 12:20) as placeholders. The 7-day correction window
and the 75% attendance warning are also guesses.

## API

| Area | Endpoints |
| --- | --- |
| Parent sign-in | `POST /api/v1/auth/parent/request-code/`, `POST /api/v1/auth/parent/verify-code/`, `POST /api/v1/auth/parent/issue-code/` (office) |
| Staff accounts | `/api/v1/auth/users/` (+ `reset-password/`), `GET /api/v1/auth/permissions/` |
| Teaching | `/api/v1/academics/subjects/`, `teaching-assignments/`, `periods/`, `timetable/`, `my-sections/`, `my-timetable/` |
| Attendance | `GET/POST /api/v1/attendance/sheet/?section=&date=`, `GET /api/v1/attendance/month/?section=&month=` |
| Marks | `/api/v1/assessments/` (+ `marks/`, `publish/`, `unpublish/`) |
| Notices | `/api/v1/notices/` |
| Parent portal | `/api/v1/parent/children/`, `children/<id>/attendance/`, `fees/`, `receipts/<payment>/`, `marks/`, `timetable/`, `/api/v1/parent/notices/` |
| Reports | `GET /api/v1/reports/dashboard/` |
