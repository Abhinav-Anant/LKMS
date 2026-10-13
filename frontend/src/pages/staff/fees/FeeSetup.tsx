import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";

import { Field, NativeSelect } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, formatMoney } from "@/lib/labels";
import type { AcademicSession, FeeAmount, FeeHead, Installment, Paginated, SchoolClass } from "@/lib/types";

import { FeesNav } from "./FeesNav";

export default function FeeSetup() {
  const { can } = useAuth();
  const [params, setParams] = useSearchParams();
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: () => api.get<Paginated<AcademicSession>>("/academics/sessions/") });
  const currentId = sessions.data?.results.find((s) => s.is_current)?.id;
  const sessionId = params.get("session") ?? (currentId ? String(currentId) : "");
  const installments = useQuery({
    queryKey: ["installments", sessionId],
    queryFn: () => api.get<Installment[]>("/fees/installments/", { session: sessionId }),
    enabled: Boolean(sessionId),
  });
  const installmentId = params.get("installment") ?? (installments.data?.[0] ? String(installments.data[0].id) : "");
  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    next.set(key, value);
    if (key === "session") next.delete("installment");
    setParams(next, { replace: true });
  };

  if (!can("fees.manage")) return <Navigate to="/staff/fees" replace />;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Fees</h1>
      <FeesNav />
      <p className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
        The fee heads, installments and amounts loaded at set-up are samples. Replace them with the school's real fee structure before creating invoices.
      </p>
      <div className="flex flex-wrap items-end gap-4">
        <label className="space-y-1 text-sm">
          <span className="font-medium">Session</span>
          <NativeSelect value={sessionId} onChange={(e) => set("session", e.target.value)} className="w-48">
            {sessions.data?.results.map((s) => <option key={s.id} value={s.id}>{s.name}{s.is_current ? " (current)" : ""}</option>)}
          </NativeSelect>
        </label>
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {installmentId && <AmountGrid installmentId={installmentId} installments={installments.data ?? []} onPick={(id) => set("installment", id)} />}
          {installmentId && <Generate installmentId={installmentId} />}
        </div>
        <aside className="space-y-6">
          {sessionId && <Installments sessionId={sessionId} installments={installments.data ?? []} />}
          <Heads />
        </aside>
      </div>
    </div>
  );
}

function AmountGrid({ installmentId, installments, onPick }: { installmentId: string; installments: Installment[]; onPick: (id: string) => void }) {
  const queryClient = useQueryClient();
  const heads = useQuery({ queryKey: ["fee-heads"], queryFn: () => api.get<FeeHead[]>("/fees/heads/") });
  const classes = useQuery({ queryKey: ["classes"], queryFn: () => api.get<Paginated<SchoolClass>>("/academics/classes/") });
  const amounts = useQuery({ queryKey: ["fee-amounts", installmentId], queryFn: () => api.get<FeeAmount[]>("/fees/amounts/", { installment: installmentId }) });
  const [grid, setGrid] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const next: Record<string, string> = {};
    for (const a of amounts.data ?? []) next[`${a.school_class}:${a.fee_head}`] = String(Number(a.amount));
    setGrid(next);
    setSaved(false);
  }, [amounts.data]);

  const activeHeads = (heads.data ?? []).filter((h) => h.is_active);
  const activeClasses = (classes.data?.results ?? []).filter((c) => c.is_active);
  const save = useMutation({
    mutationFn: () =>
      api.post("/fees/amounts/bulk/", {
        installment: Number(installmentId),
        amounts: activeClasses.flatMap((c) => activeHeads.map((h) => ({ school_class: c.id, fee_head: h.id, amount: grid[`${c.id}:${h.id}`] || "0" }))),
      }),
    onSuccess: () => {
      setSaved(true);
      void queryClient.invalidateQueries({ queryKey: ["fee-amounts", installmentId] });
    },
  });
  const total = (classId: number) => activeHeads.reduce((sum, h) => sum + (Number(grid[`${classId}:${h.id}`]) || 0), 0);

  return (
    <Panel
      title="Fee amounts by class"
      actions={
        <NativeSelect aria-label="Installment" value={installmentId} onChange={(e) => onPick(e.target.value)} className="h-9 w-72">
          {installments.map((i) => <option key={i.id} value={i.id}>{i.name} · due {formatDate(i.due_date)}</option>)}
        </NativeSelect>
      }
    >
      <p className="text-sm text-muted-foreground">Leave a box empty or 0 if that class does not pay the head in this installment.</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left">
              <th scope="col" className="py-2 pr-3 font-medium">Class</th>
              {activeHeads.map((h) => <th key={h.id} scope="col" className="px-1 py-2 font-medium">{h.name}{h.new_students_only && <span className="block text-xs font-normal text-muted-foreground">new students only</span>}</th>)}
              <th scope="col" className="py-2 pl-3 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {activeClasses.map((c) => (
              <tr key={c.id} className="border-b last:border-0">
                <th scope="row" className="py-1 pr-3 text-left font-normal">{c.name}</th>
                {activeHeads.map((h) => (
                  <td key={h.id} className="px-1 py-1">
                    <Input
                      inputMode="decimal"
                      aria-label={`${h.name} for ${c.name}`}
                      className="h-9 w-28 text-right tabular-nums"
                      value={grid[`${c.id}:${h.id}`] ?? ""}
                      onChange={(e) => { setSaved(false); setGrid({ ...grid, [`${c.id}:${h.id}`]: e.target.value.replace(/[^\d.]/g, "") }); }}
                    />
                  </td>
                ))}
                <td className="py-1 pl-3 text-right tabular-nums">{formatMoney(total(c.id))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ErrorNote error={save.error} />
      <div className="flex items-center gap-3">
        <Button onClick={() => save.mutate()} disabled={save.isPending}>{save.isPending ? "Saving…" : "Save amounts"}</Button>
        {saved && <span role="status" className="text-sm text-emerald-700">Saved.</span>}
      </div>
    </Panel>
  );
}

