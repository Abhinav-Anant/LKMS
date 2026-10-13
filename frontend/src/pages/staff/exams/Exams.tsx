import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { Field, NativeSelect } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";
import { ApiError, api } from "@/lib/api";
import { sectionLabel, useSections } from "@/lib/academics";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/labels";
import type { ExamTerm, GradeBand, MySection } from "@/lib/types";

import GradeScale from "./GradeScale";

export default function Exams() {
  const { can } = useAuth();
  const manages = can("academics.manage");
  const [chosenSession, setChosenSession] = useState<number>();
  const { sessions, sessionId, sections } = useSections(chosenSession);
  const mine = useQuery({
    queryKey: ["my-sections"],
    queryFn: () => api.get<MySection[]>("/academics/my-sections/"),
    enabled: !manages,
  });
  const sectionOptions = manages
    ? (sections.data ?? []).map((s) => ({ id: s.id, label: sectionLabel(s) }))
    : (mine.data ?? []).map((s) => ({ id: s.id, label: s.label }));
  const terms = useQuery({
    queryKey: ["exam-terms", sessionId],
    queryFn: () => api.get<ExamTerm[]>("/exams/terms/", { session: sessionId }),
    enabled: Boolean(sessionId),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Exams and report cards</h1>
          <p className="text-sm text-muted-foreground">
            Tests are added under each class's marks. Link them to a term here to put them on that term's report card.
          </p>
        </div>
        {manages && (
          <label className="flex items-center gap-2 text-sm">
            Session
            <NativeSelect className="h-10 w-36" value={sessionId ?? ""} onChange={(e) => setChosenSession(Number(e.target.value))}>
              {sessions.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </NativeSelect>
          </label>
        )}
      </div>
      <ErrorNote error={terms.error} />
      <div className="space-y-3">
        {terms.data?.map((t) => <TermCard key={t.id} term={t} manages={manages} sections={sectionOptions} />)}
        {terms.data?.length === 0 && (
          <p className="rounded-lg border bg-background p-6 text-center text-muted-foreground">
            No exam terms for this session yet.{manages ? " Add one below." : " The principal adds them."}
          </p>
        )}
      </div>
      {manages && sessionId && <NewTerm sessionId={sessionId} />}
      {manages && <GradeScale />}
      {!manages && <GradeScaleView />}
    </div>
  );
}

function TermCard({ term, manages, sections }: { term: ExamTerm; manages: boolean; sections: { id: number; label: string }[] }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [section, setSection] = useState("");
  const publish = useMutation({
    mutationFn: (action: "publish" | "unpublish") => api.post<ExamTerm>(`/exams/terms/${term.id}/${action}/`),
    onSuccess: (t) => {
      void queryClient.invalidateQueries({ queryKey: ["exam-terms"] });
      toast({ title: t.is_published ? "Report cards are now shown to parents" : "Report cards withdrawn from parents" });
    },
  });
  return (
    <section className="space-y-3 rounded-lg border bg-background p-4" aria-label={term.name}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="font-semibold">{term.name} · {term.session_name}</h2>
          <p className="text-sm text-muted-foreground">
            {formatDate(term.start_date)} to {formatDate(term.end_date)} · {term.assessments} test{term.assessments === 1 ? "" : "s"}
            {term.unpublished_assessments > 0 && ` · ${term.unpublished_assessments} not yet published`}
          </p>
        </div>
        {term.is_published ? <Badge>Shown to parents</Badge> : <Badge variant="outline">Not shown to parents</Badge>}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <NativeSelect aria-label={`Class for ${term.name} results`} className="h-10 w-48" value={section} onChange={(e) => setSection(e.target.value)}>
          <option value="">Choose a class…</option>
          {sections.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </NativeSelect>
        <Button variant="outline" disabled={!section} onClick={() => navigate(`/staff/exams/${term.id}/sections/${section}`)}>
          Results and report cards
        </Button>
        {manages && !term.is_published && (
          <Button onClick={() => publish.mutate("publish")} disabled={publish.isPending || term.assessments === 0}>
            Publish report cards
          </Button>
        )}
        {manages && term.is_published && (
          <Button variant="outline" onClick={() => publish.mutate("unpublish")} disabled={publish.isPending}>
            Withdraw from parents
          </Button>
        )}
      </div>
      {manages && !term.is_published && (
        <p className="text-sm text-muted-foreground">Publishing shows report cards in the parent portal and sends each family one WhatsApp message.</p>
      )}
      <ErrorNote error={publish.error} />
    </section>
  );
}

function NewTerm({ sessionId }: { sessionId: number }) {
  const queryClient = useQueryClient();
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const create = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post<ExamTerm>("/exams/terms/", body),
    onSuccess: () => {
      setErrors({});
      void queryClient.invalidateQueries({ queryKey: ["exam-terms"] });
      toast({ title: "Term added" });
    },
    onError: (err) => setErrors(err instanceof ApiError ? err.fieldErrors : {}),
  });
  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    create.mutate({ session: sessionId, ...Object.fromEntries(new FormData(e.currentTarget)) });
    e.currentTarget.reset();
  }
  return (
    <Panel title="New exam term">
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-4">
        <Field label="Name" required hint="e.g. Half-yearly" error={errors.name}>
          <Input name="name" maxLength={60} />
        </Field>
        <Field label="Attendance from" required error={errors.start_date}>
          <Input name="start_date" type="date" />
        </Field>
        <Field label="Attendance to" required error={errors.end_date}>
          <Input name="end_date" type="date" />
        </Field>
        <Field label="Order" hint="1 for the first term" error={errors.order}>
          <Input name="order" type="number" min={1} defaultValue={1} />
        </Field>
        <div className="sm:col-span-4">
          <ErrorNote error={create.error} />
          <Button type="submit" disabled={create.isPending}>Add term</Button>
        </div>
      </form>
    </Panel>
  );
}

function GradeScaleView() {
  const bands = useQuery({ queryKey: ["grade-bands"], queryFn: () => api.get<GradeBand[]>("/exams/grades/") });
  if (!bands.data?.length) return null;
  return (
    <Panel title="Grade scale">
      <p className="text-sm">
        {bands.data.map((b) => `${b.grade}: ${Number(b.min_percent)}% and above${b.is_pass ? "" : " (fail)"}`).join(" · ")}
      </p>
    </Panel>
  );
}
