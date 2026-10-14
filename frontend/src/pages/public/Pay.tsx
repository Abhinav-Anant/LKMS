import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";

import { Field } from "@/components/Field";
import { ErrorNote } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, api, fetchFileUrl } from "@/lib/api";
import { formatDate, formatMoney, todayISO } from "@/lib/labels";
import { UPI_QR_URL } from "@/lib/school";
import type { PayPage, PublicInvoice } from "@/lib/types";

const base = (token: string) => `/fees/public/pay/${encodeURIComponent(token)}`;

export default function Pay() {
  const { token = "" } = useParams();
  const page = useQuery({ queryKey: ["pay", token], queryFn: () => api.get<PayPage>(`${base(token)}/`), retry: false });

  if (page.isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (page.isError || !page.data) {
    return (
      <div className="mx-auto max-w-lg space-y-3">
        <h1 className="text-2xl font-bold">Pay school fees</h1>
        <ErrorNote error={page.error ?? "This payment link could not be opened."} />
      </div>
    );
  }
  const data = page.data;
  const { invoice } = data;
  const toPay = Math.max(Number(invoice.balance) - Number(data.pending_amount), 0);
  const open = invoice.status === "unpaid" || invoice.status === "partly_paid";

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <h1 className="text-2xl font-bold">Pay school fees</h1>
      <InvoiceTable invoice={invoice} />
      {invoice.status === "paid" && <p role="status" className="rounded-md bg-emerald-50 p-3 text-emerald-900">This fee is fully paid. Thank you.</p>}
      {invoice.status === "cancelled" && <p className="rounded-md border p-3">This invoice has been cancelled. Please contact the school office.</p>}
      {Number(data.pending_amount) > 0 && (
        <p role="status" className="rounded-md bg-amber-50 p-3 text-amber-900">
          The school has your payment of {formatMoney(data.pending_amount)} and will check it in its bank account. You will get a receipt once it is confirmed. Please do not pay it again.
        </p>
      )}
      {open && toPay > 0 && <ScanAndPay data={data} amount={toPay} />}
      {open && <SendReceipt token={token} suggested={toPay > 0 ? String(toPay) : ""} />}
      <History token={token} data={data} />
    </div>
  );
}

function InvoiceTable({ invoice }: { invoice: PublicInvoice }) {
  return (
    <section className="space-y-3 rounded-lg border p-4" aria-label="Fee details">
      <p className="text-sm text-muted-foreground">
        {invoice.student_name} · {invoice.class_name} ({invoice.session_name}) · {invoice.installment_name} · due {formatDate(invoice.due_date)}
      </p>
      <table className="w-full text-sm">
        <tbody>
          {invoice.lines.map((l) => (
            <tr key={l.id}>
              <th scope="row" className="py-1 text-left font-normal">{l.fee_head_name}</th>
              <td className="py-1 text-right tabular-nums">{formatMoney(l.net)}{Number(l.concession) > 0 && <span className="block text-xs text-muted-foreground">after {formatMoney(l.concession)} concession</span>}</td>
            </tr>
          ))}
          {Number(invoice.amount_paid) > 0 && (
            <tr className="border-t"><th scope="row" className="py-1 text-left font-normal">Already paid</th><td className="py-1 text-right tabular-nums">− {formatMoney(invoice.amount_paid)}</td></tr>
          )}
          <tr className="border-t text-base font-semibold"><th scope="row" className="py-2 text-left">Balance</th><td className="py-2 text-right tabular-nums">{formatMoney(invoice.balance)}</td></tr>
        </tbody>
      </table>
      <p className="text-xs text-muted-foreground">Invoice {invoice.number}</p>
    </section>
  );
}

function ScanAndPay({ data, amount }: { data: PayPage; amount: number }) {
  const [copied, setCopied] = useState(false);
  const upiLink = `upi://pay?${new URLSearchParams({ pa: data.upi_id, pn: data.payee_name, am: amount.toFixed(2), cu: "INR", tn: `Fees ${data.invoice.number}` })}`;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(data.upi_id);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };
  return (
    <section className="space-y-3 rounded-lg border p-4" aria-labelledby="step-1">
      <h2 id="step-1" className="font-semibold">Step 1: Pay {formatMoney(amount)} by UPI</h2>
      <p className="text-sm">Scan this code with any UPI app (Google Pay, PhonePe, Paytm, BHIM or your bank's app).</p>
      <img src={UPI_QR_URL} alt={`UPI QR code for ${data.payee_name}, UPI ID ${data.upi_id}`} className="mx-auto w-full max-w-xs rounded-md border bg-white" />
      <dl className="grid grid-cols-[7rem_1fr] gap-x-2 gap-y-1 text-sm">
        <dt className="text-muted-foreground">Pay to</dt>
        <dd className="font-medium">{data.payee_name}</dd>
        <dt className="text-muted-foreground">UPI ID</dt>
        <dd className="flex flex-wrap items-center gap-2">
          <span className="font-mono font-medium">{data.upi_id}</span>
          <Button type="button" variant="outline" size="sm" className="h-7" onClick={copy}>{copied ? "Copied" : "Copy"}</Button>
        </dd>
        <dt className="text-muted-foreground">Amount</dt>
        <dd className="font-medium tabular-nums">{formatMoney(amount)}</dd>
      </dl>
      <p className="text-sm text-muted-foreground">
        On a phone you can also <a href={upiLink} className="text-primary underline">open your UPI app</a> with these details filled in.
        Check the name shows as {data.payee_name} before you pay.
      </p>
    </section>
  );
}