function Generate({ installmentId }: { installmentId: string }) {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<{ created: number; skipped_existing: number; skipped_no_fees: number } | null>(null);
  const run = useMutation({
    mutationFn: () => api.post<{ created: number; skipped_existing: number; skipped_no_fees: number }>("/fees/invoices/generate/", { installment: Number(installmentId) }),
    onSuccess: (data) => {
      setResult(data);
      void queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
  });
  return (
    <Panel title="Create invoices">
      <p className="text-sm text-muted-foreground">
        Creates one invoice for every student studying this session, using the amounts above and any approved concessions.
        Running it again only adds students who do not have an invoice yet. Amounts cannot be changed once invoices exist.
      </p>
      <ErrorNote error={run.error} />
      {result && (
        <p role="status" className="text-sm">
          Created {result.created} invoices. {result.skipped_existing > 0 && `${result.skipped_existing} students already had one. `}
          {result.skipped_no_fees > 0 && `${result.skipped_no_fees} students had no fees set for their class.`}
        </p>
      )}
      <Button variant="outline" onClick={() => run.mutate()} disabled={run.isPending}>{run.isPending ? "Creating…" : "Create invoices for this installment"}</Button>
    </Panel>
  );
}

function Installments({ sessionId, installments }: { sessionId: string; installments: Installment[] }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", due_date: "" });
  const add = useMutation({
    mutationFn: () => api.post("/fees/installments/", { ...form, session: Number(sessionId), order: installments.length + 1 }),
    onSuccess: () => {
      setForm({ name: "", due_date: "" });
      void queryClient.invalidateQueries({ queryKey: ["installments"] });
    },
  });
  const errors = add.error instanceof ApiError ? add.error.fieldErrors : {};
  return (
    <Panel title="Installments">
      <ul className="space-y-1 text-sm">
        {installments.map((i) => <li key={i.id} className="flex justify-between"><span>{i.name}</span><span className="text-muted-foreground">due {formatDate(i.due_date)}</span></li>)}
        {installments.length === 0 && <li className="text-muted-foreground">None yet.</li>}
      </ul>
      <form className="space-y-2 border-t pt-3" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <Field label="Name" required error={errors.name}><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Quarter 1" /></Field>
        <Field label="Due date" required error={errors.due_date}><Input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} /></Field>
        <Button type="submit" variant="outline" size="sm" disabled={add.isPending}>Add installment</Button>
      </form>
    </Panel>
  );
}

function Heads() {
  const queryClient = useQueryClient();
  const heads = useQuery({ queryKey: ["fee-heads"], queryFn: () => api.get<FeeHead[]>("/fees/heads/") });
  const [form, setForm] = useState({ name: "", code: "", new_students_only: false });
  const order = useMemo(() => (heads.data?.length ?? 0) + 1, [heads.data]);
  const add = useMutation({
    mutationFn: () => api.post("/fees/heads/", { ...form, order }),
    onSuccess: () => {
      setForm({ name: "", code: "", new_students_only: false });
      void queryClient.invalidateQueries({ queryKey: ["fee-heads"] });
    },
  });
  const toggle = useMutation({
    mutationFn: (h: FeeHead) => api.patch(`/fees/heads/${h.id}/`, { is_active: !h.is_active }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["fee-heads"] }),
  });
  const errors = add.error instanceof ApiError ? add.error.fieldErrors : {};
  return (
    <Panel title="Fee heads">
      <ul className="space-y-1 text-sm">
        {heads.data?.map((h) => (
          <li key={h.id} className="flex items-center justify-between gap-2">
            <span className={h.is_active ? "" : "text-muted-foreground line-through"}>{h.name}{h.new_students_only && " (new students)"}</span>
            <button type="button" className="text-xs text-primary underline" onClick={() => toggle.mutate(h)}>{h.is_active ? "Stop using" : "Use again"}</button>
          </li>
        ))}
      </ul>
      <form className="space-y-2 border-t pt-3" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <Field label="Name" required error={errors.name}>
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value, code: e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 30) })} placeholder="e.g. Transport fee" />
        </Field>
        {errors.code && <p className="text-sm text-destructive">{errors.code.join(" ")}</p>}
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="h-4 w-4" checked={form.new_students_only} onChange={(e) => setForm({ ...form, new_students_only: e.target.checked })} />
          Charge only to newly admitted students
        </label>
        <Button type="submit" variant="outline" size="sm" disabled={add.isPending || !form.name}>Add fee head</Button>
      </form>
    </Panel>
  );
}
