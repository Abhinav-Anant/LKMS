import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { NativeSelect } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatDate, formatMoney, todayISO } from "@/lib/labels";
import type { DailyCollection, InvoiceListItem, Paginated, SchoolClass } from "@/lib/types";

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
                      <TableCell>{p.received_by ?? ""}</TableCell>
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
