# LKMS school management system

A ready-to-install school management system for Indian schools: online admissions, student records, fees by UPI QR
code, attendance, marks, report cards, transfer certificates, WhatsApp alerts to parents and nightly backups.

Each school gets its own installation (its own server or VPS, database and web address). A setup wizard asks every
question a new school needs, one at a time, and sets the server up: see `docs/NEW_SCHOOL.md`. Nothing is tied to
one school: the name, logo, colour, board, classes, fees and UPI account all come from the wizard and can be
changed later in **School settings**. `examples/` holds ready answers for Lotus Kids School (the first school) and
a sample CBSE school.

## Layout

- `backend/` – Django + Django REST Framework API
- `frontend/` – React + TypeScript + Vite UI: public admission form, tracking and fee payment; staff, teacher and parent portals
- `whatsapp-server/` – WhatsApp sender (server part of Blastup); Django talks to it on 127.0.0.1 with an API key
- `docs/LKMS_PLAN.md` – build plan and phase breakdown
- `docs/ADMISSIONS.md` – how the admission workflow and its API work
- `docs/FEES.md` – fee setup, invoices, receipts, UPI QR payments and how staff verify them
- `docs/PORTALS.md` – teacher, parent and admin portals: sign-in, attendance, marks, timetable, notices, users
- `docs/WHATSAPP.md` – WhatsApp alerts: what is sent, safety limits, opt-outs and server setup
- `docs/EXAMS.md` – exam terms, report cards, transfer certificates and school-wide reports
- `docs/DEPLOY.md` – step-by-step setup on a server (Ubuntu VPS, PostgreSQL, Nginx, HTTPS, WhatsApp, backups)
- `docs/NEW_SCHOOL.md` – setting LKMS up for a new school: what to collect from the school, the answers file, the wizard
- `deploy/setup_wizard.py` – asks for every setting and the school's details one question at a time, then sets up the server (`DEPLOY.md` step 6)
- `examples/` – answers files for the setup wizard (Lotus Kids School, and a sample CBSE school)
- `docs/BACKUPS.md` – nightly backups, retention, off-site copies and how to restore
- `docs/BOARD_CHECKS.md` – standard formats each school and its board should confirm (TC, report card, grades)

## Running the backend locally (Windows, PowerShell)

Needs Python 3.12+, [uv](https://docs.astral.sh/uv/) and Docker Desktop.

```powershell
docker compose up -d postgres         # PostgreSQL on localhost:5432
cd backend
copy .env.example .env                # then edit if needed
uv sync
uv run python manage.py migrate
uv run python manage.py setup_school --answers ../examples/lotus-kids/school.json   # the school's details, asked one by one
# or, for sample data without questions: uv run python manage.py seed_lkms_defaults, then createsuperuser
uv run python manage.py runserver
```

- API docs: http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/
- Tests: `uv run pytest`

Without Docker, leave `DATABASE_URL` empty in `.env` and SQLite is used (development only).
Tests read `backend/.env`, so copy `.env.example` first (it turns on `DJANGO_DEBUG`).

## Running the frontend locally

Needs Node.js 18+. Start the backend first; the dev server forwards `/api` to it.

```powershell
cd frontend
npm install
npm run dev          # http://localhost:8080
```

- Parents: `/apply` to fill in the admission form, `/track` to check status and upload documents, `/pay/...` links to pay fees by the school's UPI QR and send the receipt.
- Staff: `/staff/login` with a user created in the Django admin (set its role, e.g. office or principal).
- Checks: `npm run typecheck`, `npm run lint`, `npm run build`.

## Placeholders to replace with the school's real setup

`seed_lkms_defaults` creates sample data only: classes Nursery to Class 8 with section A,
sessions starting 1 April, age limits for Nursery/LKG/UKG, a sample document list, and sample
fee heads, quarterly installments and amounts (change them in Fees → Fee setup).
Change these in the admin once the school confirms its classes, sections, documents
and admission number format (School profile → admission number prefix, width and next number).

## Sources

- Base: [frankmathewsajan/acharya](https://github.com/frankmathewsajan/acharya) at commit `89409789dc3fd2fea8e378c632bed81f2cc40598`, used with the author's permission. Original README in `docs/ACHARYA_README.md`.
- WhatsApp server: [kalpintelligence/Blastup](https://github.com/kalpintelligence/Blastup) at commit `7a6df66cee12241f8d9f909392d37728942e84b2`, MIT licence (see `whatsapp-server/LICENSE`).
