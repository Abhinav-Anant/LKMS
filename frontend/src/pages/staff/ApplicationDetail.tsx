import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { DocumentUploader } from "@/components/DocumentUploader";
import { Field, NativeSelect } from "@/components/Field";
import { StatusBadge, VerificationBadge } from "@/components/StatusBadge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api, fetchFileUrl } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CATEGORIES, GENDERS, RELATIONSHIPS, STATUS_LABELS, formatBytes, formatDate, formatDateTime } from "@/lib/labels";
import type { ApplicationDetail as Detail, ApplicationDocument, DocumentType, Paginated, Section, StudentDetail } from "@/lib/types";

const OPEN = ["submitted", "under_review", "documents_requested"];

export default function ApplicationDetail() {
  const { id } = useParams();
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const query = useQuery({ queryKey: ["application", id], queryFn: () => api.get<Detail>(`/admissions/applications/${id}/`) });

  const refresh = (data?: Detail) => {
    if (data) queryClient.setQueryData(["application", id], data);
    else void queryClient.invalidateQueries({ queryKey: ["application", id] });
    void queryClient.invalidateQueries({ queryKey: ["applications"] });
  };
  const onError = (err: unknown) => setError(err instanceof ApiError ? err.message : "Something went wrong.");

  if (query.isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (query.isError || !query.data) return <p role="alert">This application could not be loaded.</p>;
  const app = query.data;
  const isOpen = OPEN.includes(app.status);

  return (
    <div className="space-y-6">
      <div>
        <Link to="/staff/applications" className="text-sm text-muted-foreground underline-offset-4 hover:underline">← All applications</Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold">{`${app.first_name} ${app.last_name}`.trim()}</h1>
          <StatusBadge status={app.status} />
        </div>
        <p className="text-sm text-muted-foreground">
          <span className="font-mono">{app.application_number}</span> · {app.class_name} · {app.session_name} · submitted {formatDateTime(app.submitted_at)}
        </p>
      </div>

      {error && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {app.status_message && (
        <p className="rounded-md border bg-background p-3 text-sm">
          <span className="font-medium">Message shown to parent: </span>{app.status_message}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Documents app={app} canReview={can("admissions.review") && isOpen} onChanged={() => { setError(""); refresh(); }} onError={onError} />
          <Details app={app} />
        </div>
        <aside className="space-y-6">
          {app.student_id && (
            <Panel title="Student record">
              <Link to={`/staff/students/${app.student_id}`} className="text-primary underline">Open student record</Link>
            </Panel>
          )}
          <Actions app={app} onDone={(d) => { setError(""); refresh(d); }} onError={onError} />
          <Panel title="History">
            <ol className="space-y-3 text-sm">
              {app.history.map((h, i) => (
                <li key={i}>
                  <p className="font-medium">{STATUS_LABELS[h.to_status]}</p>
                  <p className="text-muted-foreground">{formatDateTime(h.created_at)}{h.changed_by ? ` · ${h.changed_by}` : " · parent"}</p>
                  {h.message && <p>{h.message}</p>}
                </li>
              ))}
            </ol>
          </Panel>
        </aside>
      </div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3 rounded-lg border bg-background p-4" aria-label={title}>
      <h2 className="font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function Documents({ app, canReview, onChanged, onError }: { app: Detail; canReview: boolean; onChanged: () => void; onError: (e: unknown) => void }) {
  const current = app.documents.filter((d) => d.is_current);
  const [showUpload, setShowUpload] = useState(false);
  const types = useQuery({
    queryKey: ["document-types"],
    queryFn: () => api.get<Paginated<DocumentType>>("/admissions/document-types/"),
    enabled: showUpload,
  });

  return (
    <Panel title="Documents">
      {app.missing_documents.length > 0 && (
        <p className="text-sm text-warning">
          Needed before approval: {app.missing_documents.join(", ")}
        </p>
      )}
      {current.length === 0 && <p className="text-sm text-muted-foreground">No documents uploaded yet.</p>}
      <ul className="divide-y">
        {current.map((doc) => (
          <DocumentRow key={doc.id} doc={doc} canReview={canReview} onChanged={onChanged} onError={onError} />
        ))}
      </ul>
      {canReview && (
        <div>
          <Button variant="outline" size="sm" onClick={() => setShowUpload((s) => !s)} aria-expanded={showUpload}>
            {showUpload ? "Hide upload" : "Upload for parent"}
          </Button>
          {showUpload && types.data && (
            <div className="mt-3">
              <DocumentUploader
                documentTypes={types.data.results}
                uploaded={{}}
                uploadPath={`/admissions/applications/${app.id}/documents/`}
                onUploaded={onChanged}
              />
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}

function DocumentRow({ doc, canReview, onChanged, onError }: { doc: ApplicationDocument; canReview: boolean; onChanged: () => void; onError: (e: unknown) => void }) {
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState("");
  const verify = useMutation({
    mutationFn: (body: { verification: "verified" | "rejected"; note?: string }) => api.post(`/admissions/documents/${doc.id}/verify/`, body),
    onSuccess: () => { setRejecting(false); setNote(""); onChanged(); },
    onError,
  });

  async function view() {
    // Open the window first so pop-up blockers allow it, then load the protected file into it.
    const win = window.open("", "_blank");
    try {
      const url = await fetchFileUrl(`/admissions/documents/${doc.id}/file/`);
      if (win) win.location.href = url;
      else window.location.href = url;
    } catch (err) {
      win?.close();
      onError(err);
    }
  }

  return (
    <li className="space-y-2 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-medium">{doc.document_type_name}</p>
          <p className="text-xs text-muted-foreground">
            {doc.content_type === "application/pdf" ? "PDF" : "Image"} · {formatBytes(doc.size)} · uploaded {formatDateTime(doc.uploaded_at)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <VerificationBadge value={doc.verification} />
          <Button variant="outline" size="sm" onClick={() => void view()}>View<span className="sr-only"> {doc.document_type_name}</span></Button>
          {canReview && doc.verification !== "verified" && (
            <Button size="sm" disabled={verify.isPending} onClick={() => verify.mutate({ verification: "verified" })}>
              Verify<span className="sr-only"> {doc.document_type_name}</span>
            </Button>
          )}
          {canReview && doc.verification !== "rejected" && (
            <Button variant="outline" size="sm" onClick={() => setRejecting((r) => !r)} aria-expanded={rejecting}>
              Not acceptable<span className="sr-only">: {doc.document_type_name}</span>
            </Button>
          )}
        </div>
      </div>
      {doc.verification_note && <p className="text-sm text-destructive">{doc.verification_note}</p>}
      {rejecting && (
        <form
          className="flex flex-col gap-2 sm:flex-row sm:items-end"
          onSubmit={(e) => { e.preventDefault(); verify.mutate({ verification: "rejected", note }); }}
        >
          <Field label="Reason (the parent will see this)" required className="flex-1">
            <Input value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} />
          </Field>
          <Button type="submit" variant="destructive" disabled={verify.isPending}>Mark not acceptable</Button>
        </form>
      )}
    </li>
  );
}

function Actions({ app, onDone, onError }: { app: Detail; onDone: (d?: Detail) => void; onError: (e: unknown) => void }) {
  const { can } = useAuth();
  const [mode, setMode] = useState<"" | "documents_requested" | "rejected" | "withdrawn" | "admit">("");
  const [message, setMessage] = useState("");
  const transition = useMutation({
    mutationFn: (body: { status: string; message?: string }) => api.post<Detail>(`/admissions/applications/${app.id}/transition/`, body),
    onSuccess: (d) => { setMode(""); setMessage(""); onDone(d); },
    onError,
  });
  const approve = useMutation({
    mutationFn: () => api.post<Detail>(`/admissions/applications/${app.id}/approve/`, {}),
    onSuccess: (d) => onDone(d),
    onError,
  });

  const isOpen = OPEN.includes(app.status);
  const review = can("admissions.review");
  const decide = can("admissions.decide");
  if (!(isOpen || app.status === "approved") || !(review || decide)) return null;

  function submitMessage(e: FormEvent) {
    e.preventDefault();
    transition.mutate({ status: mode, message });
  }

  const messageLabel: Record<string, string> = {
    documents_requested: "What should the parent upload or correct?",
    rejected: "Reason for rejection (the parent will see this)",
    withdrawn: "Note (optional)",
  };

  return (
    <Panel title="Actions">
      <div className="flex flex-col gap-2">
        {review && app.status === "submitted" && (
          <Button variant="outline" disabled={transition.isPending} onClick={() => transition.mutate({ status: "under_review" })}>Start review</Button>
        )}
        {review && isOpen && app.status !== "documents_requested" && (
          <Button variant="outline" onClick={() => setMode("documents_requested")}>Ask parent for documents</Button>
        )}
        {review && app.status === "documents_requested" && (
          <Button variant="outline" disabled={transition.isPending} onClick={() => transition.mutate({ status: "under_review" })}>Back to review</Button>
        )}
        {decide && isOpen && (
          <Button disabled={approve.isPending || app.missing_documents.length > 0} onClick={() => approve.mutate()}
            aria-describedby={app.missing_documents.length ? "approve-hint" : undefined}>
            Approve
          </Button>
        )}
        {decide && isOpen && app.missing_documents.length > 0 && (
          <p id="approve-hint" className="text-xs text-muted-foreground">Verify all required documents to approve.</p>
        )}
        {decide && app.status === "approved" && <Button onClick={() => setMode("admit")}>Admit and assign section</Button>}
        {decide && <Button variant="outline" className="text-destructive" onClick={() => setMode("rejected")}>Reject</Button>}
        {review && <Button variant="ghost" onClick={() => setMode("withdrawn")}>Mark withdrawn</Button>}
      </div>

      {mode && mode !== "admit" && (
        <form onSubmit={submitMessage} className="space-y-3 border-t pt-3">
          <Field label={messageLabel[mode]} required={mode !== "withdrawn"}>
            <Textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} maxLength={1000} />
          </Field>
          <div className="flex gap-2">
            <Button type="submit" variant={mode === "rejected" ? "destructive" : "default"} disabled={transition.isPending}>
              {mode === "documents_requested" ? "Send request" : mode === "rejected" ? "Reject application" : "Mark withdrawn"}
            </Button>
            <Button type="button" variant="ghost" onClick={() => setMode("")}>Cancel</Button>
          </div>
        </form>
      )}
      {mode === "admit" && <AdmitForm app={app} onCancel={() => setMode("")} onDone={() => { setMode(""); onDone(); }} onError={onError} />}
    </Panel>
  );
}

function AdmitForm({ app, onCancel, onDone, onError }: { app: Detail; onCancel: () => void; onDone: () => void; onError: (e: unknown) => void }) {
  const sections = useQuery({
    queryKey: ["sections", app.session, app.class_applied],
    queryFn: () => api.get<Paginated<Section>>("/academics/sections/", { session: app.session, school_class: app.class_applied }),
  });
  const [section, setSection] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [result, setResult] = useState<StudentDetail | null>(null);
  const admit = useMutation({
    mutationFn: () => api.post<StudentDetail>(`/admissions/applications/${app.id}/admit/`, { section: Number(section), admission_date: date }),
    onSuccess: (student) => { setResult(student); onDone(); },
    onError,
  });

  if (result) {
    return (
      <Alert>
        <AlertDescription>
          Admitted with admission number <strong>{result.admission_number}</strong>.
        </AlertDescription>
      </Alert>
    );
  }
  return (
    <form className="space-y-3 border-t pt-3" onSubmit={(e) => { e.preventDefault(); admit.mutate(); }}>
      <Field label="Section" required>
        <NativeSelect value={section} onChange={(e) => setSection(e.target.value)}>
          <option value="">Choose…</option>
          {sections.data?.results.map((s) => (
            <option key={s.id} value={s.id} disabled={s.strength >= s.capacity}>
              {s.class_name} {s.name} ({s.strength}/{s.capacity})
            </option>
          ))}
        </NativeSelect>
      </Field>
      <Field label="Admission date" required>
        <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </Field>
      <p className="text-xs text-muted-foreground">This creates the student record and takes the next number in the admission register.</p>
      <div className="flex gap-2">
        <Button type="submit" disabled={admit.isPending}>Admit student</Button>
        <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  );
}

function Details({ app }: { app: Detail }) {
  const gender = GENDERS.find((g) => g.value === app.gender)?.label;
  const category = CATEGORIES.find((c) => c.value === app.category)?.label;
  const groups: [string, [string, string | null | undefined][]][] = [
    ["Child", [
      ["Date of birth", formatDate(app.date_of_birth)], ["Gender", gender], ["Category", category],
      ["Religion", app.religion], ["Mother tongue", app.mother_tongue], ["Blood group", app.blood_group],
      ["Aadhaar", app.aadhaar_number], ["Previous school", [app.previous_school, app.previous_class].filter(Boolean).join(", ")],
      ["Sibling admission no.", app.sibling_admission_number],
    ]],
    ["Address", [["Address", [app.address_line, app.city, app.district, app.state, app.pincode].filter(Boolean).join(", ")]]],
    ["Father", [["Name", app.father_name], ["Mobile", app.father_phone], ["Email", app.father_email], ["Occupation", app.father_occupation], ["Education", app.father_qualification]]],
    ["Mother", [["Name", app.mother_name], ["Mobile", app.mother_phone], ["Email", app.mother_email], ["Occupation", app.mother_occupation], ["Education", app.mother_qualification]]],
    ["Guardian", [["Name", app.guardian_name], ["Relationship", app.guardian_relationship], ["Mobile", app.guardian_phone], ["Email", app.guardian_email]]],
    ["Contact and consent", [["Main contact", RELATIONSHIPS[app.primary_contact]], ["Consent given", formatDateTime(app.consent_given_at)]]],
  ];
  return (
    <Panel title="Application details">
      <div className="grid gap-6 sm:grid-cols-2">
        {groups.map(([title, rows]) => {
          const filled = rows.filter(([, v]) => v);
          if (!filled.length) return null;
          return (
            <div key={title}>
              <h3 className="mb-2 text-sm font-semibold text-muted-foreground">{title}</h3>
              <dl className="space-y-1 text-sm">
                {filled.map(([k, v]) => (
                  <div key={k} className="grid grid-cols-[9rem_1fr] gap-2">
                    <dt className="text-muted-foreground">{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
