# Fees and payments (Phase 2)

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
| See fees, reports, UPI reports, create pay links | ✓ | ✓ | ✓ | ✓ | |
| Record office payments, approve or reject UPI reports | ✓ | ✓ | ✓ | | |
| Fee setup, create/cancel invoices | ✓ | ✓ | ✓ | | |
| Ask for a concession | ✓ | ✓ | ✓ | ✓ | |
| Approve concessions, reverse payments | ✓ | ✓ | | | |

Change these in `backend/core/permissions.py` if the school works differently (e.g. if the office collects cash).

## Paying online: the school's UPI QR code

The school takes online fees only through its own UPI QR code
(Lotus Kids Education Society, UPI ID `8619190956@SBI`). There is no payment gateway, so LKMS cannot
see these payments by itself: the parent sends the payment receipt and the school checks it.

1. Staff open an invoice and click **Create link**, then send it to the parent (WhatsApp, SMS). The link
   (`/pay/<signed token>`) works without a login, shows only the child's first name, class and charges,
   and expires after `PAY_LINK_MAX_AGE_DAYS` (default 45).
2. **Step 1** on that page shows the balance, the school's QR code and UPI ID (with a button that opens the
   parent's UPI app on a phone). The parent pays from any UPI app.
3. **Step 2** asks the parent to send the payment receipt to the school: the UPI transaction ID (UTR), amount,
   date, and a screenshot or PDF of the receipt from their UPI app. Screenshots are checked to be real images or
   PDFs and stored privately, like admission documents.
4. The report waits in **Fees → UPI payments** (the tab shows how many are waiting). An accountant, the principal
   or an admin finds the payment in the school's bank statement, then either:
   - **approves** it (the amount can be corrected to what actually arrived), which records the payment and
     issues the school receipt, or
   - **rejects** it with a reason the parent sees on the pay page; the parent can then send it again.
5. Nothing is marked paid until staff approve. The same UTR cannot be sent twice unless the earlier one was
   rejected. Every report, screenshot view, approval and rejection is in the audit log.
6. After approval the parent can download the school receipt from the same link.

The QR image is `frontend/public/school-upi-qr.jpeg`. The UPI ID and payee name shown next to it come from
`SCHOOL_UPI_ID` and `SCHOOL_UPI_NAME` in `backend/.env`. If the school's account changes, update all three.

### Scheduled job (cron on the server)

```
0 9 * * *   cd /srv/lkms/backend && .venv/bin/python manage.py send_fee_reminders   # due in 3 days or overdue
```

Reminders include the pay link and go through the notification hook, which only logs until WhatsApp is added in Phase 4.

## Reports

- **Daily collection**: total and per payment mode for a day, with each receipt. Printable.
- **Overdue fees**: invoices past their due date with a balance, by class.

## Not done yet

- Real fee structure, concession rules and late fees: waiting for the school.
- Refunds: done outside LKMS, then reverse the payment here.
- Parent portal view of fees (Phase 3) and WhatsApp pay links, reminders and receipts (Phase 4).
