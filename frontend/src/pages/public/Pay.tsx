import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { ErrorNote } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { api, fetchFileUrl } from "@/lib/api";
import { openCashfreeCheckout } from "@/lib/cashfree";
import { formatDate, formatMoney } from "@/lib/labels";
import type { OrderStatus, PublicInvoice } from "@/lib/types";

interface PayPage {
  invoice: PublicInvoice;
  online_payments_enabled: boolean;
  school_name: string;
}

interface OrderResult {
  status: OrderStatus;
  receipt_number: string | null;
  invoice: PublicInvoice;
}

const base = (token: string) => `/fees/public/pay/${encodeURIComponent(token)}`;

export default function Pay() {
  const { token = "" } = useParams();
  const [params] = useSearchParams();
  const orderId = params.get("order_id");
  const page = useQuery({ queryKey: ["pay", token], queryFn: () => api.get<PayPage>(`${base(token)}/`, undefined), retry: false });

  if (page.isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (page.isError || !page.data) {
    return (
      <div className="mx-auto max-w-lg space-y-3">
        <h1 className="text-2xl font-bold">Pay school fees</h1>
        <ErrorNote error={page.error ?? "This payment link could not be opened."} />
      </div>
    );
  }
  return (
    <div className="mx-auto max-w-lg space-y-6">
      <h1 className="text-2xl font-bold">Pay school fees</h1>
      {orderId ? <Result token={token} orderId={orderId} /> : <Summary token={token} data={page.data} />}
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
          <tr className="border-t text-base font-semibold"><th scope="row" className="py-2 text-left">To pay now</th><td className="py-2 text-right tabular-nums">{formatMoney(invoice.balance)}</td></tr>
        </tbody>
      </table>
      <p className="text-xs text-muted-foreground">Invoice {invoice.number}</p>
    </section>
  );
}

function Summary({ token, data }: { token: string; data: PayPage }) {
  const { invoice } = data;
  const start = useMutation({
    mutationFn: async () => {
      const order = await api.post<{ payment_session_id: string; mode: string }>(`${base(token)}/start/`, undefined, { auth: false });
      await openCashfreeCheckout(order.payment_session_id, order.mode);
    },
  });

  if (invoice.status === "paid") {
    return (
      <>
        <p role="status" className="rounded-md bg-emerald-50 p-3 text-emerald-900">This fee is fully paid. Thank you.</p>
        <InvoiceTable invoice={invoice} />
      </>
    );
  }
  if (invoice.status === "cancelled") return <p className="rounded-md border p-3">This invoice has been cancelled. Please contact the school office.</p>;

  return (
    <>
      <InvoiceTable invoice={invoice} />
      <ErrorNote error={start.error} />
      {data.online_payments_enabled ? (
        <>
          <Button size="lg" className="w-full" onClick={() => start.mutate()} disabled={start.isPending}>
            {start.isPending ? "Opening payment page…" : `Pay ${formatMoney(invoice.balance)}`}
          </Button>
          <p className="text-center text-sm text-muted-foreground">You can pay by UPI, debit or credit card, or net banking on Cashfree's secure page.</p>
        </>
      ) : (
        <p className="rounded-md border p-3 text-sm">Online payment is not switched on yet. Please pay at the school office.</p>
      )}
    </>
  );
}

function Result({ token, orderId }: { token: string; orderId: string }) {
  const [tries, setTries] = useState(0);
  const timer = useRef<number>();
  const result = useQuery({
    queryKey: ["pay-order", token, orderId, tries],
    queryFn: () => api.get<OrderResult>(`${base(token)}/orders/${encodeURIComponent(orderId)}/`),
    retry: false,
  });
  const waiting = result.data?.status === "created" && tries < 8;

  // Cashfree may tell us a moment after the parent is sent back, so check a few times.
  useEffect(() => {
    if (!waiting) return;
    timer.current = window.setTimeout(() => setTries((t) => t + 1), 3000);
    return () => window.clearTimeout(timer.current);
  }, [waiting, tries]);

  const download = useMutation({
    mutationFn: async (receipt: string) => {
      const url = await fetchFileUrl(`${base(token)}/receipts/${encodeURIComponent(receipt)}/`);
      const link = document.createElement("a");
      link.href = url;
      link.download = `receipt-${receipt}.pdf`;
      link.click();
    },
  });

  if (result.isError) return <ErrorNote error={result.error} />;
  if (!result.data || waiting) return <p role="status" className="text-muted-foreground">Checking your payment with the bank… please keep this page open.</p>;
  const { status, receipt_number, invoice } = result.data;

  return (
    <div className="space-y-4">
      {status === "paid" && (
        <div role="status" className="space-y-2 rounded-md bg-emerald-50 p-4 text-emerald-900">
          <p className="font-semibold">Payment received. Thank you.</p>
          {receipt_number && <p>Receipt number <span className="font-mono">{receipt_number}</span></p>}
          {receipt_number && <Button variant="outline" onClick={() => download.mutate(receipt_number)} disabled={download.isPending}>Download receipt</Button>}
        </div>
      )}
      {(status === "failed" || status === "expired") && (
        <div role="alert" className="space-y-2 rounded-md bg-red-50 p-4 text-red-900">
          <p className="font-semibold">The payment did not go through.</p>
          <p>No money was taken for this attempt. If money left your account, it is usually returned by the bank within a few days.</p>
        </div>
      )}
      {status === "created" && (
        <p role="status" className="rounded-md bg-amber-50 p-4 text-amber-900">
          We have not heard from the bank yet. If you completed the payment, it will show here and at the school once the bank confirms it. Please do not pay again for now.
        </p>
      )}
      {status === "mismatch" && <p role="alert" className="rounded-md bg-amber-50 p-4 text-amber-900">The school office will check this payment and contact you.</p>}
      <ErrorNote error={download.error} />
      <InvoiceTable invoice={invoice} />
      {(status === "failed" || status === "expired") && (
        <Button asChild className="w-full"><a href={`/pay/${encodeURIComponent(token)}`}>Try again</a></Button>
      )}
    </div>
  );
}
