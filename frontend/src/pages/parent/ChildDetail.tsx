import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { ErrorNote, Panel } from "@/components/Panel";
import { TimetableGrid } from "@/components/TimetableGrid";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { useChildren } from "@/lib/parent";
import { ATTENDANCE_LABELS, formatDate, formatMoney, todayISO } from "@/lib/labels";
import type { ChildAttendance, ChildFees, ChildMark, ParentReportCard, TimetableEntry } from "@/lib/types";
import { cn } from "@/lib/utils";
import { openPdf } from "@/pages/staff/fees/receipt";

const TABS = [
  ["attendance", "Attendance"],
  ["fees", "Fees"],
  ["marks", "Marks"],
  ["report-cards", "Report cards"],
  ["timetable", "Timetable"],
] as const;

export default function ChildDetail() {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "attendance";
  const children = useChildren();
  const child = children.data?.find((c) => String(c.id) === id);

  return (
    <div className="space-y-4">
      <Link to="/parent" className="text-sm text-primary underline-offset-4 hover:underline">← My children</Link>
      {child && (
        <div>
          <h1 className="text-2xl font-bold">{child.full_name}</h1>
          <p className="text-sm text-muted-foreground">
            {child.class_label ?? "Class not assigned"}{child.roll_number ? ` · Roll ${child.roll_number}` : ""} · Adm. no. {child.admission_number}
          </p>
        </div>
      )}
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Sections">
        {TABS.map(([value, label]) => (
          <Button key={value} role="tab" aria-selected={tab === value} size="sm" variant={tab === value ? "default" : "outline"}
            onClick={() => setParams({ tab: value }, { replace: true })}>
            {label}
          </Button>
        ))}
      </div>
      {tab === "attendance" && <AttendanceTab id={id!} />}
      {tab === "fees" && <FeesTab id={id!} />}
      {tab === "marks" && <MarksTab id={id!} />}
      {tab === "report-cards" && <ReportCardsTab id={id!} />}
      {tab === "timetable" && <TimetableTab id={id!} />}
    </div>
  );
}

const DAY_STYLE: Record<string, string> = {
  present: "bg-green-100 text-green-900",
  late: "bg-amber-100 text-amber-900",
  absent: "bg-red-100 text-red-900",
  leave: "bg-slate-200 text-slate-900",
};

