import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { ErrorNote, Panel } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import type { GradeBand } from "@/lib/types";

/** The principal edits the grading scale. The default is a placeholder until the school confirms its own. */
export default function GradeScale() {
  const queryClient = useQueryClient();
  const bands = useQuery({ queryKey: ["grade-bands"], queryFn: () => api.get<GradeBand[]>("/exams/grades/") });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["grade-bands"] });
  const save = useMutation({
    mutationFn: ({ id, ...body }: Partial<GradeBand>) =>
      id ? api.patch<GradeBand>(`/exams/grades/${id}/`, body) : api.post<GradeBand>("/exams/grades/", body),
    onSuccess: () => {
      refresh();
      toast({ title: "Grade scale saved" });
    },
  });
  const remove = useMutation({ mutationFn: (id: number) => api.delete(`/exams/grades/${id}/`), onSuccess: refresh });
  const [adding, setAdding] = useState(false);

  function submit(e: FormEvent<HTMLFormElement>, id?: number) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    save.mutate({
      id,
      grade: String(form.get("grade")),
      min_percent: String(form.get("min_percent")),
      description: String(form.get("description") ?? ""),
      is_pass: form.get("is_pass") === "on",
    });
    if (!id) setAdding(false);
  }

  return (
    <Panel title="Grade scale" actions={<Button size="sm" variant="outline" onClick={() => setAdding(true)}>Add grade</Button>}>
      <p className="text-sm text-muted-foreground">
        A percentage at or above the minimum earns the grade. This scale is a placeholder until the school confirms the one it uses.
      </p>
      <div className="space-y-2">
        {[...(bands.data ?? []), ...(adding ? [null] : [])].map((b) => (
          <form key={b?.id ?? "new"} onSubmit={(e) => submit(e, b?.id)} className="flex flex-wrap items-center gap-2">
            <Input name="grade" aria-label="Grade" defaultValue={b?.grade} maxLength={4} required className="h-9 w-20" />
            <Input name="min_percent" aria-label="Minimum percent" type="number" min={0} max={100} step="0.01" required
              defaultValue={b ? Number(b.min_percent) : ""} className="h-9 w-24" />
            <span className="text-sm text-muted-foreground">% and above</span>
            <Input name="description" aria-label="Description" defaultValue={b?.description} maxLength={60} className="h-9 w-44" />
            <label className="flex items-center gap-1 text-sm">
              <input type="checkbox" name="is_pass" defaultChecked={b?.is_pass ?? true} className="h-4 w-4 accent-primary" /> Pass
            </label>
            <Button size="sm" type="submit" variant="outline" disabled={save.isPending}>Save</Button>
            {b && (
              <Button size="sm" type="button" variant="ghost" onClick={() => remove.mutate(b.id)} disabled={remove.isPending}>
                Remove
              </Button>
            )}
          </form>
        ))}
      </div>
      <ErrorNote error={save.error ?? remove.error} />
    </Panel>
  );
}
