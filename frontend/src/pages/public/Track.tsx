import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { CaptchaGate } from "@/components/CaptchaGate";
import { Field } from "@/components/Field";
import { StatusBadge, VerificationBadge } from "@/components/StatusBadge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { formatDate } from "@/lib/labels";
import type { TrackResult } from "@/lib/types";

export default function Track() {
  const [result, setResult] = useState<TrackResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [captcha, setCaptcha] = useState<string | null>(null);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    const data = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      setResult(
        await api.post<TrackResult>(
          "/admissions/public/track/",
          {
            application_number: String(data.get("application_number")).trim().toUpperCase(),
            date_of_birth: data.get("date_of_birth"),
            phone: data.get("phone"),
            captcha,
          },
          { auth: false },
        ),
      );
    } catch (err) {
      setResult(null);
      setCaptcha(null); // each check uses up the pass
      setError(
        err instanceof ApiError && err.status === 404
          ? "No application matches these details. Check the application number, the child's date of birth and the mobile number given on the form."
          : err instanceof ApiError && err.status === 429
            ? "Too many attempts. Please try again in an hour."
            : err instanceof ApiError && err.fieldErrors.captcha
              ? "Please type the letters from the picture again."
              : "Something went wrong. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h1 className="text-2xl font-bold">Track your application</h1>
      <CaptchaGate pass={captcha} onPass={setCaptcha}>
      <form onSubmit={submit} className="space-y-4" method="post">
        <Field label="Application number" required hint="For example LK-2027-28-00012">
          <Input name="application_number" autoCapitalize="characters" autoCorrect="off" spellCheck={false} autoComplete="off" />
        </Field>
        <Field label="Child's date of birth" required>
          <Input name="date_of_birth" type="date" />
        </Field>
        <Field label="Mobile number given on the form" required>
          <Input name="phone" type="tel" inputMode="tel" autoComplete="tel-national" maxLength={14} />
        </Field>
        <Button type="submit" disabled={busy}>
          {busy ? "Checking…" : "Check status"}
        </Button>
      </form>
      </CaptchaGate>

      <div aria-live="polite">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {result && (
          <section className="space-y-4 rounded-lg border p-5" aria-labelledby="result-heading">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 id="result-heading" className="text-lg font-semibold">
                {result.child_first_name}, {result.class_applied} ({result.session})
              </h2>
              <StatusBadge status={result.status} />
            </div>
            <p className="text-sm text-muted-foreground">
              {result.application_number} · submitted {formatDate(result.submitted_at)}
            </p>
            {result.message && <p className="rounded-md bg-muted p-3">{result.message}</p>}
            {result.documents.length > 0 && (
              <div>
                <h3 className="mb-2 font-medium">Documents</h3>
                <ul className="space-y-2">
                  {result.documents.map((d) => (
                    <li key={d.document_type} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                      <span>{d.document_type_name}</span>
                      <span className="flex items-center gap-2">
                        <VerificationBadge value={d.verification} />
                        {d.verification_note && <span className="text-destructive">{d.verification_note}</span>}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {result.documents_still_needed.length > 0 &&
              ["submitted", "under_review", "documents_requested"].includes(result.status) && (
                <p className="text-sm">
                  Still to be uploaded or checked: {result.documents_still_needed.join(", ")}. Upload them with the access code
                  you got when applying, or bring them to the school office.
                </p>
              )}
          </section>
        )}
      </div>
      <p className="text-sm text-muted-foreground">
        Haven't applied yet? <Link to="/#admissions" className="underline">Start an application</Link>.
      </p>
    </div>
  );
}
