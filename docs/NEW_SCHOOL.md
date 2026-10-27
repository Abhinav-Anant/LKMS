# Setting up LKMS for a new school

Each school gets its **own installation**: its own server (or VPS), database, web address and WhatsApp number.
Schools never share data. Setting one up takes three steps:

1. **Collect the school's answers** with the checklist below, before you touch the server.
2. **Put them in an answers file** (optional, but it makes the wizard mostly "press Enter").
3. **Rent the server and run the wizard** as described in `DEPLOY.md`:
   `sudo python3 /srv/lkms/deploy/setup_wizard.py --school school.json`.

Everything the wizard asks can be changed later by the school's administrator in the app (**School settings**,
**School setup**, **Fees > Setup**, **Exams > Grade scale**, **Users**), so a wrong answer is never a disaster.

## 1. What to collect from the school

Send this list to the school. Items marked *optional* can be skipped.

**Server**
- The web address it wants, e.g. `erp.greenvalleyschool.in` (the school or you must own the domain).
- Whether it wants WhatsApp alerts to parents, and a phone with WhatsApp to link (not a brand-new SIM).
- *Optional:* where off-site backup copies should go (Google Drive, another server).

**The school**
- Full name, as on certificates; a short code for application numbers (e.g. GVPS).
- Address, district, state, PIN code, office phone; *optional:* email, website.
- *Optional:* UDISE+ code (11 digits), affiliation or recognition number.
- Board: CBSE, CISCE (ICSE), a state board (and its full name, e.g. Rajasthan Board of Secondary Education), or none.
- *Optional:* logo (PNG or JPEG), and the school's colour.
- *Optional:* where the school is on the map (latitude, longitude) and its Facebook, Instagram, YouTube and X links,
  shown on the front page. School photos for the website's gallery are uploaded later in the app.

**Admissions**
- Admission (S.R.) number format: any text before the number (e.g. `GV/`), number of digits, and the next number
  if the school already has a paper register.
- School year dates (usually 1 April to 31 March), and the date on which a child's age is checked.
- Classes offered, youngest first, and sections in each (A, B…), and the most students per section.
- Age limits for the youngest classes (e.g. Play Group 2 to 3, Nursery 3 to 4 years).
- Documents parents must upload (birth certificate, photo, ID proof…), and which are optional.

**Teaching**
- Subjects taught.
- Bell times: when the first period starts, period length, number of periods, and the break (after which period,
  how long).
- Grade scale: A+ to E, or the 8-point A1 to E used by CBSE.

**Fees**
- The school's UPI ID and the name on that account; *optional:* a photo of the bank's QR code (otherwise LKMS makes
  one from the UPI ID).
- How often fees are collected (once, twice, four times or twelve times a year) and the due day of the month.
- Tuition fee per installment, class by class; admission fee (new students only); annual charges; exam fee; any
  other fees (transport, computer…) and whether each is charged every installment or once a year.
- Whether office staff may take cash or cheque payments at the counter.
- How many days before a due date parents get a WhatsApp reminder, and how often while a fee is overdue.

**People**
- The administrator: name, mobile number and a username (they choose their password during setup).
- *Optional:* the principal, office staff, accountant and teachers: name, role and mobile number. Each gets a
  temporary password and must change it at first sign-in.

Finally, ask the school to check `BOARD_CHECKS.md` (TC layout, report card, pass marks) with its board.

## 2. The answers file

A JSON file whose values become the wizard's suggested answers. Leave out anything you do not know: the wizard
asks for it. Pictures are named relative to the file and kept next to it. Two complete examples:

- `examples/lotus-kids/school.json`: Lotus Kids School, Rajasthan board, with its UPI QR picture.
- `examples/green-valley/school.json`: a sample CBSE school using every key below.

| Key | Example | Meaning |
| --- | --- | --- |
| `domain`, `data_dir`, `whatsapp`, `backup_copy_command` | `"erp.gv.in"`, `"/srv/lkms-data"`, `true` | Server settings (part 1 of the wizard) |
| `name`, `short_code`, `address`, `district`, `state`, `pincode`, `phone`, `email`, `website`, `udise_code`, `affiliation_number` | | The school |
| `board`, `board_name` | `"state"`, `"Rajasthan Board of Secondary Education (RBSE)"` | `board` is `cbse`, `icse`, `state` or `other` |
| `logo`, `brand_colour` | `"logo.png"`, `"#ad2972"` or `"green"` | Look |
| `map`, `facebook_url`, `instagram_url`, `youtube_url`, `x_url` | `"26.830321, 75.825578"`, `"https://facebook.com/myschool"` | Front page map and social links |
| `admission_number_prefix`, `admission_number_width`, `next_admission_number` | `"GV/"`, `5`, `1201` | Admission numbers |
| `age_cutoff`, `admissions_open` | `"31-03-2027"`, `true` | Age check date; take applications for next year |
| `classes`, `sections`, `capacity`, `age_limits` | `["Nursery", "KG", "Class 1"]`, `["A", "B"]`, `35`, `{"Nursery": [3, 4]}` | Classes |
| `subjects` | `["English", "Hindi", "Mathematics"]` | Subjects |
| `first_period`, `period_minutes`, `periods`, `break_after`, `break_minutes` | `"08:30"`, `35`, `7`, `4`, `25` | Bell times |
| `documents` | `[{"name": "Birth certificate", "required": true}]` | Admission documents |
| `grade_scale` | `"standard"` or `"eight-point"` | Grade scale |
| `upi_id`, `upi_name`, `upi_qr` | `"school@okaxis"`, `"Green Valley Trust"`, `"upi-qr.jpeg"` | UPI payments |
| `office_can_collect_fees`, `fee_reminder_days_before`, `fee_reminder_every_days` | `true`, `3`, `7` | Fee rules |
| `installments`, `due_day` | `4`, `10` | Fee plan: 1, 2, 4 or 12 installments |
| `fee.tuition`, `fee.admission`, `fee.annual`, `fee.exam` | `2500` or `{"Nursery": 1800, "Class 1": 2400}` | One amount for all classes, or class by class |
| `fee.extra` | `[{"name": "Transport fee", "every": true, "amount": 900}]` | Other fees |
| `admin.username`, `admin.first_name`, `admin.last_name`, `admin.phone` | | The administrator (password asked, never stored) |
| `staff` | `[{"name": "Suresh Gupta", "role": "principal", "phone": "9829000101"}]` | First staff logins; roles `principal`, `office`, `accountant`, `teacher` |

The file holds no passwords. Do not put it on GitHub if it contains a real school's phone numbers.

To fill in the school's details with no questions at all (for example when preparing a demo), use
`manage.py setup_school --answers school.json --accept-defaults` with the administrator's password in the
`LKMS_ADMIN_PASSWORD` environment variable. It stops and names the first answer the file is missing.

## 3. After setup

- Sign in as the administrator at `https://<address>/staff/login` and look over **School settings**.
- Link the school's WhatsApp phone (`DEPLOY.md` step 7) and check the backups (step 8).
- Give each staff member their username and temporary password.
- Go through the checklist at the end of `DEPLOY.md` before the school starts using it.