function AttendanceTab({ id }: { id: string }) {
  const [month, setMonth] = useState(todayISO().slice(0, 7));
  const data = useQuery({
    queryKey: ["parent-attendance", id, month],
    queryFn: () => api.get<ChildAttendance>(`/parent/children/${id}/attendance/`, { month }),
  });
  const d = data.data;
  return (
    <Panel title="Attendance" actions={<Input type="month" aria-label="Month" value={month} max={todayISO().slice(0, 7)} onChange={(e) => e.target.value && setMonth(e.target.value)} className="w-44" />}>
      <ErrorNote error={data.error} />
      {d && (
        <>
          <p className="text-sm">
            <span className="text-2xl font-bold">{d.percentage === null ? "–" : `${d.percentage}%`}</span>{" "}
            <span className="text-muted-foreground">
              present {d.present} · late {d.late} · absent {d.absent} · leave {d.leave}
            </span>
          </p>
          {d.days.length === 0 ? (
            <p className="text-sm text-muted-foreground">No attendance has been marked this month.</p>
          ) : (
            <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">
              {d.days.map((day) => (
                <li key={day.date} className={cn("rounded-md p-2 text-sm", DAY_STYLE[day.status])}>
                  <span className="block font-medium">{formatDate(day.date)}</span>
                  {ATTENDANCE_LABELS[day.status]}
                  {day.note && <span className="block text-xs">{day.note}</span>}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Panel>
  );
}

function FeesTab({ id }: { id: string }) {
  const data = useQuery({ queryKey: ["parent-fees", id], queryFn: () => api.get<ChildFees>(`/parent/children/${id}/fees/`) });
  const d = data.data;
  return (
    <div className="space-y-4">
      <ErrorNote error={data.error} />
      {d && (
        <>
          <Panel title="Fees">
            <p className="text-sm">
              Total due now: <span className="text-xl font-bold">{formatMoney(d.total_due)}</span>
            </p>
            <p className="text-sm text-muted-foreground">
              Pay by scanning the school's UPI QR code on the payment page, then send the transaction ID there. The school checks
              it and issues a receipt. You can also pay at the school office.
            </p>
            <ul className="divide-y">
              {d.invoices.map((inv) => (
                <li key={inv.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                  <span>
                    <span className="font-medium">{inv.installment_name || inv.number}</span>
                    <span className="block text-sm text-muted-foreground">
                      Due {formatDate(inv.due_date)} · {formatMoney(inv.net_amount)} · paid {formatMoney(inv.amount_paid)}
                    </span>
                  </span>
                  <span className="flex items-center gap-2">
                    <Badge variant={inv.status === "paid" ? "default" : "outline"}>{inv.status_label}</Badge>
                    {inv.pay_link && (
                      <Button asChild size="sm">
                        <a href={inv.pay_link}>Pay {formatMoney(inv.balance)}</a>
                      </Button>
                    )}
                  </span>
                </li>
              ))}
              {d.invoices.length === 0 && <li className="py-3 text-sm text-muted-foreground">No fee bills yet.</li>}
            </ul>
          </Panel>
          <Panel title="Receipts">
            <ul className="divide-y">
              {d.payments.map((p) => (
                <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <span className="text-sm">
                    <span className="font-medium">{p.receipt_number}</span> · {formatDate(p.paid_on)} · {formatMoney(p.amount)} · {p.mode_label}
                  </span>
                  <Button variant="outline" size="sm"
                    onClick={() => openPdf(`/parent/children/${id}/receipts/${p.id}/`).catch(() => toast({ title: "Could not open the receipt", variant: "destructive" }))}>
                    Download receipt
                  </Button>
                </li>
              ))}
              {d.payments.length === 0 && <li className="py-2 text-sm text-muted-foreground">No payments yet.</li>}
            </ul>
          </Panel>
        </>
      )}
    </div>
  );
}

function MarksTab({ id }: { id: string }) {
  const data = useQuery({ queryKey: ["parent-marks", id], queryFn: () => api.get<ChildMark[]>(`/parent/children/${id}/marks/`) });
  const groups = new Map<string, ChildMark[]>();
  for (const m of data.data ?? []) groups.set(m.name, [...(groups.get(m.name) ?? []), m]);
  return (
    <div className="space-y-4">
      <ErrorNote error={data.error} />
      {data.data?.length === 0 && <p className="rounded-lg border bg-background p-6 text-muted-foreground">No results have been published yet.</p>}
      {[...groups.entries()].map(([name, marks]) => (
        <Panel key={name} title={name}>
          <table className="w-full text-sm">
            <thead className="text-left text-muted-foreground">
              <tr><th className="py-1">Subject</th><th className="py-1">Marks</th><th className="py-1">Remark</th></tr>
            </thead>
            <tbody>
              {marks.map((m) => (
                <tr key={m.assessment} className="border-t">
                  <td className="py-1.5">{m.subject}</td>
                  <td className="py-1.5 font-medium">{m.is_absent ? "Absent" : `${Number(m.marks)} / ${Number(m.max_marks)}`}</td>
                  <td className="py-1.5">{m.remark}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      ))}
    </div>
  );
}

function TimetableTab({ id }: { id: string }) {
  const data = useQuery({ queryKey: ["parent-timetable", id], queryFn: () => api.get<TimetableEntry[]>(`/parent/children/${id}/timetable/`) });
  return (
    <Panel title="Timetable">
      <ErrorNote error={data.error} />
      {data.data && <TimetableGrid entries={data.data} show="teacher" />}
    </Panel>
  );
}

function ReportCardsTab({ id }: { id: string }) {
  const data = useQuery({
    queryKey: ["parent-report-cards", id],
    queryFn: () => api.get<ParentReportCard[]>(`/parent/children/${id}/report-cards/`),
  });
  const [error, setError] = useState<unknown>(null);
  return (
    <Panel title="Report cards">
      <ErrorNote error={data.error ?? error} />
      {data.data?.length === 0 && <p className="text-sm text-muted-foreground">No report cards have been published yet.</p>}
      <ul className="divide-y">
        {data.data?.map((r) => (
          <li key={r.term} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span>
              <span className="font-medium">{r.name} {r.session}</span>
              <span className="block text-sm text-muted-foreground">Published {formatDate(r.published_at)}</span>
            </span>
            <Button size="sm" variant="outline"
              onClick={() => openPdf(`/parent/children/${id}/report-cards/${r.term}/`).catch(setError)}>
              Open report card
            </Button>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
