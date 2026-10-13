import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { Field, NativeSelect } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/hooks/use-toast";
import { ApiError, api } from "@/lib/api";
import { sectionLabel, useSections } from "@/lib/academics";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/labels";
import type { MySection, Notice, Paginated } from "@/lib/types";

export default function Notices() {
  const { can, user } = useAuth();
  const queryClient = useQueryClient();
  const manager = can("notices.manage");
  const notices = useQuery({ queryKey: ["notices"], queryFn: () => api.get<Paginated<Notice>>("/notices/") });
  const mine = useQuery({
    queryKey: ["my-sections"],
    queryFn: () => api.get<MySection[]>("/academics/my-sections/"),
    enabled: !manager,
  });
  const { sections: all } = useSections();
  // Managers may post to any class; teachers only to the classes they teach.
  const choices = manager ? (all.data ?? []).map((s) => ({ id: s.id, label: sectionLabel(s) })) : mine.data ?? [];
  const [audience, setAudience] = useState(manager ? "everyone" : "parents");
  const [picked, setPicked] = useState<number[]>([]);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});

  const create = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post<Notice>("/notices/", body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notices"] });
      setPicked([]);
      setFieldErrors({});
      toast({ title: "Notice posted" });
    },
    onError: (err) => setFieldErrors(err instanceof ApiError ? err.fieldErrors : {}),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/notices/${id}/`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["notices"] }),
  });

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    create.mutate(
      { title: data.get("title"), body: data.get("body"), audience, sections: audience === "staff" ? [] : picked },
      { onSuccess: () => form.reset() },
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Notices</h1>
      <Panel title="Post a notice">
        <form onSubmit={submit} className="space-y-3">
          <Field label="Title" required error={fieldErrors.title}>
            <Input name="title" maxLength={150} />
          </Field>
          <Field label="Message" required error={fieldErrors.body}>
            <Textarea name="body" rows={4} />
          </Field>
          {manager && (
            <Field label="Who sees it" required>
              <NativeSelect value={audience} onChange={(e) => setAudience(e.target.value)}>
                <option value="everyone">Everyone (staff and parents)</option>
                <option value="parents">Parents only</option>
                <option value="staff">Staff only</option>
              </NativeSelect>
            </Field>
          )}
          {audience !== "staff" && (
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium">
                {manager ? "Limit to these classes (leave all unticked for the whole school)" : "Parents of"}
              </legend>
              <div className="flex flex-wrap gap-3">
                {choices.map((s) => (
                  <label key={s.id} className="flex items-center gap-2 text-sm">
                    <input type="checkbox" className="h-4 w-4 accent-primary" checked={picked.includes(s.id)}
                      onChange={(e) => setPicked((p) => (e.target.checked ? [...p, s.id] : p.filter((x) => x !== s.id)))} />
                    {s.label}
                  </label>
                ))}
              </div>
              {fieldErrors.sections && <p className="text-sm text-destructive">{fieldErrors.sections.join(" ")}</p>}
            </fieldset>
          )}
          <p className="text-sm text-muted-foreground">Parents see notices in the parent portal. WhatsApp alerts come in a later phase.</p>
          <ErrorNote error={create.error} />
          <Button type="submit" disabled={create.isPending || (!manager && picked.length === 0)}>
            {create.isPending ? "Posting…" : "Post notice"}
          </Button>
        </form>
      </Panel>
      <ErrorNote error={notices.error} />
      <ul className="space-y-3">
        {notices.data?.results.map((n) => (
          <li key={n.id} className="space-y-2 rounded-lg border bg-background p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h2 className="font-semibold">{n.title}</h2>
                <p className="text-xs text-muted-foreground">
                  {formatDateTime(n.published_at ?? n.created_at)} · {n.created_by_name ?? "School"}
                </p>
              </div>
              <div className="flex flex-wrap gap-1">
                <Badge variant="outline">{n.audience_label}</Badge>
                {n.section_labels.map((l) => <Badge key={l} variant="secondary">{l}</Badge>)}
              </div>
            </div>
            <p className="whitespace-pre-line text-sm">{n.body}</p>
            {(manager || n.created_by === user?.id) && (
              <Button variant="ghost" size="sm" className="text-destructive" disabled={remove.isPending}
                onClick={() => window.confirm(`Delete "${n.title}"?`) && remove.mutate(n.id)}>
                Delete
              </Button>
            )}
          </li>
        ))}
        {notices.data?.results.length === 0 && <li className="rounded-lg border bg-background p-6 text-center text-muted-foreground">No notices yet.</li>}
      </ul>
    </div>
  );
}
