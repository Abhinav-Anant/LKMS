import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Field } from "@/components/Field";
import { ErrorNote } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { UPI_STATUS_LABELS, formatDate, formatDateTime, formatMoney } from "@/lib/labels";
import type { UpiSubmission } from "@/lib/types";

import { openPdf } from "./receipt";

/** One UPI payment a parent reported, with the staff check (approve or reject). */
export function UpiCard({ submission: s, showStudent = false }: { submission: UpiSubmission; showStudent?: boolean }) {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"idle" | "approve" | "reject">("idle");
  const [amount, setAmount] = useState(s.amount);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<unknown>(null);
  const done = () => {
    setMode("idle");
    setError(null);
    void queryClient.invalidateQueries({ queryKey: ["upi-submissions"] });
    void queryClient.invalidateQueries({ queryKey: ["invoice"] });
    void queryClient.invalidateQueries({ queryKey: ["invoices"] });
  };
  const approve = useMutation({ mutationFn: () => api.post(`/fees/upi-submissions/${s.id}/approve/`, { amount }), onSuccess: done, onError: setError });
  const reject = useMutation({ mutationFn: () => api.post(`/fees/upi-submissions/${s.id}/reject/`, { reason }), onSuccess: done, onError: setError });
  const pending = s.status === "pending";

  return (
    <li className="space-y-2 rounded-lg border bg-background p-4 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-base font-semibold tabular-nums">
          {formatMoney(s.amount)} <span className="font-mono text-sm font-normal">UTR {s.utr}</span>
        </p>
        <span className={pending ? "font-medium text-amber-800" : s.status === "rejected" ? "text-destructive" : "text-emerald-700"}>{UPI_STATUS_LABELS[s.status]}</span>
      </div>
      {showStudent && (
        <p>
          <Link to={`/staff/fees/invoices/${s.invoice}`} className="font-medium text-primary underline-offset-4 hover:underline">{s.student_name}</Link>{" "}
          <span className="text-muted-foreground">({s.admission_number}, {s.class_name}) · invoice {s.invoice_number} · balance {formatMoney(s.invoice_balance)}</span>
        </p>
      )}
      <p className="text-muted-foreground">
        Paid on {formatDate(s.paid_on)}{s.payer_name && ` by ${s.payer_name}`} · sent {formatDateTime(s.submitted_at)}
        {s.reviewed_by && ` · checked by ${s.reviewed_by} on ${formatDateTime(s.reviewed_at)}`}
      </p>
      {s.reject_reason && <p className="text-destructive">Reason: {s.reject_reason}</p>}
      <ErrorNote error={error} />
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" onClick={() => openPdf(`/fees/upi-submissions/${s.id}/screenshot/`).catch(setError)}>View parent's receipt</Button>
        {s.payment_id && <Button variant="outline" size="sm" onClick={() => openPdf(`/fees/payments/${s.payment_id}/receipt/`).catch(setError)}>School receipt {s.receipt_number}</Button>}
        {pending && can("fees.collect") && mode === "idle" && (
          <>
            <Button size="sm" onClick={() => setMode("approve")}>Found in bank, approve</Button>
            <Button size="sm" variant="ghost" onClick={() => setMode("reject")}>Reject</Button>
          </>
        )}
      </div>
      {mode === "approve" && (
        <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); approve.mutate(); }}>
          <Field label="Amount received in bank (₹)" required className="w-56">
            <Input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </Field>
          <Button type="submit" size="sm" disabled={approve.isPending}>Approve and issue receipt</Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => setMode("idle")}>Back</Button>
        </form>
      )}
      {mode === "reject" && (
        <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); reject.mutate(); }}>
          <Field label="Reason the parent will see" required className="min-w-64 flex-1">
            <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. No payment with this UTR in the bank statement" />
          </Field>
          <Button type="submit" size="sm" variant="destructive" disabled={!reason || reject.isPending}>Reject</Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => setMode("idle")}>Back</Button>
        </form>
      )}
    </li>
  );
}
