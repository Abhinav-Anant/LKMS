import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { ErrorNote, Panel } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { ATTENDANCE_LABELS, formatDate, todayISO } from "@/lib/labels";
import type { AttendanceMonthRow, AttendanceSheet, AttendanceStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUSES: AttendanceStatus[] = ["present", "absent", "late", "leave"];
const STATUS_STYLE: Record<AttendanceStatus, string> = {
  present: "peer-checked:bg-green-600 peer-checked:text-white peer-checked:border-green-600",
  absent: "peer-checked:bg-red-600 peer-checked:text-white peer-checked:border-red-600",
  late: "peer-checked:bg-amber-500 peer-checked:text-white peer-checked:border-amber-500",
  leave: "peer-checked:bg-slate-500 peer-checked:text-white peer-checked:border-slate-500",
};

export default function Attendance() {
  const { sectionId } = useParams();
  const [params, setParams] = useSearchParams();
  const date = params.get("date") ?? todayISO();
  const view = params.get("view") ?? "day";

  return (
    <div className="space-y-4">
      <Link to="/staff/classes" className="text-sm text-primary underline-offset-4 hover:underline">
        ← My classes
      </Link>
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Attendance view">
        {[["day", "Daily register"], ["month", "Monthly summary"]].map(([v, label]) => (
          <Button key={v} role="tab" aria-selected={view === v} variant={view === v ? "default" : "outline"} size="sm"
            onClick={() => setParams({ date, view: v }, { replace: true })}>
            {label}
          </Button>
        ))}
      </div>
      {view === "day" ? (
        <DayRegister sectionId={sectionId!} date={date} onDate={(d) => setParams({ date: d, view }, { replace: true })} />
      ) : (
        <MonthSummary sectionId={sectionId!} initialMonth={date.slice(0, 7)} />
      )}
    </div>
  );
}

function DayRegister({ sectionId, date, onDate }: { sectionId: string; date: string; onDate: (d: string) => void }) {
  const queryClient = useQueryClient();
  const sheet = useQuery({
    queryKey: ["attendance", sectionId, date],
    queryFn: () => api.get<AttendanceSheet>("/attendance/sheet/", { section: sectionId, date }),
  });
  const [marks, setMarks] = useState<Record<number, AttendanceStatus | null>>({});

  useEffect(() => {
    if (sheet.data) setMarks(Object.fromEntries(sheet.data.rows.map((r) => [r.student, r.status])));
  }, [sheet.data]);

  const save = useMutation({
    mutationFn: () =>
      api.post<AttendanceSheet>("/attendance/sheet/", {
        section: Number(sectionId),
        date,
        records: Object.entries(marks).filter(([, s]) => s).map(([student, status]) => ({ student: Number(student), status })),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["attendance", sectionId, date], data);
      toast({ title: "Attendance saved", description: `${data.section_label}, ${formatDate(date)}` });
    },
  });

  const rows = sheet.data?.rows ?? [];
  const missing = rows.filter((r) => !marks[r.student]).length;
  const absent = rows.filter((r) => marks[r.student] === "absent").length;
  const editable = Boolean(sheet.data?.can_edit);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Attendance {sheet.data ? `· ${sheet.data.section_label}` : ""}</h1>
          <p className="text-sm text-muted-foreground">
            {sheet.data?.marked ? `Marked${sheet.data.marked_by ? ` by ${sheet.data.marked_by}` : ""}.` : "Not marked yet."}{" "}
            {!editable && sheet.data && "You can view this register but not change it."}
          </p>
        </div>
        <label className="space-y-1 text-sm">
          <span className="block font-medium">Date</span>
          <Input type="date" value={date} max={todayISO()} onChange={(e) => e.target.value && onDate(e.target.value)} className="w-44" />
        </label>
      </div>
      <ErrorNote error={sheet.error} />
      {editable && rows.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setMarks(Object.fromEntries(rows.map((r) => [r.student, marks[r.student] ?? "present"])))}>
            Mark the rest present
          </Button>
          <span className="text-sm text-muted-foreground">
            {rows.length} students · {absent} absent{missing ? ` · ${missing} not marked` : ""}
          </span>
        </div>
      )}
      <ul className="divide-y rounded-lg border bg-background">
        {rows.map((r) => (
          <li key={r.student} className="flex flex-wrap items-center justify-between gap-2 p-3">
            <div>
              <span className="mr-2 inline-block w-8 text-muted-foreground">{r.roll_number ?? "–"}</span>
              <span className="font-medium">{r.name}</span>
            </div>
            <fieldset className="flex gap-1" disabled={!editable}>
              <legend className="sr-only">{r.name}</legend>
              {STATUSES.map((s) => (
                <label key={s} className="cursor-pointer">
                  <input type="radio" name={`s-${r.student}`} value={s} checked={marks[r.student] === s} className="peer sr-only"
                    onChange={() => setMarks((m) => ({ ...m, [r.student]: s }))} />
                  <span className={cn("inline-flex h-9 min-w-9 items-center justify-center rounded-md border px-2 text-sm peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-disabled:opacity-60", STATUS_STYLE[s])}
                    title={ATTENDANCE_LABELS[s]}>
                    <span aria-hidden="true">{s === "leave" ? "Lv" : s[0].toUpperCase()}</span>
                    <span className="sr-only">{ATTENDANCE_LABELS[s]}</span>
                  </span>
                </label>
              ))}
            </fieldset>
          </li>
        ))}
        {sheet.data && rows.length === 0 && <li className="p-6 text-center text-muted-foreground">No students in this section.</li>}
      </ul>
      <p className="text-xs text-muted-foreground">P present · A absent · L late · Lv on leave</p>
      <ErrorNote error={save.error} />
      {editable && rows.length > 0 && (
        <Button onClick={() => save.mutate()} disabled={save.isPending || missing === rows.length}>
          {save.isPending ? "Saving…" : "Save attendance"}
        </Button>
      )}
    </div>
  );
}

function MonthSummary({ sectionId, initialMonth }: { sectionId: string; initialMonth: string }) {
  const [month, setMonth] = useState(initialMonth);
  const rows = useQuery({
    queryKey: ["attendance-month", sectionId, month],
    queryFn: () => api.get<AttendanceMonthRow[]>("/attendance/month/", { section: sectionId, month }),
  });
  return (
    <Panel title="Monthly summary" actions={
      <Input type="month" aria-label="Month" value={month} onChange={(e) => e.target.value && setMonth(e.target.value)} className="w-44" />
    }>
      <ErrorNote error={rows.error} />
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-muted-foreground">
            <tr>
              <th className="p-2">Roll</th><th className="p-2">Name</th><th className="p-2">Present</th><th className="p-2">Absent</th>
              <th className="p-2">Late</th><th className="p-2">Leave</th><th className="p-2">Attendance</th>
            </tr>
          </thead>
          <tbody>
            {rows.data?.map((r) => (
              <tr key={r.student} className="border-t">
                <td className="p-2">{r.roll_number ?? "–"}</td>
                <td className="p-2 font-medium">{r.name}</td>
                <td className="p-2">{r.present}</td>
                <td className="p-2">{r.absent}</td>
                <td className="p-2">{r.late}</td>
                <td className="p-2">{r.leave}</td>
                <td className={cn("p-2", r.percentage !== null && r.percentage < 75 && "font-semibold text-destructive")}>
                  {r.percentage === null ? "–" : `${r.percentage}%`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted-foreground">Late counts as present. Below 75% is shown in red.</p>
    </Panel>
  );
}
