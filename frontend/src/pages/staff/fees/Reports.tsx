import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { NativeSelect } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, formatDateTime, formatMoney, todayISO } from "@/lib/labels";
import type { DailyCollection, InvoiceListItem, Paginated, PaymentIssue, SchoolClass } from "@/lib/types";

import { FeesNav } from "./FeesNav";

export default function Reports() {
  const [params, setParams] = useSearchParams();
  const day = params.get("date") ?? todayISO();
  const schoolClass = params.get("school_class") ?? "";
  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Fees</h1>
      <FeesNav />
      <Issues />
      <Daily day={day} onDay={(v) => set("date", v)} />
      <Defaulters schoolClass={schoolClass} onClass={(v) => set("school_class", v)} />
    </div>
  );
}

function Daily({ day, onDay }: { day: string; onDay: (v: string) => void }) {
  const report = useQuery({ queryKey: ["daily-collection", day], queryFn: () => api.get<DailyCollection>("/fees/reports/daily-collection/", { date: day }) });
  const data = report.data;
  return (
    <Panel
      title="Daily collection"
      actions={<Input type="date" value={day} max={todayISO()} onChange={(e) => onDay(e.target.value)} className="h-9 w-44" aria-label="Date" />}
    >
      <ErrorNote error={report.error} />
      {data && (
        <>
          <div className="flex flex-wrap gap-6 text-sm">
            <p><span className="text-muted-foreground">Total </span><span className="text-lg font-semibold tabular-nums">{formatMoney(data.total)}</span></p>
            {data.by_mode.map((m) => <p key={m.mode}><span className="text-muted-foreground">{m.label} </span><span className="tabular-nums">{formatMoney(m.total)} ({m.count})</span></p>)}
          </div>
          {data.payments.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Receipt</TableHead>
                    <TableHead scope="col">Student</TableHead>
                    <TableHead scope="col">Mode</TableHead>
                    <TableHead scope="col">Taken by</TableHead>
                    <TableHead scope="col" className="text-right">Amount</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.payments.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell><Link to={`/staff/fees/invoices/${p.invoice}`} className="font-mono text-primary underline-offset-4 hover:underline">{p.receipt_number}</Link></TableCell>
                      <TableCell>{p.student_name} <span className="text-muted-foreground">({p.admission_number})</span></TableCell>
                      <TableCell>{p.mode_label}{p.reference && ` · ${p.reference}`}</TableCell>
                      <TableCell>{p.received_by ?? "Online"}</TableCell>
                      <TableCell className="text-right tabular-nums">{formatMoney(p.amount)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No payments on {formatDate(day)}.</p>
          )}
          {data.payments.length > 0 && <Button variant="outline" size="sm" onClick={() => window.print()}>Print</Button>}
        </>
      )}
    </Panel>
  );
}

function Defaulters({ schoolClass, onClass }: { schoolClass: string; onClass: (v: string) => void }) {
  const classes = useQuery({ queryKey: ["classes"], queryFn: () => api.get<Paginated<SchoolClass>>("/academics/classes/") });
  const report = useQuery({ queryKey: ["defaulters", schoolClass], queryFn: () => api.get<InvoiceListItem[]>("/fees/reports/defaulters/", { school_class: schoolClass }) });
  const total = (report.data ?? []).reduce((sum, i) => sum + Number(i.balance), 0);
  return (
    <Panel
      title="Overdue fees"
      actions={
        <NativeSelect aria-label="Class" value={schoolClass} onChange={(e) => onClass(e.target.value)} className="h-9 w-44">
          <option value="">All classes</option>
          {classes.data?.results.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </NativeSelect>
      }
    >
      <ErrorNote error={report.error} />
      {report.data && (
        report.data.length === 0 ? (
          <p className="text-sm text-muted-foreground">No overdue fees.</p>
        ) : (
          <>
            <p className="text-sm">{report.data.length} invoices, {formatMoney(total)} outstanding.</p>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Student</TableHead>
                    <TableHead scope="col">Class</TableHead>
                    <TableHead scope="col">Installment</TableHead>
                    <TableHead scope="col">Due</TableHead>
                    <TableHead scope="col" className="text-right">Balance</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.data.map((i) => (
                    <TableRow key={i.id}>
                      <TableCell><Link to={`/staff/fees/invoices/${i.id}`} className="text-primary underline-offset-4 hover:underline">{i.student_name}</Link> <span className="text-muted-foreground">({i.admission_number})</span></TableCell>
                      <TableCell>{i.class_name}</TableCell>
                      <TableCell>{i.installment_name}</TableCell>
                      <TableCell>{formatDate(i.due_date)}</TableCell>
                      <TableCell className="text-right tabular-nums">{formatMoney(i.balance)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </>
        )
      )}
    </Panel>
  );
}

function Issues() {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const issues = useQuery({ queryKey: ["payment-issues"], queryFn: () => api.get<Paginated<PaymentIssue>>("/fees/issues/", { resolved: "false" }) });
  const resolve = useMutation({
    mutationFn: (id: number) => api.patch(`/fees/issues/${id}/`, { resolved: true, resolved_note: "Checked" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["payment-issues"] }),
  });
  if (!issues.data?.results.length) return null;
  return (
    <Panel title="Online payments to check" className="border-amber-300">
      <ul className="divide-y text-sm">
        {issues.data.results.map((i) => (
          <li key={i.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <div>
              <p className="font-medium">{i.kind_label}</p>
              <p className="text-muted-foreground">{i.detail} · {formatDateTime(i.created_at)}{i.order_id && <> · <span className="font-mono">{i.order_id}</span></>}</p>
            </div>
            <div className="flex gap-2">
              {i.invoice && <Button asChild variant="outline" size="sm"><Link to={`/staff/fees/invoices/${i.invoice}`}>Open invoice</Link></Button>}
              {can("fees.approve") && <Button variant="ghost" size="sm" onClick={() => resolve.mutate(i.id)}>Mark checked</Button>}
            </div>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
