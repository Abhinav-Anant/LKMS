# LKMS: base repo review and build plan

Reviewed 12 Oct 2026 from fresh clones of
`frankmathewsajan/acharya` (last commit 19 Sep 2025) and `kalpintelligence/Blastup` (last commit 17 Aug 2026).

## 1. What acharya is

- **Stack:** Django 5.2 + Django REST Framework + SimpleJWT (backend), React 18 + TypeScript + Vite + shadcn/ui + Tailwind + React Query (frontend). SQLite in dev, Postgres driver present. ReportLab (PDFs) already a dependency.
- **Built for:** a multi-school Rajasthan government admissions portal, modelled partly on a college: students have `course`, `department`, `semester`; fee structures are per course and semester; applicants pick up to 3 schools.
- **Extras we don't need:** `web3/` (blockchain marks), `hostel/`, `library/`, Gemini/Tesseract AI document extraction, the multi-school preference flow.
- **No LICENSE file.** By default that means the author keeps all rights. See question 2.

### Problems to fix before anything goes live

| Issue | Where |
|---|---|
| Hard-coded `SECRET_KEY`, `DEBUG = True`, `CORS_ALLOW_ALL_ORIGINS = True` | `backend/config/settings.py:28,31,108` |
| Dev database committed to git | `backend/db.sqlite3` |
| `.env` committed | `frontend/.env` |
| Fee "payment" trusts a `transaction_id` sent by the browser and marks the invoice paid | `backend/fees/views.py:183` (`pay`) |
| Parent is tied to a single student (FK), logs in by email OTP without a user account, so one parent cannot see several children | `backend/users/models.py` (`ParentProfile.student`) |
| Uploaded documents live under public `MEDIA_ROOT` | `settings.py:203` |

## 2. acharya against the five phases

| Phase | What exists | Gap |
|---|---|---|
| 1. Admissions and records | Rich application form (father, mother, guardian, category, previous school), email OTP, reference number, statuses pending / under review / approved / rejected, documents stored as JSON, admission number field on student | No academic session, class or section models; school-specific document list; private document storage with access checks; admission register; single-school workflow |
| 2. Fees and payments | `FeeStructure`, `FeeInvoice`, `Payment`; category-based fee idea | Fixed fee heads, no installments, concessions or approvals, no receipt PDFs, **no gateway at all**, no reminders |
| 3. Portals | Dashboards for student, parent, faculty, admin, warden; attendance (`ClassSession`, `AttendanceRecord`); notices | Attendance is lecture-style (course/subject/batch), not daily class attendance; multi-child parent accounts; teacher-to-class assignment; admin permissions screen |
| 4. WhatsApp | Nothing (in-app notices only) | All of it, via Blastup |
| 5. Academic admin | Basic `Exam` and `ExamResult` with grades; empty `reports` app | Report cards, promotion, timetable, homework, circulars, TC, fee/defaulter reports, audit log, backups |

**Verdict:** acharya saves us the project skeleton, auth, roles, the admission form and the React UI kit. The data model underneath (college-style, multi-school) needs reworking around Session → Class → Section → Enrollment. Treat it as a starting point to reshape, not a nearly-finished product.

## 3. What Blastup's WhatsApp part needs

- **Licence:** MIT. Fine to use; keep the copyright notice.
- **Stack:** Node 18+ / Express / TypeScript server, MongoDB, Redis (optional, falls back to memory), plus a Next.js dashboard. Docker Compose and PM2 configs included.
- **How it talks to WhatsApp:** `@whiskeysockets/baileys`, i.e. it logs in as WhatsApp Web by scanning a QR code. It is **not** the official WhatsApp Business API.
  - Free per message, but against WhatsApp's terms; the number can be banned, especially for bulk sends. Its "SafeMode" throttling reduces but does not remove this.
  - Needs a dedicated school phone number kept logged in.
- **What we'd take:** the `server/` only (send text/image/document, session + QR, reminders, API keys). Django calls `POST /api/send/text` with an `x-api-key` header. We can keep the Next.js dashboard just for scanning the QR, or add a QR page to LKMS admin.
- **Recommendation:** wrap it behind a small `messaging` module in Django with a queue, so switching to the official Meta Cloud API later (if bans become a problem) is one adapter, not a rewrite.

## 4. Payments

Changed 13 Oct 2026 at Abhinav's request: no payment gateway. Parents pay to the school's UPI QR code and send
the transaction ID and receipt screenshot; staff verify against the bank statement and issue the receipt.
See `docs/FEES.md`.

## 5. Proposed architecture (single VPS)

- Nginx + Let's Encrypt in front
- Django (Gunicorn) + PostgreSQL + Celery workers/beat on Redis (reminders, WhatsApp queue, reconciliation, backups)
- React frontend served as static files
- Blastup server + MongoDB, internal-only (not exposed publicly)
- Private document storage on disk outside the web root, served only through authenticated Django views
- Nightly `pg_dump` + documents archived off-server, with a monthly restore test
- Admin MFA (TOTP), audit log of who viewed or changed student data

## 6. Build order

0. **Set-up:** new LKMS repo from acharya, strip web3/hostel/library/AI/multi-school, move secrets to env, remove committed DB and `.env`, Postgres, Docker Compose for dev.
1. **Admissions and records:** Session/Class/Section/Enrollment models, school's document checklist, application → review → approve/reject → admission number + class + section, private documents.
2. **Fees:** fee heads, class-wise structures, installments, concessions with approval, invoices, UPI QR payments verified by staff, receipts, reminders.
3. **Portals:** proper parent accounts (phone OTP, many children), teacher class assignments, daily attendance, marks, notices, admin users/permissions.
4. **WhatsApp:** Blastup service + templates for fee due, payment received, admission status, absence, announcements, exams/holidays/PTM.
5. **Academic admin:** exams and report cards in the school's format, promotion, timetable, homework, circulars, TC, daily collection and defaulter reports, audit trail, backup and restore drill.

## 7. Questions for Abhinav

1. **Repository:** where should LKMS code live? (A new private GitHub repo I can create, or one you create and add to the project.)
2. **acharya licence:** it has no licence file. Are you or the school in touch with its author, or happy to get permission? Otherwise I'd use it as a reference and write LKMS fresh on the same stack.
3. **WhatsApp route:** OK to use Blastup (unofficial, free, ban risk) with a dedicated school number, keeping the official API as a fallback?
4. **School details:** classes offered (e.g. Nursery to 8?), sections, board (RBSE or CBSE), fee heads and installments, concessions, required admission documents, admission number format.
5. **Parent login:** phone OTP (via WhatsApp/SMS) or email OTP?
