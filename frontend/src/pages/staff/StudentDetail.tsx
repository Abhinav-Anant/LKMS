import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { OneTimeSecret } from "@/components/OneTimeSecret";
import { ErrorNote } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, fetchFileUrl } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CATEGORIES, ENROLLMENT_STATUS_LABELS, GENDERS, RELATIONSHIPS, STUDENT_STATUS_LABELS, formatDate, formatDateTime } from "@/lib/labels";
import type { StudentDetail as Detail, IssuedCode } from "@/lib/types";

export default function StudentDetail() {
  const { id } = useParams();
  const { can } = useAuth();
  const student = useQuery({ queryKey: ["student", id], queryFn: () => api.get<Detail>(`/students/${id}/`) });

  if (student.isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (student.isError || !student.data) {
    return <p className="text-destructive">Could not load this student{student.error ? `: ${student.error.message}` : "."}</p>;
  }
  const s = student.data;

  return (
    <div className="space-y-4">
      <Link to="/staff/students" className="text-sm text-primary underline-offset-4 hover:underline">
        Back to students
      </Link>
      <div className="flex flex-wrap items-start gap-4">
        <Photo student={s} />
        <div className="space-y-1">
          <h1 className="text-2xl font-bold">{s.first_name} {s.last_name}</h1>
          <p className="text-sm text-muted-foreground">
            Admission no. <span className="font-mono text-foreground">{s.admission_number}</span> · admitted {formatDate(s.admission_date)}
            {s.admitted_in_class_name && ` in ${s.admitted_in_class_name}`}
          </p>
          <p className="text-sm">{STUDENT_STATUS_LABELS[s.status] ?? s.status}</p>
          {can("fees.view") && (
            <Link to={`/staff/fees?student=${s.id}`} className="mr-4 text-sm text-primary underline-offset-4 hover:underline">
              Fees
            </Link>
          )}
          {s.application && (
            <Link to={`/staff/applications/${s.application}`} className="text-sm text-primary underline-offset-4 hover:underline">
              View admission application
            </Link>
          )}
        </div>
      </div>

      <Panel title="Class history">
        {s.enrollments.length === 0 ? (
          <p className="text-sm text-muted-foreground">Not enrolled in any session.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Session</TableHead>
                <TableHead scope="col">Class</TableHead>
                <TableHead scope="col">Roll no.</TableHead>
                <TableHead scope="col">Since</TableHead>
                <TableHead scope="col">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {s.enrollments.map((e) => (
                <TableRow key={e.id}>
                  <TableCell>{e.session_name}</TableCell>
                  <TableCell>{e.class_name} {e.section_name}</TableCell>
                  <TableCell>{e.roll_number ?? "Not set"}</TableCell>
                  <TableCell>{formatDate(e.enrolled_on)}</TableCell>
                  <TableCell>{ENROLLMENT_STATUS_LABELS[e.status] ?? e.status}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Panel>

      <Panel title="Parents and guardians">
        <div className="grid gap-4 sm:grid-cols-2">
          {s.guardians.map((g) => (
            <div key={g.id} className="rounded-md border p-3">
              <h3 className="text-sm font-semibold">
                {RELATIONSHIPS[g.relationship] ?? g.relationship}
                {g.relationship_detail && ` (${g.relationship_detail})`}
                {g.is_primary_contact && <span className="ml-2 font-normal text-muted-foreground">main contact</span>}
              </h3>
              <Rows
                rows={[
                  ["Name", g.guardian.full_name],
                  ["Mobile", g.guardian.phone],
                  ["Other phone", g.guardian.alternate_phone],
                  ["Email", g.guardian.email],
                  ["Occupation", g.guardian.occupation],
                  ["Education", g.guardian.qualification],
                ]}
              />
              {can("students.edit") && s.status === "active" && g.guardian.phone && <ParentCodeButton phone={g.guardian.phone} />}
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Details">
        <Rows
          rows={[
            ["Date of birth", formatDate(s.date_of_birth)],
            ["Gender", GENDERS.find((g) => g.value === s.gender)?.label],
            ["Category", CATEGORIES.find((c) => c.value === s.category)?.label],
            ["Religion", s.religion],
            ["Mother tongue", s.mother_tongue],
            ["Nationality", s.nationality],
            ["Blood group", s.blood_group],
            ["Aadhaar", s.aadhaar_number],
            ["Address", [s.address_line, s.city, s.district, s.state, s.pincode].filter(Boolean).join(", ")],
            ["Previous school", s.previous_school],
          ]}
        />
      </Panel>
    </div>
  );
}

function Photo({ student }: { student: Detail }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!student.has_photo) return;
    let objectUrl: string | null = null;
    let cancelled = false;
    fetchFileUrl(`/students/${student.id}/photo/`)
      .then((u) => {
        objectUrl = u;
        if (!cancelled) setUrl(u);
      })
      .catch(() => setUrl(null));
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [student.id, student.has_photo]);

  const box = "h-32 w-24 rounded-md border bg-muted object-cover";
  if (!url) return <div className={`${box} flex items-center justify-center text-xs text-muted-foreground`}>No photo</div>;
  return <img src={url} alt={`Photo of ${student.first_name}`} className={box} />;
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3 rounded-lg border bg-background p-4" aria-label={title}>
      <h2 className="font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function Rows({ rows }: { rows: [string, string | null | undefined][] }) {
  return (
    <dl className="space-y-1 text-sm">
      {rows
        .filter(([, v]) => v)
        .map(([k, v]) => (
          <div key={k} className="grid grid-cols-[9rem_1fr] gap-2">
            <dt className="text-muted-foreground">{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
    </dl>
  );
}

/** Issue a one-time parent portal sign-in code, for parents who can't receive one on WhatsApp yet. */
function ParentCodeButton({ phone }: { phone: string }) {
  const [issued, setIssued] = useState<IssuedCode | null>(null);
  const issue = useMutation({
    mutationFn: () => api.post<IssuedCode>("/auth/parent/issue-code/", { phone }),
    onSuccess: setIssued,
  });
  if (issued)
    return (
      <div className="mt-3">
        <OneTimeSecret title="Parent portal sign-in code" value={issued.code} onDone={() => setIssued(null)}>
          <p className="text-sm">
            Valid until {formatDateTime(issued.expires_at)} for mobile {issued.phone}. The parent opens the Parents page, chooses
            "I already have a code" and signs in. They will see: {issued.children.join(", ")}.
          </p>
        </OneTimeSecret>
      </div>
    );
  return (
    <div className="mt-3 space-y-1">
      <Button variant="outline" size="sm" disabled={issue.isPending}
        onClick={() => window.confirm(`Create a parent portal sign-in code for ${phone}? Any earlier unused code stops working.`) && issue.mutate()}>
        Parent sign-in code
      </Button>
      <ErrorNote error={issue.error} />
    </div>
  );
}
