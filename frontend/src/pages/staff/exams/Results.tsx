import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ErrorNote } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import type { ResultSheet } from "@/lib/types";
import { openPdf } from "@/pages/staff/fees/receipt";

interface Entry {
  remark: string;
  co_scholastic: Record<string, string>;
}

export default function Results() {
  const { termId, sectionId } = useParams();
  const queryClient = useQueryClient();
  const key = ["results", termId, sectionId];
  const sheet = useQuery({
    queryKey: key,
    queryFn: () => api.get<ResultSheet>(`/exams/terms/${termId}/results/`, { section: sectionId }),
  });
  const [entries, setEntries] = useState<Record<number, Entry>>({});
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (sheet.data) {
      setEntries(Object.fromEntries(sheet.data.rows.map((r) => [r.student, { remark: r.remark, co_scholastic: r.co_scholastic }])));
      setDirty(false);
    }
  }, [sheet.data]);

  const save = useMutation({
    mutationFn: () =>
      api.post<ResultSheet>(`/exams/terms/${termId}/remarks/?section=${sectionId}`, {
        rows: Object.entries(entries).map(([student, e]) => ({ student: Number(student), ...e })),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(key, data);
      toast({ title: "Remarks saved" });
    },
  });
  const pdf = useMutation({ mutationFn: (path: string) => openPdf(path) });

  const d = sheet.data;
  const subjects = [...new Set(d?.rows.flatMap((r) => r.subjects.map((s) => s.subject)) ?? [])];
  const editable = Boolean(d?.can_edit_remarks);
  const cardsPath = `/exams/terms/${termId}/report-cards/?section=${sectionId}`;

  function update(student: number, change: Partial<Entry>) {
    setEntries((all) => ({ ...all, [student]: { ...all[student], ...change } }));
    setDirty(true);
  }

  return (
    <div className="space-y-4">
      <Link to="/staff/exams" className="text-sm text-primary underline-offset-4 hover:underline">← Exams</Link>
      <ErrorNote error={sheet.error} />
      {d && (
        <>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h1 className="text-2xl font-bold">{d.term.name} results · {d.section_label}</h1>
              <p className="text-sm text-muted-foreground">
                {d.term.session_name} · {d.rows.length} students · grades per subject, overall percentage and attendance for the term
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {d.term.is_published ? <Badge>Shown to parents</Badge> : <Badge variant="outline">Not shown to parents</Badge>}
              <Button variant="outline" onClick={() => pdf.mutate(cardsPath)} disabled={pdf.isPending || d.rows.length === 0}>
                Print all report cards
              </Button>
            </div>
          </div>
          {d.term.unpublished_assessments > 0 && (
            <p className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              {d.term.unpublished_assessments} test(s) in this term are still drafts. Their marks are included here but
              the report cards cannot be published until every test is published.
            </p>
          )}
          <div className="overflow-x-auto rounded-lg border bg-background">
            <table className="w-full text-sm">
              <thead className="text-left text-muted-foreground">
                <tr>
                  <th className="p-2">Roll</th>
                  <th className="p-2">Name</th>
                  {subjects.map((s) => <th key={s} className="p-2">{s}</th>)}
                  <th className="p-2">Overall</th>
                  <th className="p-2">Result</th>
                  <th className="p-2">Attendance</th>
                  <th className="p-2">Remark</th>
                  <th className="p-2"><span className="sr-only">Report card</span></th>
                </tr>
              </thead>
              <tbody>
                {d.rows.map((r) => {
                  const entry = entries[r.student] ?? { remark: "", co_scholastic: {} };
                  const bySubject = Object.fromEntries(r.subjects.map((s) => [s.subject, s]));
                  return (
                    <Fragment key={r.student}>
                      <tr className="border-t align-top">
                        <td className="p-2">{r.roll_number ?? "–"}</td>
                        <td className="p-2 font-medium">{r.name}</td>
                        {subjects.map((s) => (
                          <td key={s} className="p-2">
                            {bySubject[s] ? `${bySubject[s].grade || "–"}` : "–"}
                            {bySubject[s]?.percent && <span className="block text-xs text-muted-foreground">{Number(bySubject[s].percent)}%</span>}
                          </td>
                        ))}
                        <td className="p-2 font-medium">
                          {r.grade || "–"}
                          {r.percent && <span className="block text-xs text-muted-foreground">{Number(r.percent)}%</span>}
                        </td>
                        <td className="p-2">{r.result === "Pass" ? "Pass" : r.result ? <span className="text-destructive">{r.result}</span> : "–"}</td>
                        <td className="p-2">{r.attendance_marked ? `${r.attendance_present}/${r.attendance_marked}` : "–"}</td>
                        <td className="p-2">
                          <Input className="h-9 min-w-56" maxLength={300} aria-label={`Remark for ${r.name}`} value={entry.remark}
                            disabled={!editable} onChange={(e) => update(r.student, { remark: e.target.value })} />
                        </td>
                        <td className="p-2">
                          <Button size="sm" variant="ghost" disabled={pdf.isPending}
                            onClick={() => pdf.mutate(`${cardsPath}&student=${r.student}`)}>
                            PDF
                          </Button>
                        </td>
                      </tr>
                      <tr>
                        <td />
                        <td colSpan={subjects.length + 6} className="px-2 pb-3">
                          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
                            {d.co_scholastic_areas.map((area) => (
                              <label key={area} className="flex items-center gap-1 text-muted-foreground">
                                {area}
                                <select className="h-7 rounded border border-input bg-background px-1 text-foreground" disabled={!editable}
                                  value={entry.co_scholastic[area] ?? ""}
                                  onChange={(e) => update(r.student, { co_scholastic: { ...entry.co_scholastic, [area]: e.target.value } })}>
                                  <option value="">–</option>
                                  {d.co_scholastic_grades.map((g) => <option key={g} value={g}>{g}</option>)}
                                </select>
                              </label>
                            ))}
                          </div>
                        </td>
                      </tr>
                    </Fragment>
                  );
                })}
                {d.rows.length === 0 && (
                  <tr><td colSpan={subjects.length + 7} className="p-6 text-center text-muted-foreground">No students in this class.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {subjects.length === 0 && d.rows.length > 0 && (
            <p className="text-sm text-muted-foreground">No tests in this class are linked to {d.term.name} yet.</p>
          )}
          <ErrorNote error={save.error ?? pdf.error} />
          {editable ? (
            <Button onClick={() => save.mutate()} disabled={save.isPending || !dirty}>
              {save.isPending ? "Saving…" : "Save remarks and grades"}
            </Button>
          ) : (
            <p className="text-sm text-muted-foreground">
              {d.term.is_published
                ? "Report cards are published. Only the principal can change remarks now."
                : "Only the class teacher and the principal write report card remarks."}
            </p>
          )}
        </>
      )}
    </div>
  );
}
