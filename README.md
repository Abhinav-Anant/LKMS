# Lotus Kids Management System (LKMS)

School management system for Lotus Kids School, Rajasthan.

## Layout

- `backend/` – Django + Django REST Framework API
- `frontend/` – React + TypeScript + Vite UI: public admission form, tracking and fee payment; staff, teacher and parent portals
- `whatsapp-server/` – WhatsApp messaging service (server part of Blastup), wired in Phase 4
- `docs/LKMS_PLAN.md` – build plan and phase breakdown
- `docs/ADMISSIONS.md` – how the admission workflow and its API work
- `docs/FEES.md` – fee setup, invoices, receipts, UPI QR payments and how staff verify them
- `docs/PORTALS.md` – teacher, parent and admin portals: sign-in, attendance, marks, timetable, notices, users

## Running the backend locally (Windows, PowerShell)

Needs Python 3.12+, [uv](https://docs.astral.sh/uv/) and Docker Desktop.

```powershell
docker compose up -d                  # PostgreSQL on localhost:5432
cd backend
copy .env.example .env                # then edit if needed
uv sync
uv run python manage.py migrate
uv run python manage.py seed_lkms_defaults   # placeholder classes, sections, documents, fees, subjects, periods
uv run python manage.py createsuperuser
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