function SendReceipt({ token, suggested }: { token: string; suggested: string }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ utr: "", amount: suggested, paid_on: todayISO(), payer_name: "" });
  const [file, setFile] = useState<File | null>(null);
  const [sent, setSent] = useState(false);
  const send = useMutation({
    mutationFn: () => {
      const body = new FormData();
      Object.entries(form).forEach(([k, v]) => body.append(k, v));
      if (file) body.append("screenshot", file);
      return api.post<PayPage>(`${base(token)}/upi/`, body, { auth: false });
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["pay", token], data);
      setSent(true);
      setForm({ utr: "", amount: "", paid_on: todayISO(), payer_name: "" });
      setFile(null);
    },
  });
  const errors = send.error instanceof ApiError ? send.error.fieldErrors : {};
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setSent(false);
    send.mutate();
  };

  return (
    <section className="space-y-3 rounded-lg border p-4" aria-labelledby="step-2">
      <h2 id="step-2" className="font-semibold">Step 2: Send your payment receipt to the school</h2>
      <p className="text-sm">
        After paying, send the transaction ID and a screenshot of the payment receipt from your UPI app. The school office
        checks it in the bank account and then issues the school's fee receipt.
      </p>
      {sent && (
        <p role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-900">
          Thank you, the school has your receipt. Come back to this link to download the school's receipt once it is checked.
        </p>
      )}
      <form className="space-y-3" onSubmit={submit}>
        <Field label="UPI transaction ID (UTR)" required hint="Usually 12 digits. Find it in your UPI app under the payment details." error={errors.utr}>
          <Input value={form.utr} onChange={(e) => setForm({ ...form, utr: e.target.value.replace(/\s/g, "") })} inputMode="text" autoComplete="off" autoCorrect="off" spellCheck={false} maxLength={30} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Amount paid (₹)" required error={errors.amount}>
            <Input inputMode="decimal" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          </Field>
          <Field label="Date paid" required error={errors.paid_on}>
            <Input type="date" value={form.paid_on} max={todayISO()} onChange={(e) => setForm({ ...form, paid_on: e.target.value })} />
          </Field>
        </div>
        <Field label="Name of the person who paid" error={errors.payer_name}>
          <Input value={form.payer_name} onChange={(e) => setForm({ ...form, payer_name: e.target.value })} autoComplete="name" />
        </Field>
        <Field label="Screenshot of the payment receipt" required hint="Photo (JPG or PNG) or PDF, up to 5 MB." error={errors.screenshot}>
          <Input type="file" accept="image/jpeg,image/png,application/pdf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="h-auto py-2" />
        </Field>
        {send.error && !Object.keys(errors).length && <ErrorNote error={send.error} />}
        <Button type="submit" className="w-full" disabled={send.isPending || !file || !form.utr || !form.amount}>
          {send.isPending ? "Sending…" : "Send receipt to school"}
        </Button>
      </form>
    </section>
  );
}

function History({ token, data }: { token: string; data: PayPage }) {
  const download = useMutation({
    mutationFn: async (receipt: string) => {
      const url = await fetchFileUrl(`${base(token)}/receipts/${encodeURIComponent(receipt)}/`);
      const link = document.createElement("a");
      link.href = url;
      link.download = `receipt-${receipt}.pdf`;
      link.click();
    },
  });
  if (!data.submissions.length && !data.receipts.length) return null;
  return (
    <section className="space-y-3 rounded-lg border p-4" aria-labelledby="history">
      <h2 id="history" className="font-semibold">Your payments</h2>
      <ul className="divide-y text-sm">
        {data.receipts.map((r) => (
          <li key={r.receipt_number} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span>{formatMoney(r.amount)} on {formatDate(r.paid_on)} · receipt <span className="font-mono">{r.receipt_number}</span></span>
            <Button variant="outline" size="sm" onClick={() => download.mutate(r.receipt_number)} disabled={download.isPending}>Download receipt</Button>
          </li>
        ))}
        {data.submissions.filter((s) => s.status !== "approved").map((s) => (
          <li key={`${s.utr}-${s.submitted_at}`} className="py-2">
            <p>{formatMoney(s.amount)} · UTR <span className="font-mono">{s.utr}</span> · {s.status_label}</p>
            {s.reject_reason && <p className="text-destructive">{s.reject_reason}. Please check the details and send again, or contact the school office.</p>}
          </li>
        ))}
      </ul>
      <ErrorNote error={download.error} />
    </section>
  );
}
