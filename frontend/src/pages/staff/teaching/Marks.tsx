import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Field, NativeSelect } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, todayISO } from "@/lib/labels";
import type { Assessment, MySection, Subject } from "@/lib/types";

export default function Marks() {
  const { sectionId } = useParams();
  const { can } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sections = useQuery({ queryKey: ["my-sections"], queryFn: () => api.get<MySection[]>("/academics/my-sections/") });
  const allSubjects = useQuery({
    queryKey: ["subjects"],
    queryFn: () => api.get<Subject[]>("/academics/subjects/"),
    enabled: can("academics.manage"),
  });
  const tests = useQuery({
    queryKey: ["assessments", sectionId],
    queryFn: () => api.get<Assessment[]>("/assessments/", { section: sectionId }),
  });
  const section = sections.data?.find((s) => String(s.id) === sectionId);
  // Admin and principal may set a test in any subject; teachers in the subjects they teach here.
  const subjects = can("academics.manage") ? (allSubjects.data ?? []).filter((s) => s.is_active) : section?.subjects ?? [];
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});

  const create = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post<Assessment>("/assessments/", body),
    onSuccess: (a) => {
      void queryClient.invalidateQueries({ queryKey: ["assessments", sectionId] });
      navigate(`/staff/assessments/${a.id}`);
    },
    onError: (err) => setFieldErrors(err instanceof ApiError ? err.fieldErrors : {}),
  });

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    create.mutate({ section: Number(sectionId), ...Object.fromEntries(form) });
  }

  return (
    <div className="space-y-4">
      <Link to="/staff/classes" className="text-sm text-primary underline-offset-4 hover:underline">
        ← My classes
      </Link>
      <h1 className="text-2xl font-bold">Tests and marks {section ? `· ${section.label}` : ""}</h1>
      <ErrorNote error={tests.error} />
      <ul className="divide-y rounded-lg border bg-background">
        {tests.data?.map((t) => (
          <li key={t.id}>
            <Link to={`/staff/assessments/${t.id}`} className="flex flex-wrap items-center justify-between gap-2 p-3 hover:bg-accent">
              <span>
                <span className="font-medium">{t.name}</span> · {t.subject_name}
                <span className="block text-sm text-muted-foreground">
                  {formatDate(t.date)} · out of {Number(t.max_marks)} · {t.marks_entered} marks entered
                </span>
              </span>
              {t.is_published ? <Badge>Shown to parents</Badge> : <Badge variant="outline">Draft</Badge>}
            </Link>
          </li>
        ))}
        {tests.data?.length === 0 && <li className="p-6 text-center text-muted-foreground">No tests yet.</li>}
      </ul>
      {can("marks.enter") && subjects.length > 0 && (
        <Panel title="New test">
          <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
            <Field label="Subject" required error={fieldErrors.subject}>
              <NativeSelect name="subject" defaultValue="">
                <option value="" disabled>Choose…</option>
                {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </NativeSelect>
            </Field>
            <Field label="Test name" required hint="e.g. Unit Test 1, Half-yearly" error={fieldErrors.name}>
              <Input name="name" maxLength={80} />
            </Field>
            <Field label="Date" required error={fieldErrors.date}>
              <Input name="date" type="date" defaultValue={todayISO()} />
            </Field>
            <Field label="Maximum marks" required error={fieldErrors.max_marks}>
              <Input name="max_marks" type="number" min={1} step="0.5" inputMode="decimal" />
            </Field>
            <div className="sm:col-span-2">
              <ErrorNote error={create.error} />
              <Button type="submit" disabled={create.isPending}>{create.isPending ? "Creating…" : "Create and enter marks"}</Button>
            </div>
          </form>
        </Panel>
      )}
    </div>
  );
}
