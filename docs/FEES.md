# Fees and online payments (Phase 2)

## How fees are set up

| Thing | What it is | Where |
|---|---|---|
| Fee head | A kind of charge: tuition, admission, annual, exam… A head can be marked *new students only* (e.g. admission fee). | Staff app → Fees → Fee setup |
| Installment | When fees fall due in a session, e.g. Quarter 1 due 10 April. | Fee setup |
| Fee amount | How much each class pays for each head in each installment (the fee structure grid). | Fee setup |
| Concession | A discount for one student in one session: a percentage, or a fixed rupee amount per installment, on one head or all fees. | Fees → Concessions |

`seed_lkms_defaults` loads **placeholder** heads, four quarterly installments and sample amounts
(`seed_fee_placeholders`). Replace them with the school's real structure before creating invoices.

## Invoices and receipts

- **Create invoices** (Fee setup) makes one invoice per student studying in the session, for one installment,
  from the grid plus approved concessions. Running it again only adds students who have no invoice yet.
  Once invoices exist, that installment's amounts are locked; cancel the invoices to change them.
- Invoice numbers (`INV-2026-27-00001`) and receipt numbers (`RCT-2026-27-00001`) run per session without gaps.
- **Office payments** (cash, cheque, bank transfer, UPI to the school's own account) are recorded on the invoice
  and give a PDF receipt straight away. Cheques and transfers need a reference number. An office payment cannot be
  more than the balance.
- **Reversing** a payment (bounced cheque, wrong entry) needs the principal or admin and a reason. Nothing is
  deleted; the receipt is marked reversed.
- **Concessions** are asked for by office staff and approved by the principal or admin. Approving one updates the
  student's open invoices for that session; it never reduces an invoice below what has already been paid.

## Who can do what

| | Admin | Principal | Accountant | Office | Teacher |
|---|---|---|---|---|---|
| See fees, reports, create pay links | ✓ | ✓ | ✓ | ✓ | |
| Record office payments | ✓ | ✓ | ✓ | | |
| Fee setup, create/cancel invoices | ✓ | ✓ | ✓ | | |
| Ask for a concession | ✓ | ✓ | ✓ | ✓ | |
| Approve concessions, reverse payments | ✓ | ✓ | | | |

Change these in `backend/core/permissions.py` if the school works differently (e.g. if the office collects cash).

## Online payments (Cashfree)

1. Staff open an invoice and click **Create link**. The link (`/pay/<signed token>`) works without a login, shows
   only the child's first name, class and charges, and expires after `PAY_LINK_MAX_AGE_DAYS` (default 45).
2. The parent clicks **Pay**. The server creates a Cashfree order for the current balance and the browser opens
   Cashfree's checkout (UPI, cards, net banking).
3. The invoice is marked paid **only** when:
   - Cashfree's webhook arrives with a valid signature (HMAC-SHA256 of timestamp + raw body with the secret key,
     Base64, compared in constant time), or
   - LKMS asks Cashfree for the order's payments itself (when the parent returns to the pay page, when staff click
     *Check with Cashfree*, or during reconciliation).

   The redirect back from Cashfree is never trusted on its own.
4. Each order is applied once, however many times the webhook is retried. If the amount paid differs from the order,
   the payment is **not** credited and appears under *Fees → Reports → Online payments to check*. A payment that
   arrives after the invoice was already paid at the office is recorded and flagged for a refund.
5. Every webhook call is stored as received (`WebhookEvent`, visible in Django admin), including rejected ones.

### Set-up

In `backend/.env`:

```
CASHFREE_ENV=sandbox            # production when the school's account is live
CASHFREE_CLIENT_ID=...          # Cashfree dashboard > Developers > API keys
CASHFREE_CLIENT_SECRET=...
FRONTEND_BASE_URL=https://fees.example.in      # where parents open pay links
PUBLIC_API_BASE_URL=https://fees.example.in    # where Cashfree can reach the API (https only)
```

In the Cashfree dashboard, add the webhook URL `<PUBLIC_API_BASE_URL>/api/v1/fees/cashfree/webhook/`
for payment events. LKMS also sends it as `notify_url` on each order when the URL is https.

### Scheduled jobs (cron on the server)

```
30 1 * * *  cd /srv/lkms/backend && .venv/bin/python manage.py reconcile_cashfree   # checks the last 3 days
0 9 * * *   cd /srv/lkms/backend && .venv/bin/python manage.py send_fee_reminders   # due in 3 days or overdue
```

Reminders go through the notification hook, which only logs until WhatsApp is added in Phase 4.

## Reports

- **Daily collection**: total and per payment mode for a day, with each receipt. Printable.
- **Overdue fees**: invoices past their due date with a balance, by class.

## Not done yet

- Real fee structure, concession rules and late fees: waiting for the school.
- Refunds through Cashfree (refund manually in the Cashfree dashboard, then reverse the payment in LKMS).
- Settlement reconciliation (matching Cashfree's bank settlements to receipts); order-level reconciliation is done.
- Parent portal view of fees (Phase 3) and WhatsApp reminders and receipts (Phase 4).
- Tested against a fake Cashfree in automated tests only; a sandbox run with the school's test keys is still needed.
