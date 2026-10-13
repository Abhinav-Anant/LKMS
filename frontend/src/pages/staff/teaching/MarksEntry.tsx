import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ErrorNote } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/labels";
import type { Assessment, ExamTerm, MarkSheet } from "@/lib/types";

interface Row {
  marks: string;
  is_absent: boolean;
  remark: string;
}

export default function MarksEntry() {
  const { id } = useParams();
  const { can, user } = useAuth();
  const queryClient = useQueryClient();
  const key = ["mark-sheet", id];
  const sheet = useQuery({ queryKey: key, queryFn: () => api.get<MarkSheet>(`/assessments/${id}/marks/`) });
  const [rows, setRows] = useState<Record<number, Row>>({});

  useEffect(() => {
    if (sheet.data)
      setRows(Object.fromEntries(sheet.data.rows.map((r) => [r.student, { marks: r.marks ?? "", is_absent: r.is_absent, remark: r.remark }])));
  }, [sheet.data]);

  const save = useMutation({
    mutationFn: () =>
      api.post<MarkSheet>(`/assessments/${id}/marks/`, {
        rows: Object.entries(rows)
          .filter(([, r]) => r.marks !== "" || r.is_absent || r.remark)
          .map(([student, r]) => ({ student: Number(student), marks: r.marks === "" ? null : r.marks, is_absent: r.is_absent, remark: r.remark })),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(key, data);
      toast({ title: "Marks saved" });
    },
  });
  const publish = useMutation({
    mutationFn: (action: "publish" | "unpublish") => api.post<Assessment>(`/assessments/${id}/${action}/`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: key }),
  });

  const terms = useQuery({ queryKey: ["exam-terms", "all"], queryFn: () => api.get<ExamTerm[]>("/exams/terms/") });
  const setTerm = useMutation({
    mutationFn: (term: number | null) => api.patch<Assessment>(`/assessments/${id}/`, { term }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: key });
      toast({ title: "Report card updated" });
    },
  });

  const a = sheet.data?.assessment;
  const max = a ? Number(a.max_marks) : 0;
  const editable = Boolean(sheet.data?.can_edit);
  const over = Object.values(rows).some((r) => r.marks !== "" && Number(r.marks) > max);
  const seesAll = user?.role === "admin" || user?.role === "principal" || can("academics.manage");

  function update(student: number, change: Partial<Row>) {
    setRows((all) => ({ ...all, [student]: { ...all[student], ...change } }));
  }

  return (
    <div className="space-y-4">
      {a && (
        <Link to={`/staff/classes/${a.section}/marks`} className="text-sm text-primary underline-offset-4 hover:underline">
          ← Tests for {a.section_label}
        </Link>
      )}
      <ErrorNote error={sheet.error} />
      {a && (
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h1 className="text-2xl font-bold">{a.name} · {a.subject_name}</h1>
            <p className="text-sm text-muted-foreground">
              {a.section_label} · {formatDate(a.date)} · out of {max}
            </p>
            <label className="mt-1 flex items-center gap-2 text-sm">
              Counts towards
              <select className="h-9 rounded-md border border-input bg-background px-2" value={a.term ?? ""}
                disabled={!editable || setTerm.isPending}
                onChange={(e) => setTerm.mutate(e.target.value ? Number(e.target.value) : null)}>
                <option value="">No report card</option>
                {terms.data?.map((t) => <option key={t.id} value={t.id}>{t.name} {t.session_name}</option>)}
              </select>
            </label>
          </div>
          {a.is_published ? <Badge>Shown to parents</Badge> : <Badge variant="outline">Draft, parents cannot see it</Badge>}
        </div>
      )}
      <div className="overflow-x-auto rounded-lg border bg-background">
        <table className="w-full text-sm">
          <thead className="text-left text-muted-foreground">
            <tr>
              <th className="p-2">Roll</th><th className="p-2">Name</th><th className="p-2">Marks</th><th className="p-2">Absent</th><th className="p-2">Remark</th>
            </tr>
          </thead>
          <tbody>
            {sheet.data?.rows.map((r) => {
              const row = rows[r.student] ?? { marks: "", is_absent: false, remark: "" };
              const tooHigh = row.marks !== "" && Number(row.marks) > max;
              return (
                <tr key={r.student} className="border-t">
                  <td className="p-2">{r.roll_number ?? "–"}</td>
                  <td className="p-2 font-medium">{r.name}</td>
                  <td className="p-2">
                    <Input type="number" inputMode="decimal" min={0} max={max} step="0.5" className="h-9 w-24" aria-label={`Marks for ${r.name}`}
                      value={row.marks} disabled={!editable || row.is_absent} aria-invalid={tooHigh || undefined}
                      onChange={(e) => update(r.student, { marks: e.target.value })} />
                    {tooHigh && <span className="block text-xs text-destructive">Above {max}</span>}
                  </td>
                  <td className="p-2">
                    <input type="checkbox" className="h-5 w-5 accent-primary" aria-label={`${r.name} was absent`} checked={row.is_absent}
                      disabled={!editable} onChange={(e) => update(r.student, { is_absent: e.target.checked, marks: e.target.checked ? "" : row.marks })} />
                  </td>
                  <td className="p-2">
                    <Input className="h-9 min-w-40" maxLength={200} aria-label={`Remark for ${r.name}`} value={row.remark} disabled={!editable}
                      onChange={(e) => update(r.student, { remark: e.target.value })} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <ErrorNote error={save.error ?? publish.error ?? setTerm.error} />
      <div className="flex flex-wrap gap-2">
        {editable && (
          <Button onClick={() => save.mutate()} disabled={save.isPending || over}>
            {save.isPending ? "Saving…" : "Save marks"}
          </Button>
        )}
        {a && !a.is_published && editable && (
          <Button variant="outline" disabled={publish.isPending || a.marks_entered === 0}
            onClick={() => window.confirm("Show these marks to parents? Only the principal can change them afterwards.") && publish.mutate("publish")}>
            Show to parents
          </Button>
        )}
        {a?.is_published && seesAll && (
          <Button variant="outline" disabled={publish.isPending} onClick={() => publish.mutate("unpublish")}>
            Hide from parents
          </Button>
        )}
      </div>
      {a && !a.is_published && a.marks_entered === 0 && editable && (
        <p className="text-sm text-muted-foreground">Save marks first, then show them to parents.</p>
      )}
    </div>
  );
}
