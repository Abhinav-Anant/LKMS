import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { Field, NativeSelect } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { InvoiceBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PAYMENT_MODES, formatDate, formatDateTime, formatMoney, todayISO } from "@/lib/labels";
import type { FeePayment, InvoiceDetail as Detail } from "@/lib/types";

import { FeesNav } from "./FeesNav";
import { openPdf } from "./receipt";
import { UpiCard } from "./UpiCard";

export default function InvoiceDetail() {
  const { id } = useParams();
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState<unknown>(null);
  const query = useQuery({ queryKey: ["invoice", id], queryFn: () => api.get<Detail>(`/fees/invoices/${id}/`) });
  const refresh = () => {
    setError(null);
    void queryClient.invalidateQueries({ queryKey: ["invoice", id] });
    void queryClient.invalidateQueries({ queryKey: ["invoices"] });
  };

  if (query.isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (query.isError || !query.data) return <ErrorNote error={query.error ?? "This invoice could not be loaded."} />;
  const inv = query.data;
  const open = inv.status === "unpaid" || inv.status === "partly_paid";

  return (
    <div className="space-y-4">
      <h1 className="sr-only">Invoice {inv.number}</h1>
      <FeesNav />
      <div>
        <Link to="/staff/fees" className="text-sm text-muted-foreground underline-offset-4 hover:underline">← All invoices</Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h2 className="text-2xl font-bold">{inv.student_name}</h2>
          <InvoiceBadge status={inv.status} overdue={inv.due_date < todayISO()} />
        </div>
        <p className="text-sm text-muted-foreground">
          <span className="font-mono">{inv.number}</span> · {inv.installment_name} · {inv.class_name} ({inv.session_name}) · due {formatDate(inv.due_date)} ·{" "}
          <Link to={`/staff/students/${inv.student}`} className="underline">{inv.admission_number}</Link>
        </p>
        {inv.cancel_reason && <p className="mt-1 text-sm">Cancelled: {inv.cancel_reason}</p>}
      </div>
      <ErrorNote error={error} />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Panel title="Charges">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Fee head</TableHead>
                  <TableHead scope="col" className="text-right">Amount</TableHead>
                  <TableHead scope="col" className="text-right">Concession</TableHead>
                  <TableHead scope="col" className="text-right">To pay</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {inv.lines.map((l) => (
                  <TableRow key={l.id}>
                    <TableCell>{l.fee_head_name}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatMoney(l.amount)}</TableCell>
                    <TableCell className="text-right tabular-nums">{Number(l.concession) ? `− ${formatMoney(l.concession)}` : ""}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatMoney(l.net)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
              <TableFooter>
                <TableRow>
                  <TableCell>Total</TableCell>
                  <TableCell className="text-right tabular-nums">{formatMoney(inv.gross_amount)}</TableCell>
                  <TableCell className="text-right tabular-nums">{Number(inv.concession_amount) ? `− ${formatMoney(inv.concession_amount)}` : ""}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatMoney(inv.net_amount)}</TableCell>
                </TableRow>
              </TableFooter>
            </Table>
            <dl className="grid grid-cols-2 gap-2 text-sm sm:w-72 sm:justify-self-end">
              <dt className="text-muted-foreground">Paid</dt><dd className="text-right tabular-nums">{formatMoney(inv.amount_paid)}</dd>
              <dt className="font-semibold">Balance</dt><dd className="text-right font-semibold tabular-nums">{formatMoney(inv.balance)}</dd>
            </dl>
          </Panel>

          <Panel title="Payments">
            {inv.payments.length === 0 ? (
              <p className="text-sm text-muted-foreground">No payments yet.</p>
            ) : (
              <ul className="divide-y">
                {inv.payments.map((p) => (
                  <PaymentRow key={p.id} payment={p} canReverse={can("fees.approve")} onDone={refresh} onError={setError} />
                ))}
              </ul>
            )}
          </Panel>

          {inv.upi_submissions.length > 0 && (
            <Panel title="UPI payments sent by the parent">
              <ul className="space-y-3">
                {inv.upi_submissions.map((u) => <UpiCard key={u.id} submission={u} />)}
              </ul>
            </Panel>
          )}
        </div>

        <aside className="space-y-6">
          {open && can("fees.collect") && <RecordPayment invoice={inv} onDone={refresh} onError={setError} />}
          {open && <PayLink invoiceId={inv.id} onError={setError} />}
          {inv.status !== "cancelled" && Number(inv.amount_paid) === 0 && can("fees.manage") && (
            <CancelInvoice invoiceId={inv.id} onDone={refresh} onError={setError} />
          )}
        </aside>
      </div>
    </div>
  );
}

function PaymentRow({ payment: p, canReverse, onDone, onError }: { payment: FeePayment; canReverse: boolean; onDone: () => void; onError: (e: unknown) => void }) {
  const [reason, setReason] = useState("");
  const [asking, setAsking] = useState(false);
  const reverse = useMutation({
    mutationFn: () => api.post(`/fees/payments/${p.id}/reverse/`, { reason }),
    onSuccess: onDone,
    onError,
  });
  const reversed = p.status === "reversed";
  return (
    <li className="space-y-2 py-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className={reversed ? "line-through" : "font-medium"}>
            {formatMoney(p.amount)} · {p.mode_label}{p.reference && ` (${p.reference})`}
          </p>
          <p className="text-muted-foreground">
            Receipt <span className="font-mono">{p.receipt_number}</span> · {formatDate(p.paid_on)}{p.received_by ? ` · ${p.received_by}` : ""}
          </p>
          {reversed && <p className="text-destructive">Reversed {formatDateTime(p.reversed_at)}: {p.reversal_reason}</p>}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => openPdf(`/fees/payments/${p.id}/receipt/`).catch(onError)}>Receipt</Button>
          {canReverse && !reversed && !asking && <Button variant="ghost" size="sm" onClick={() => setAsking(true)}>Reverse</Button>}
        </div>
      </div>
      {asking && (
        <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); reverse.mutate(); }}>
          <Field label="Why is this payment being reversed?" required className="min-w-64 flex-1">
            <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Cheque bounced" />
          </Field>
          <Button type="submit" variant="destructive" size="sm" disabled={!reason || reverse.isPending}>Reverse payment</Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => setAsking(false)}>Keep</Button>
        </form>
      )}
    </li>
  );
}

