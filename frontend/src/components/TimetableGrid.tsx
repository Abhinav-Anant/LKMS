import { WEEKDAYS, formatTime } from "@/lib/labels";
import type { TimetableEntry } from "@/lib/types";

/** Week grid: one row per period, one column per school day. `show` picks the second line of each cell. */
export function TimetableGrid({ entries, show }: { entries: TimetableEntry[]; show: "teacher" | "section" }) {
  if (entries.length === 0) return <p className="text-sm text-muted-foreground">No timetable has been entered yet.</p>;
  const periods = [...new Map(entries.map((e) => [e.period_number, e])).values()].sort((a, b) => a.period_number - b.period_number);
  const cell = (day: number, period: number) => entries.find((e) => e.weekday === day && e.period_number === period);
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <thead>
          <tr>
            <th scope="col" className="border p-2 text-left">Period</th>
            {WEEKDAYS.map(([n, name]) => (
              <th key={n} scope="col" className="border p-2 text-left">{name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {periods.map((p) => (
            <tr key={p.period_number}>
              <th scope="row" className="border p-2 text-left font-medium">
                {p.period_number}
                <span className="block text-xs font-normal text-muted-foreground">
                  {formatTime(p.start_time)}–{formatTime(p.end_time)}
                </span>
              </th>
              {WEEKDAYS.map(([n]) => {
                const e = cell(n, p.period_number);
                return (
                  <td key={n} className="border p-2 align-top">
                    {e ? (
                      <>
                        <span className="font-medium">{e.subject_name}</span>
                        <span className="block text-xs text-muted-foreground">
                          {show === "teacher" ? e.teacher_name : e.section_label.replace(/ \(.*\)$/, "")}
                        </span>
                      </>
                    ) : (
                      <span className="text-muted-foreground">–</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
