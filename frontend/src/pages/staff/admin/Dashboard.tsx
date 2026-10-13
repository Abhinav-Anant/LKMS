import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ErrorNote, Panel } from "@/components/Panel";
import { api } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/labels";
import type { Dashboard as DashboardData } from "@/lib/types";

function Stat({ label, value, to }: { label: string; value: string | number; to?: string }) {
  const body = (
    <>
      <span className="block text-sm text-muted-foreground">{label}</span>
      <span className="text-2xl font-bold">{value}</span>
    </>
  );
  return to ? (
    <Link to={to} className="block rounded-lg border bg-background p-4 hover:bg-accent">{body}</Link>
  ) : (
    <div className="rounded-lg border bg-background p-4">{body}</div>
  );
}

export default function Dashboard() {
  const data = useQuery({ queryKey: ["dashboard"], queryFn: () => api.get<DashboardData>("/reports/dashboard/") });
  const d = data.data;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">School dashboard</h1>
      <ErrorNote error={data.error} />
      {d && (
        <>
          <p className="text-sm text-muted-foreground">Session {d.session ?? "not set"} · {formatDate(d.date)}</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Students studying" value={d.students_total} to="/staff/students" />
            <Stat label="Present today" value={d.attendance_today.present} />
            <Stat label="Absent today" value={d.attendance_today.absent} />
            <Stat label="Registers marked" value={`${d.attendance_today.sections_marked} of ${d.attendance_today.sections_total}`} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Fees collected this session" value={formatMoney(d.fees.collected)} to="/staff/fees/reports" />
            <Stat label="Fees outstanding" value={formatMoney(d.fees.outstanding)} to="/staff/fees/reports" />
            <Stat label="Collected this month" value={formatMoney(d.fees.collected_this_month)} />
            <Stat label="Overdue invoices" value={d.fees.overdue_invoices} to="/staff/fees" />
          </div>
          <Panel title="Waiting for action">
            <ul className="grid gap-3 sm:grid-cols-3">
              <li><Stat label="Admission applications" value={d.pending.admissions} to="/staff/applications" /></li>
              <li><Stat label="UPI payments to check" value={d.pending.upi_payments} to="/staff/fees/upi" /></li>
              <li><Stat label="Concession requests" value={d.pending.concessions} to="/staff/fees/concessions" /></li>
            </ul>
          </Panel>
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Students by class">
              <table className="w-full text-sm">
                <tbody>
                  {d.students_by_class.map((c) => (
                    <tr key={c.name} className="border-t first:border-t-0">
                      <td className="py-1.5">{c.name}</td>
                      <td className="py-1.5 text-right font-medium">{c.students}</td>
                    </tr>
                  ))}
                  {d.students_by_class.length === 0 && <tr><td className="text-muted-foreground">No students enrolled this session.</td></tr>}
                </tbody>
              </table>
            </Panel>
            <Panel title="Registers not marked today">
              {d.attendance_today.sections_not_marked.length === 0 ? (
                <p className="text-sm text-muted-foreground">Every class has been marked.</p>
              ) : (
                <p className="text-sm">{d.attendance_today.sections_not_marked.join(", ")}</p>
              )}
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}
