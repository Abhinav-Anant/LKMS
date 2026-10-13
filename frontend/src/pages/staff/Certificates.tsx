import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { Field, NativeSelect } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { TC_STATUS_LABELS, formatDate, formatMoney, todayISO } from "@/lib/labels";
import type { Paginated, StudentListItem, TransferCertificate } from "@/lib/types";
import { openPdf } from "@/pages/staff/fees/receipt";

export default function Certificates() {
  const { can } = useAuth();
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const list = useQuery({
    queryKey: ["tcs", status, search],
    queryFn: () => api.get<Paginated<TransferCertificate>>("/certificates/tc/", { status, search, page_size: 100 }),
  });
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Transfer certificates</h1>
        <p className="text-sm text-muted-foreground">
          The office records a parent's request. The principal issues it, which marks the student as left. Unpaid fees block the TC
          unless the principal gives a reason.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Input aria-label="Search by name, admission number or TC number" placeholder="Search name, adm. no. or TC no." className="h-10 w-72"
          value={search} onChange={(e) => setSearch(e.target.value)} />
        <NativeSelect aria-label="Status" className="h-10 w-56" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All</option>
          {Object.entries(TC_STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </NativeSelect>
      </div>
      <ErrorNote error={list.error} />
      <ul className="space-y-2">
        {list.data?.results.map((tc) => <TcRow key={tc.id} tc={tc} canIssue={can("tc.issue")} />)}
        {list.data?.results.length === 0 && (
          <li className="rounded-lg border bg-background p-6 text-center text-muted-foreground">No transfer certificates.</li>
        )}
      </ul>
      {can("tc.request") && <NewRequest />}
    </div>
  );
}

function TcRow({ tc, canIssue }: { tc: TransferCertificate; canIssue: boolean }) {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"" | "issue" | "cancel">("");
  const [text, setText] = useState("");
  const done = (title: string) => {
    setMode("");
    setText("");
    void queryClient.invalidateQueries({ queryKey: ["tcs"] });
    toast({ title });
  };
  const issue = useMutation({
    mutationFn: () => api.post<TransferCertificate>(`/certificates/tc/${tc.id}/issue/`, { dues_waived_reason: text }),
    onSuccess: (t) => done(`${t.number} issued`),
  });
  const cancel = useMutation({
    mutationFn: () => api.post<TransferCertificate>(`/certificates/tc/${tc.id}/cancel/`, { reason: text }),
    onSuccess: () => done("Cancelled"),
  });
  const pdf = useMutation({ mutationFn: () => openPdf(`/certificates/tc/${tc.id}/pdf/`) });
  const due = Number(tc.current_fees_due);
  const canCancel = tc.status === "requested" || (tc.status === "issued" && canIssue);

  return (
    <li className="space-y-2 rounded-lg border bg-background p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-medium">
            {tc.student_name} <span className="font-normal text-muted-foreground">· Adm. no. {tc.admission_number} · {tc.class_label}</span>
          </p>
          <p className="text-sm text-muted-foreground">
            {tc.number ? `${tc.number} · issued ${formatDate(tc.issued_on)}` : `Requested ${formatDate(tc.application_date)}`}
            {" · "}leaving {formatDate(tc.leaving_date)} · {tc.reason}
          </p>
          {tc.status === "requested" && due > 0 && (
            <p className="text-sm font-medium text-destructive">Unpaid fees: {formatMoney(tc.current_fees_due)}</p>
          )}
          {tc.status === "issued" && tc.dues_waived_reason && (
            <p className="text-sm text-muted-foreground">Issued with {formatMoney(tc.fees_due)} unpaid: {tc.dues_waived_reason}</p>
          )}
          {tc.status === "cancelled" && <p className="text-sm text-muted-foreground">Cancelled: {tc.cancel_reason}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={tc.status === "issued" ? "default" : "outline"}>{TC_STATUS_LABELS[tc.status]}</Badge>
          {tc.number && <Button size="sm" variant="outline" onClick={() => pdf.mutate()} disabled={pdf.isPending}>Print</Button>}
          {tc.status === "requested" && canIssue && (
            <Button size="sm" onClick={() => setMode(mode === "issue" ? "" : "issue")}>Issue</Button>
          )}
          {canCancel && (
            <Button size="sm" variant="ghost" onClick={() => setMode(mode === "cancel" ? "" : "cancel")}>
              {tc.status === "issued" ? "Withdraw" : "Cancel request"}
            </Button>
          )}
        </div>
      </div>
      {mode === "issue" && (
        <div className="flex flex-wrap items-end gap-2 border-t pt-2">
          {due > 0 ? (
            <Field label="Reason to issue with fees unpaid" required className="min-w-72 flex-1">
              <Input value={text} onChange={(e) => setText(e.target.value)} maxLength={200} />
            </Field>
          ) : (
            <p className="text-sm">All fees are paid. Issuing gives the next TC number and marks {tc.student_name} as left.</p>
          )}
          <Button onClick={() => issue.mutate()} disabled={issue.isPending || (due > 0 && !text.trim())}>Confirm and issue</Button>
        </div>
      )}
      {mode === "cancel" && (
        <div className="flex flex-wrap items-end gap-2 border-t pt-2">
          <Field label="Reason" required className="min-w-72 flex-1">
            <Input value={text} onChange={(e) => setText(e.target.value)} maxLength={200} />
          </Field>
          <Button variant="destructive" onClick={() => cancel.mutate()} disabled={cancel.isPending || !text.trim()}>
            {tc.status === "issued" ? "Withdraw TC" : "Cancel request"}
          </Button>
          {tc.status === "issued" && (
            <p className="w-full text-sm text-muted-foreground">The student goes back to studying. The TC number stays used in the register.</p>
          )}
        </div>
      )}
      <ErrorNote error={issue.error ?? cancel.error ?? pdf.error} />
    </li>
  );
}

function NewRequest() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [student, setStudent] = useState<StudentListItem | null>(null);
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const found = useQuery({
    queryKey: ["tc-student-search", search],
    queryFn: () => api.get<Paginated<StudentListItem>>("/students/", { search, status: "active", page_size: 8 }),
    enabled: search.trim().length >= 2 && !student,
  });
  const create = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post<TransferCertificate>("/certificates/tc/", body),
    onSuccess: () => {
      setStudent(null);
      setSearch("");
      setErrors({});
      void queryClient.invalidateQueries({ queryKey: ["tcs"] });
      toast({ title: "TC request recorded. The principal can now issue it." });
    },
    onError: (err) => setErrors(err instanceof ApiError ? err.fieldErrors : {}),
  });
  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!student) return;
    create.mutate({ student: student.id, ...Object.fromEntries(new FormData(e.currentTarget)) });
  }
  return (
    <Panel title="Record a TC request">
      {student ? (
        <p className="text-sm">
          <span className="font-medium">{student.first_name} {student.last_name}</span> · Adm. no. {student.admission_number}
          {student.class_name && ` · ${student.class_name} ${student.section_name ?? ""}`}{" "}
          <Button size="sm" variant="link" onClick={() => setStudent(null)}>Change</Button>
        </p>
      ) : (
        <div className="space-y-2">
          <Field label="Student" required hint="Type at least two letters of the name or the admission number" error={errors.student}>
            <Input value={search} onChange={(e) => setSearch(e.target.value)} />
          </Field>
          {found.data && (
          <ul className="divide-y rounded-md border">
            {found.data?.results.map((s) => (
              <li key={s.id}>
                <button type="button" className="w-full p-2 text-left text-sm hover:bg-accent" onClick={() => setStudent(s)}>
                  {s.first_name} {s.last_name} · {s.admission_number} {s.class_name ? `· ${s.class_name} ${s.section_name ?? ""}` : ""}
                </button>
              </li>
            ))}
            {found.data?.results.length === 0 && <li className="p-2 text-sm text-muted-foreground">No studying student matches.</li>}
          </ul>
          )}
        </div>
      )}
      {student && (
        <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
          <Field label="Date the parent asked" required error={errors.application_date}>
            <Input name="application_date" type="date" defaultValue={todayISO()} />
          </Field>
          <Field label="Last day at school" required error={errors.leaving_date}>
            <Input name="leaving_date" type="date" defaultValue={todayISO()} />
          </Field>
          <Field label="Reason for leaving" required error={errors.reason}>
            <Input name="reason" maxLength={200} />
          </Field>
          <Field label="Result of the last exam" hint="e.g. Passed Class 3, promoted to Class 4" error={errors.last_exam_result}>
            <Input name="last_exam_result" maxLength={200} />
          </Field>
          <Field label="Conduct" required error={errors.conduct}>
            <Input name="conduct" maxLength={50} defaultValue="Good" />
          </Field>
          <Field label="Other remarks" error={errors.remarks}>
            <Input name="remarks" maxLength={300} />
          </Field>
          <div className="sm:col-span-2">
            <ErrorNote error={create.error} />
            <Button type="submit" disabled={create.isPending}>Record request</Button>
          </div>
        </form>
      )}
    </Panel>
  );
}