function RecordPayment({ invoice, onDone, onError }: { invoice: Detail; onDone: () => void; onError: (e: unknown) => void }) {
  const [form, setForm] = useState({ amount: invoice.balance, mode: "cash", reference: "", paid_on: todayISO() });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [lastReceipt, setLastReceipt] = useState<FeePayment | null>(null);
  const save = useMutation({
    mutationFn: () => api.post<FeePayment>(`/fees/invoices/${invoice.id}/pay/`, form),
    onSuccess: (payment) => {
      setFieldErrors({});
      setLastReceipt(payment);
      onDone();
    },
    onError: (err) => {
      if (err instanceof ApiError) setFieldErrors(err.fieldErrors);
      onError(err);
    },
  });
  // After a payment the balance changes; offer the new balance as the next amount.
  useEffect(() => setForm((f) => ({ ...f, amount: invoice.balance, reference: "" })), [invoice.balance]);
  const needsRef = form.mode !== "cash";
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };

  return (
    <Panel title="Record a payment">
      {lastReceipt && (
        <p className="rounded-md bg-emerald-50 p-2 text-sm text-emerald-900" role="status">
          Saved receipt <span className="font-mono">{lastReceipt.receipt_number}</span>.{" "}
          <button type="button" className="underline" onClick={() => openPdf(`/fees/payments/${lastReceipt.id}/receipt/`).catch(onError)}>Print receipt</button>
        </p>
      )}
      <form className="space-y-3" onSubmit={submit}>
        <Field label="Amount (₹)" required error={fieldErrors.amount}>
          <Input inputMode="decimal" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
        </Field>
        <Field label="Paid by" required error={fieldErrors.mode}>
          <NativeSelect value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })}>
            {PAYMENT_MODES.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
          </NativeSelect>
        </Field>
        {needsRef && (
          <Field label={form.mode === "cheque" ? "Cheque number" : "Transaction reference (UTR)"} required error={fieldErrors.reference}>
            <Input value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} autoCorrect="off" spellCheck={false} />
          </Field>
        )}
        <Field label="Date received" required error={fieldErrors.paid_on}>
          <Input type="date" value={form.paid_on} max={todayISO()} onChange={(e) => setForm({ ...form, paid_on: e.target.value })} />
        </Field>
        <Button type="submit" className="w-full" disabled={save.isPending}>{save.isPending ? "Saving…" : "Save and issue receipt"}</Button>
      </form>
    </Panel>
  );
}

function PayLink({ invoiceId, onError }: { invoiceId: number; onError: (e: unknown) => void }) {
  const [url, setUrl] = useState("");
  const [copied, setCopied] = useState(false);
  const make = useMutation({
    mutationFn: () => api.post<{ url: string }>(`/fees/invoices/${invoiceId}/pay-link/`),
    onSuccess: (data) => setUrl(data.url),
    onError,
  });
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };
  return (
    <Panel title="Online payment link">
      <p className="text-sm text-muted-foreground">Send this to the parent. It shows the fees, the school UPI QR code, and a form to send the payment receipt. No sign-in needed.</p>
      {url ? (
        <div className="space-y-2">
          <Input readOnly value={url} onFocus={(e) => e.currentTarget.select()} aria-label="Payment link" />
          <Button variant="outline" size="sm" onClick={copy}>{copied ? "Copied" : "Copy link"}</Button>
        </div>
      ) : (
        <Button variant="outline" onClick={() => make.mutate()} disabled={make.isPending}>Create link</Button>
      )}
    </Panel>
  );
}

function CancelInvoice({ invoiceId, onDone, onError }: { invoiceId: number; onDone: () => void; onError: (e: unknown) => void }) {
  const [reason, setReason] = useState("");
  const [asking, setAsking] = useState(false);
  const cancel = useMutation({ mutationFn: () => api.post(`/fees/invoices/${invoiceId}/cancel/`, { reason }), onSuccess: onDone, onError });
  if (!asking) return <Button variant="ghost" className="text-destructive" onClick={() => setAsking(true)}>Cancel this invoice</Button>;
  return (
    <Panel title="Cancel invoice">
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); cancel.mutate(); }}>
        <Field label="Reason" required>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Student left before the session" />
        </Field>
        <div className="flex gap-2">
          <Button type="submit" variant="destructive" disabled={!reason || cancel.isPending}>Cancel invoice</Button>
          <Button type="button" variant="ghost" onClick={() => setAsking(false)}>Keep it</Button>
        </div>
      </form>
    </Panel>
  );
}
