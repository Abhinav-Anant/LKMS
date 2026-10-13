import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { NativeSelect } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { sectionLabel, useSections } from "@/lib/academics";
import { api } from "@/lib/api";
import { WEEKDAYS, formatTime } from "@/lib/labels";
import type { PeriodSlot, Subject, TeachingAssignment, TimetableEntry } from "@/lib/types";

/** Edit one section's week. The teacher comes from Subject teachers for that section. */
export default function Timetable() {
  const queryClient = useQueryClient();
  const [chosen, setChosen] = useState<number>();
  const { sections } = useSections();
  const section = chosen ?? sections.data?.[0]?.id;
  const periods = useQuery({ queryKey: ["periods"], queryFn: () => api.get<PeriodSlot[]>("/academics/periods/") });
  const subjects = useQuery({ queryKey: ["subjects"], queryFn: () => api.get<Subject[]>("/academics/subjects/") });
  const assignments = useQuery({
    queryKey: ["teaching-assignments", section],
    queryFn: () => api.get<TeachingAssignment[]>("/academics/teaching-assignments/", { section }),
    enabled: Boolean(section),
  });
  const entries = useQuery({
    queryKey: ["timetable", section],
    queryFn: () => api.get<TimetableEntry[]>("/academics/timetable/", { section }),
    enabled: Boolean(section),
  });

  const save = useMutation({
    mutationFn: async ({ day, period, subject }: { day: number; period: number; subject: string }) => {
      const existing = entries.data?.find((e) => e.weekday === day && e.period === period);
      if (!subject) return existing ? api.delete(`/academics/timetable/${existing.id}/`) : undefined;
      const teacher = assignments.data?.find((a) => a.subject === Number(subject))?.teacher ?? null;
      const body = { section, weekday: day, period, subject: Number(subject), teacher };
      return existing ? api.patch(`/academics/timetable/${existing.id}/`, body) : api.post("/academics/timetable/", body);
    },
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["timetable", section] }),
  });

  const teacherOf = (subject: number) => assignments.data?.find((a) => a.subject === subject)?.teacher_name;

  return (
    <Panel title="Timetable">
      <label className="block space-y-1 text-sm sm:w-56">
        <span className="font-medium">Section (current session)</span>
        <NativeSelect value={section ?? ""} onChange={(e) => setChosen(Number(e.target.value))}>
          {sections.data?.map((s) => <option key={s.id} value={s.id}>{sectionLabel(s)}</option>)}
        </NativeSelect>
      </label>
      <p className="text-sm text-muted-foreground">
        Pick a subject for each period. The teacher is taken from Subject teachers. A teacher cannot be in two classes in the same period.
      </p>
      <ErrorNote error={entries.error ?? save.error} />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead>
            <tr>
              <th className="p-2 text-left">Period</th>
              {WEEKDAYS.map(([n, name]) => <th key={n} className="p-2 text-left">{name}</th>)}
            </tr>
          </thead>
          <tbody>
            {periods.data?.map((p) => (
              <tr key={p.id} className="border-t">
                <th scope="row" className="p-2 text-left font-medium">
                  {p.number}
                  <span className="block text-xs font-normal text-muted-foreground">{formatTime(p.start_time)}–{formatTime(p.end_time)}</span>
                </th>
                {WEEKDAYS.map(([day, dayName]) => {
                  const entry = entries.data?.find((e) => e.weekday === day && e.period === p.id);
                  return (
                    <td key={day} className="p-1 align-top">
                      <NativeSelect className="h-9 text-sm" aria-label={`${dayName} period ${p.number}`} value={entry?.subject ?? ""}
                        disabled={save.isPending} onChange={(e) => save.mutate({ day, period: p.id, subject: e.target.value })}>
                        <option value="">–</option>
                        {subjects.data?.filter((s) => s.is_active).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                      </NativeSelect>
                      {entry && <span className="block truncate px-1 text-xs text-muted-foreground">{entry.teacher_name || teacherOf(entry.subject) || "No teacher"}</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
