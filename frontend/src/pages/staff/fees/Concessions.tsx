import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { Field, NativeSelect } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CONCESSION_STATUS_LABELS, formatDateTime, formatMoney } from "@/lib/labels";
import type { AcademicSession, Concession, FeeHead, Paginated, StudentListItem } from "@/lib/types";

import { FeesNav } from "./FeesNav";

function describe(c: Concession) {
  const amount = c.kind === "percent" ? `${Number(c.value)}% off` : `${formatMoney(c.value)} off each installment`;
  return `${amount} ${c.fee_head ? c.fee_head_name.toLowerCase() : "all fees"}`;
}

export default function Concessions() {
  const { can } = useAuth();
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "pending";
  const list = useQuery({
    queryKey: ["concessions", status],
    queryFn: () => api.get<Paginated<Concession>>("/fees/concessions/", { status }),
    placeholderData: keepPreviousData,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Fees</h1>
      <FeesNav />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <label className="block space-y-1 text-sm sm:w-64">
            <span className="font-medium">Show</span>
            <NativeSelect value={status} onChange={(e) => setParams({ status: e.target.value }, { replace: true })}>
              {Object.entries(CONCESSION_STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </NativeSelect>
          </label>
          <ErrorNote error={list.error} />
          <ul className="space-y-3">
            {list.data?.results.map((c) => <ConcessionCard key={c.id} concession={c} canDecide={can("fees.approve")} />)}
            {list.data?.results.length === 0 && <li className="rounded-lg border bg-background p-6 text-center text-muted-foreground">Nothing here.</li>}
          </ul>
        </div>
        {can("fees.request_concession") && <RequestForm />}
      </div>
    </div>
  );
}

function ConcessionCard({ concession: c, canDecide }: { concession: Concession; canDecide: boolean }) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const done = () => void queryClient.invalidateQueries({ queryKey: ["concessions"] });
  const decide = useMutation({ mutationFn: (approve: boolean) => api.post(`/fees/concessions/${c.id}/decide/`, { approve, note }), onSuccess: done });
  const cancel = useMutation({ mutationFn: () => api.post(`/fees/concessions/${c.id}/cancel/`, { reason: note || "Cancelled" }), onSuccess: done });

  return (
    <li className="space-y-2 rounded-lg border bg-background p-4 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-medium">
          <Link to={`/staff/students/${c.student}`} className="underline-offset-4 hover:underline">{c.student_name}</Link>{" "}
          <span className="font-normal text-muted-foreground">({c.admission_number}) · {c.session_name}</span>
        </p>
        <span className="text-muted-foreground">{CONCESSION_STATUS_LABELS[c.status]}</span>
      </div>
      <p>{describe(c)}. Reason: {c.reason}</p>
      <p className="text-muted-foreground">
        Asked by {c.requested_by ?? "unknown"} on {formatDateTime(c.requested_at)}
        {c.decided_by && ` · decided by ${c.decided_by} on ${formatDateTime(c.decided_at)}`}
        {c.decision_note && ` · “${c.decision_note}”`}
      </p>
      <ErrorNote error={decide.error ?? cancel.error} />
      {canDecide && (c.status === "pending" || c.status === "approved") && (
        <div className="flex flex-wrap items-end gap-2">
          <Input className="h-9 max-w-xs" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note (optional)" aria-label="Note" />
          {c.status === "pending" && (
            <>
              <Button size="sm" onClick={() => decide.mutate(true)} disabled={decide.isPending}>Approve</Button>
              <Button size="sm" variant="outline" onClick={() => decide.mutate(false)} disabled={decide.isPending}>Reject</Button>
            </>
          )}
          {c.status === "approved" && <Button size="sm" variant="outline" onClick={() => cancel.mutate()} disabled={cancel.isPending}>Withdraw concession</Button>}
        </div>
      )}
    </li>
  );
}

function RequestForm() {
  const queryClient = useQueryClient();
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: () => api.get<Paginated<AcademicSession>>("/academics/sessions/") });
  const heads = useQuery({ queryKey: ["fee-heads"], queryFn: () => api.get<FeeHead[]>("/fees/heads/") });
  const [search, setSearch] = useState("");
  const [picked, setPicked] = useState<StudentListItem | null>(null);
  const students = useQuery({
    queryKey: ["students", "pick", search],
    queryFn: () => api.get<Paginated<StudentListItem>>("/students/", { search, status: "active" }),
    enabled: search.length >= 2 && !picked,
  });
  const currentSession = sessions.data?.results.find((s) => s.is_current)?.id ?? "";
  const empty = { student: "", session: "", fee_head: "all", kind: "percent", value: "", reason: "" };
  const [form, setForm] = useState(empty);
  const save = useMutation({
    mutationFn: () => api.post("/fees/concessions/", { ...form, session: Number(form.session || currentSession), student: Number(form.student), fee_head: form.fee_head === "all" ? null : Number(form.fee_head) }),
    onSuccess: () => {
      setForm(empty);
      setPicked(null);
      setSearch("");
      void queryClient.invalidateQueries({ queryKey: ["concessions"] });
    },
  });
  const errors = save.error instanceof ApiError ? save.error.fieldErrors : {};

  return (
    <Panel title="Ask for a concession">
      <p className="text-sm text-muted-foreground">The principal approves it before it changes any invoice.</p>
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        <Field label="Find student" required hint="Type a name or admission number" error={errors.student}>
          <Input type="search" value={search} onChange={(e) => { setSearch(e.target.value); setPicked(null); setForm({ ...form, student: "" }); }} autoComplete="off" />
        </Field>
        {search.length >= 2 && !picked && (
          <ul className="max-h-48 overflow-y-auto rounded-md border text-sm" aria-label="Matching students">
            {students.data?.results.map((s) => (
              <li key={s.id}>
                <button type="button" className="w-full px-3 py-2 text-left hover:bg-accent" onClick={() => { setPicked(s); setForm({ ...form, student: String(s.id) }); setSearch(`${s.first_name} ${s.last_name} (${s.admission_number})`); }}>
                  {s.first_name} {s.last_name} <span className="text-muted-foreground">({s.admission_number}{s.class_name ? `, ${s.class_name}` : ""})</span>
                </button>
              </li>
            ))}
            {students.data?.results.length === 0 && <li className="px-3 py-2 text-muted-foreground">No match.</li>}
          </ul>
        )}
        <Field label="Session" required error={errors.session}>
          <NativeSelect value={form.session || String(currentSession)} onChange={(e) => setForm({ ...form, session: e.target.value })}>
            {sessions.data?.results.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </NativeSelect>
        </Field>
        <Field label="Applies to" required error={errors.fee_head}>
          <NativeSelect value={form.fee_head} onChange={(e) => setForm({ ...form, fee_head: e.target.value })}>
            <option value="all">All fees</option>
            {heads.data?.filter((h) => h.is_active).map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
          </NativeSelect>
        </Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Type" required error={errors.kind}>
            <NativeSelect value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
              <option value="percent">Percent</option>
              <option value="fixed">Rupees per installment</option>
            </NativeSelect>
          </Field>
          <Field label={form.kind === "percent" ? "Percent" : "Rupees"} required error={errors.value}>
            <Input inputMode="decimal" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} />
          </Field>
        </div>
        <Field label="Reason" required error={errors.reason}>
          <Input value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} placeholder="e.g. Sibling, staff ward, RTE" />
        </Field>
        {save.error && !Object.keys(errors).length && <ErrorNote error={save.error} />}
        <Button type="submit" disabled={save.isPending || !form.student}>Send for approval</Button>
      </form>
    </Panel>
  );
}
