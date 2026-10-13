import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ErrorNote, Panel } from "@/components/Panel";
import { TimetableGrid } from "@/components/TimetableGrid";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { MySection, TimetableEntry } from "@/lib/types";

export default function MyClasses() {
  const { can } = useAuth();
  const sections = useQuery({ queryKey: ["my-sections"], queryFn: () => api.get<MySection[]>("/academics/my-sections/") });
  const timetable = useQuery({ queryKey: ["my-timetable"], queryFn: () => api.get<TimetableEntry[]>("/academics/my-timetable/") });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">My classes</h1>
      <ErrorNote error={sections.error} />
      {sections.data?.length === 0 && (
        <p className="rounded-lg border bg-background p-6 text-muted-foreground">
          You have no classes this session yet. The principal assigns class teachers and subjects under School setup.
        </p>
      )}
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {sections.data?.map((s) => (
          <li key={s.id} className="space-y-3 rounded-lg border bg-background p-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h2 className="text-lg font-semibold">{s.label}</h2>
                <p className="text-sm text-muted-foreground">{s.strength} students</p>
              </div>
              {s.is_class_teacher && <Badge>Class teacher</Badge>}
            </div>
            {s.subjects.length > 0 && <p className="text-sm">{s.subjects.map((x) => x.name).join(", ")}</p>}
            <div className="flex flex-wrap gap-2">
              {can("attendance.view") && (
                <Button asChild size="sm" variant={s.is_class_teacher ? "default" : "outline"}>
                  <Link to={`/staff/classes/${s.id}/attendance`}>Attendance</Link>
                </Button>
              )}
              {can("marks.view") && (
                <Button asChild size="sm" variant="outline">
                  <Link to={`/staff/classes/${s.id}/marks`}>Tests and marks</Link>
                </Button>
              )}
            </div>
          </li>
        ))}
      </ul>
      <Panel title="My timetable">
        <ErrorNote error={timetable.error} />
        {timetable.data && <TimetableGrid entries={timetable.data} show="section" />}
      </Panel>
    </div>
  );
}
