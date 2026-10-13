# Admissions (Phase 1)

## Workflow

```
submitted ─┬─> under_review ─┬─> documents_requested ─┐
           │                 │                         │
           └─────────────────┴───────<─────────────────┘
   any open state ──> approved ──> admitted (student created)
   any open state ──> rejected / withdrawn
   approved ──> rejected / withdrawn
```

| Step | Who | Rule |
|---|---|---|
| Submit | Parent (no login) | Session must have admissions open, declaration and consent ticked, child's age fits the class on the cut-off date |
| Upload documents | Parent (access code) or office | PDF/JPG/PNG checked by file content, max 5 MB, re-upload replaces the old one |
| Verify / reject a document | Office, principal, admin | A rejection needs a note the parent will see |
| Under review / request documents | Office, principal, admin | Requesting documents needs a message for the parent |
| Approve | Principal, admin | Every required document must be verified |
| Reject | Principal, admin | Needs a message for the parent |
| Admit | Principal, admin | Picks a section of the applied class in the same session; checks capacity; assigns the next admission (S.R.) number; creates the student, links parents (siblings share parent records) and enrols them |

Every step is written to the application's history and to the audit log.

## Who sees what

- Parents track with application number + child's date of birth + a mobile number given on the form. They see status, the school's message and document status, nothing else.
- Documents and photos are stored outside the web folder with random names and are only served through logged-in API calls, each of which is audited.
- Aadhaar numbers are masked (`XXXX-XXXX-1234`) except for the principal and admin.
- Teachers and accountants cannot see applications or student records yet; their access arrives with their portals in Phases 2 and 3.

## API

Public (no login, rate-limited):

- `GET  /api/v1/academics/admission-options/` – open session(s) and classes
- `GET  /api/v1/admissions/public/document-types/?class=<id>`
- `POST /api/v1/admissions/public/apply/` → `application_number`, `access_token`
- `POST /api/v1/admissions/public/<application_number>/documents/` (multipart, header `X-Application-Token`)
- `POST /api/v1/admissions/public/track/` `{application_number, date_of_birth, phone}`

Staff (JWT from `POST /api/v1/auth/login/`):

- `GET/PATCH /api/v1/admissions/applications/` (filters: `status`, `session`, `class_applied`, `search`)
- `POST /api/v1/admissions/applications/<id>/transition/` `{status, message}`
- `POST /api/v1/admissions/applications/<id>/approve/`
- `POST /api/v1/admissions/applications/<id>/admit/` `{section, admission_date?, roll_number?}`
- `POST /api/v1/admissions/applications/<id>/documents/` (office upload for walk-ins)
- `GET  /api/v1/admissions/documents/<id>/file/`, `POST /api/v1/admissions/documents/<id>/verify/`
- `GET/PATCH /api/v1/students/`, `GET /api/v1/students/<id>/photo/`

Full, always-current reference: `/api/docs/` on a running server.

## Screens

| Path | Who | What |
|---|---|---|
| `/apply` | Parents | Admission form in steps, then document upload |
| `/track` | Parents | Status by application number, date of birth and mobile; upload missing documents with the access code |
| `/staff/applications` | Office, principal | Filter and open applications |
| `/staff/applications/:id` | Office, principal | Verify documents, move status, approve or reject, admit into a section |
| `/staff/students`, `/staff/students/:id` | Staff with student access | Student list and record with photo, guardians and class history |

The public form has a hidden `website` field; the API refuses any submission that fills it in (spam bots).

## Not done yet

- Parent OTP on the mobile number before submitting (needs the WhatsApp/SMS sender from Phase 4).
- Printable admission register and admission form PDF.
- MFA for administrators.
