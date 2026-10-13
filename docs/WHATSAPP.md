# WhatsApp alerts (Phase 4)

LKMS sends WhatsApp messages from the school's own WhatsApp number through the Blastup server in
`whatsapp-server/`. Blastup links to the number like WhatsApp Web (it scans a QR code once). This is not the
official WhatsApp Business API, so WhatsApp can block a number that sends too much. LKMS therefore sends slowly,
respects opt-outs and keeps a full send log.

## What is sent

| When | To | Message |
| --- | --- | --- |
| A parent asks for a sign-in code | that number | the 6-digit code (always sent, even to opted-out numbers, also at night) |
| Fee reminder (`send_fee_reminders`, daily) | the student's main contact | amount, due date, UPI payment link |
| Any payment recorded (cash, cheque, approved UPI) | main contact | amount and receipt number |
| Parent sends UPI details | main contact | "received, the school will check" |
| UPI details rejected | main contact | the reason |
| Admission application received / status changes | the contact on the application | status, message, tracking link |
| Child marked absent **today** | main contact | absence alert (once a day per child; back-dated corrections send nothing) |
| Notice posted with **Also send to parents on WhatsApp** ticked | one message per family in the chosen classes | the notice |

The wording of every message is in `backend/messaging/templates.py`.

## Safety limits

All in `backend/.env`:

| Setting | Default | Meaning |
| --- | --- | --- |
| `WHATSAPP_ENABLED` | `false` | Off: messages are logged as "Not sent" and nothing goes out. Messages from while it was off are never sent later. |
| `WHATSAPP_RATE_PER_MINUTE` | 8 | Most messages in any minute, with a random 4 to 8 second pause between messages |
| `WHATSAPP_DAILY_LIMIT_PER_NUMBER` | 6 | Most alerts to one parent number per day; the rest are marked "Not sent" |
| `WHATSAPP_QUIET_HOURS` | `21,7` | No alerts from 21:00 to 07:00 India time; they wait until morning. Sign-in codes still go. |
| `WHATSAPP_MAX_ATTEMPTS` | 5 | Retries after 1, 5, 15, 60 and 180 minutes, then "Failed" (staff can press Send again) |

If the WhatsApp server is down or the phone is unlinked, messages simply wait (no attempts are used up).
A sign-in code that cannot go out within 10 minutes is dropped; the office can still issue a code from the
student's page (**Parent sign-in code**), which works without WhatsApp.

Sign-in codes are hidden in the send log as soon as they are sent, fail, or expire.

Opt-outs: the office adds or removes numbers on the **WhatsApp** page, and parents can switch alerts off in the
parent portal (**My children** page).

Blastup's own "Safe Mode" should stay **off**: its sending window is in UTC (2:30 pm to 2:30 am India time) and LKMS
already applies the limits above.

## Setting it up on the server

1. `copy whatsapp-server\.env.example whatsapp-server\.env` and fill in the secrets and `ADMIN_PASSWORD`.
2. Start it: `docker compose up -d whatsapp` (starts MongoDB and Redis too; all ports are bound to 127.0.0.1 only).
3. Create the API key LKMS uses:
   `docker compose run --rm whatsapp node dist/scripts/lkms-api-key.js`
   and copy the printed `WHATSAPP_API_KEY=...` line into `backend/.env`. Set `WHATSAPP_ENABLED=true`.
4. Run the sender next to Django, as a service:
   `uv run python manage.py send_whatsapp --loop`
   (Without `--loop` it sends what is due once and exits, which also works from cron every minute.)
5. Sign in as principal, open **WhatsApp**, press **Link the school's phone**, and scan the QR code with the school's
   phone (WhatsApp > Settings > Linked devices > Link a device).
6. Keep the fee reminders running daily: `uv run python manage.py send_fee_reminders` from cron or Task Scheduler.

Use a dedicated school number that has been used normally for a while; brand-new numbers are blocked more easily.

## API

| Endpoint | Who |
| --- | --- |
| `GET /api/v1/whatsapp/status/` | admin, principal, office |
| `GET /api/v1/whatsapp/qr/`, `POST /api/v1/whatsapp/reconnect/` | admin, principal |
| `GET /api/v1/whatsapp/messages/` (+ `POST <id>/retry/`) | admin, principal, office |
| `/api/v1/whatsapp/opt-outs/` | admin, principal, office |
| `GET/PUT /api/v1/parent/whatsapp/` | the signed-in parent |
