import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { CaptchaGate } from "@/components/CaptchaGate";
import { DocumentUploader, type UploadedState } from "@/components/DocumentUploader";
import { Field, NativeSelect } from "@/components/Field";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { BLOOD_GROUPS, CATEGORIES, GENDERS, RELATIONSHIPS, formatDate } from "@/lib/labels";
import { useSchool } from "@/lib/school";
import type { AcademicSession, ApplicationForm, DocumentType, SchoolClass } from "@/lib/types";

const STEPS = ["Child", "Address", "Parents", "Review", "Documents"] as const;

// Which step each server-side field error belongs to, so we can send the parent back to it.
const FIELD_STEP: Record<string, number> = {
  session: 0, class_applied: 0, first_name: 0, last_name: 0, date_of_birth: 0, gender: 0, category: 0,
  religion: 0, mother_tongue: 0, nationality: 0, blood_group: 0, aadhaar_number: 0, previous_school: 0,
  previous_class: 0, sibling_admission_number: 0,
  address_line: 1, city: 1, district: 1, state: 1, pincode: 1,
};

const EMPTY: ApplicationForm = {
  session: "", class_applied: "", first_name: "", last_name: "", date_of_birth: "", gender: "",
  category: "general", religion: "", mother_tongue: "", nationality: "Indian", blood_group: "",
  aadhaar_number: "", previous_school: "", previous_class: "", sibling_admission_number: "",
  address_line: "", city: "", district: "", state: "", pincode: "",
  father_name: "", father_phone: "", father_email: "", father_occupation: "", father_qualification: "",
  father_annual_income: "", mother_name: "", mother_phone: "", mother_email: "", mother_occupation: "",
  mother_qualification: "", mother_annual_income: "", guardian_name: "", guardian_relationship: "",
  guardian_phone: "", guardian_email: "", guardian_occupation: "", primary_contact: "father",
  declaration_accepted: false,
};

interface Submitted {
  application_number: string;
  access_token: string;
  required_documents: DocumentType[];
}

const SUBMITTED_KEY = "lkms.lastApplication";

export default function Apply() {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<ApplicationForm>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState<Submitted | null>(null);
  const [captcha, setCaptcha] = useState<string | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const options = useQuery({
    queryKey: ["admission-options"],
    queryFn: () => api.get<{ sessions: AcademicSession[]; classes: SchoolClass[] }>("/academics/admission-options/"),
  });

  useEffect(() => {
    const only = options.data?.sessions.length === 1 ? options.data.sessions[0] : null;
    if (only && form.session === "") setForm((f) => ({ ...f, session: only.id }));
  }, [options.data, form.session]);

  const school = useSchool();
  useEffect(() => {
    if (school?.state) setForm((f) => (f.state === "" ? { ...f, state: school.state } : f));
  }, [school?.state]);

  useEffect(() => {
    headingRef.current?.focus();
  }, [step]);

  const set = <K extends keyof ApplicationForm>(key: K) => (value: ApplicationForm[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
    if (errors[key]) setErrors(({ [key]: _, ...rest }) => rest);
  };
  const text = (key: keyof ApplicationForm) => ({
    name: key,
    value: String(form[key] ?? ""),
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      set(key)(e.target.value as never),
  });

  function next(e: FormEvent) {
    e.preventDefault();
    if (step === 2 && !form.father_name && !form.mother_name && !form.guardian_name) {
      setFormError("Give the details of at least one parent or guardian.");
      return;
    }
    if (step === 2 && !form[`${form.primary_contact}_phone` as keyof ApplicationForm]) {
      setFormError(`Give a mobile number for the ${RELATIONSHIPS[form.primary_contact].toLowerCase()}, or choose another main contact.`);
      return;
    }
    setFormError("");
    setStep((s) => s + 1);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setFormError("");
    const honeypot = (e.currentTarget as HTMLFormElement).elements.namedItem("website") as HTMLInputElement | null;
    const payload: Record<string, unknown> = { ...form, website: honeypot?.value ?? "", captcha };
    for (const key of ["father_annual_income", "mother_annual_income"]) if (payload[key] === "") payload[key] = null;
    try {
      const result = await api.post<Submitted>("/admissions/public/apply/", payload, { auth: false });
      setSubmitted(result);
      try {
        sessionStorage.setItem(SUBMITTED_KEY, JSON.stringify(result));
      } catch {
        /* not essential */
      }
      setStep(4);
    } catch (err) {
      if (err instanceof ApiError && err.fieldErrors.captcha) {
        setCaptcha(null);
        setFormError("Please type the letters from the picture again, then send the application.");
      } else if (err instanceof ApiError) {
        const fields = err.fieldErrors;
        setErrors(fields);
        const keys = Object.keys(fields);
        const target = keys.length ? Math.min(...keys.map((k) => FIELD_STEP[k] ?? (k === "declaration_accepted" ? 3 : 2))) : 3;
        setFormError(keys.length ? "Some details need correcting. They are marked below." : err.message);
        setStep(target);
      } else {
        setFormError("Could not send the application. Check your internet connection and try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (options.isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (options.isError) return <p role="alert">The admission form could not be loaded. Please try again later.</p>;
  if (!options.data?.sessions.length) {
    return (
      <div className="mx-auto max-w-xl space-y-3">
        <h1 className="text-2xl font-bold">Admissions are closed</h1>
        <p className="text-muted-foreground">Online admissions are not open at the moment. Please contact the school office.</p>
      </div>
    );
  }

  const { sessions, classes } = options.data;
  const selectedClass = classes.find((c) => c.id === form.class_applied);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="space-y-4">
        <h1 ref={headingRef} tabIndex={-1} className="text-2xl font-bold outline-none">
          Admission application
        </h1>
        <nav aria-label="Progress">
          <ol className="flex flex-wrap gap-2 text-sm">
            {STEPS.map((label, i) => (
              <li
                key={label}
                aria-current={i === step ? "step" : undefined}
                className={
                  i === step
                    ? "rounded-full bg-primary px-3 py-1 font-medium text-primary-foreground"
                    : i < step
                      ? "rounded-full bg-secondary-light px-3 py-1 text-secondary"
                      : "rounded-full bg-muted px-3 py-1 text-muted-foreground"
                }
              >
                {i + 1}. {label}
                {i < step && <span className="sr-only"> (done)</span>}
              </li>
            ))}
          </ol>
        </nav>
      </div>

      {formError && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      <CaptchaGate pass={captcha} onPass={setCaptcha}>

      {step === 0 && (
        <StepForm onSubmit={next} onBack={null}>
          <fieldset className="space-y-4">
            <legend className="mb-2 text-lg font-semibold">Admission sought</legend>
            {sessions.length > 1 && (
              <Field label="Academic session" required error={errors.session}>
                <NativeSelect {...text("session")} onChange={(e) => set("session")(Number(e.target.value))}>
                  <option value="">Choose…</option>
                  {sessions.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </NativeSelect>
              </Field>
            )}
            <Field
              label="Class"
              required
              error={errors.class_applied}
              hint={sessions.length === 1 ? `For the ${sessions[0].name} session` : undefined}
            >
              <NativeSelect {...text("class_applied")} onChange={(e) => set("class_applied")(Number(e.target.value) || "")}>
                <option value="">Choose a class…</option>
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </NativeSelect>
            </Field>
          </fieldset>

          <fieldset className="space-y-4">
            <legend className="mb-2 text-lg font-semibold">About the child</legend>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="First name" required error={errors.first_name}>
                <Input {...text("first_name")} autoComplete="off" maxLength={50} />
              </Field>
              <Field label="Surname" error={errors.last_name}>
                <Input {...text("last_name")} autoComplete="off" maxLength={50} />
              </Field>
            </div>
            <Field
              label="Date of birth"
              required
              error={errors.date_of_birth}
              hint={ageHint(selectedClass, sessions.find((s) => s.id === form.session))}
            >
              <Input type="date" {...text("date_of_birth")} max={new Date().toISOString().slice(0, 10)} />
            </Field>
            <fieldset>
              <legend className="mb-1.5 text-sm font-medium">
                Gender<span className="text-destructive"> *</span>
              </legend>
              <div className="flex flex-wrap gap-4">
                {GENDERS.map((g) => (
                  <label key={g.value} className="flex min-h-11 items-center gap-2">
                    <input type="radio" name="gender" value={g.value} required checked={form.gender === g.value}
                      onChange={() => set("gender")(g.value as ApplicationForm["gender"])} className="h-4 w-4 accent-primary" />
                    {g.label}
                  </label>
                ))}
              </div>
              {errors.gender && <p className="text-sm text-destructive">{errors.gender.join(" ")}</p>}
            </fieldset>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Category" required error={errors.category}>
                <NativeSelect {...text("category")}>
                  {CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </NativeSelect>
              </Field>
              <Field label="Blood group" error={errors.blood_group}>
                <NativeSelect {...text("blood_group")}>
                  <option value="">Don't know</option>
                  {BLOOD_GROUPS.map((b) => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </NativeSelect>
              </Field>
              <Field label="Religion" error={errors.religion}>
                <Input {...text("religion")} maxLength={50} />
              </Field>
              <Field label="Mother tongue" error={errors.mother_tongue}>
                <Input {...text("mother_tongue")} maxLength={50} />
              </Field>
            </div>
            <Field label="Child's Aadhaar number" error={errors.aadhaar_number} hint="12 digits, if the child has one">
              <Input {...text("aadhaar_number")} inputMode="numeric" pattern="\d{12}" maxLength={12} autoComplete="off" />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Previous school" error={errors.previous_school}>
                <Input {...text("previous_school")} maxLength={200} />
              </Field>
              <Field label="Class studied there" error={errors.previous_class}>
                <Input {...text("previous_class")} maxLength={50} />
              </Field>
            </div>
            <Field label="Brother or sister already studying here" error={errors.sibling_admission_number}
              hint="Their admission number, if any">
              <Input {...text("sibling_admission_number")} maxLength={20} />
            </Field>
          </fieldset>
        </StepForm>
      )}

      {step === 1 && (
        <StepForm onSubmit={next} onBack={() => setStep(0)}>
          <fieldset className="space-y-4">
            <legend className="mb-2 text-lg font-semibold">Home address</legend>
            <Field label="House, street and area" required error={errors.address_line}>
              <Textarea {...text("address_line")} autoComplete="street-address" maxLength={300} rows={3} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="City / town / village" required error={errors.city}>
                <Input {...text("city")} autoComplete="address-level2" maxLength={100} />
              </Field>
              <Field label="District" required error={errors.district}>
                <Input {...text("district")} maxLength={100} />
              </Field>
              <Field label="State" required error={errors.state}>
                <Input {...text("state")} autoComplete="address-level1" maxLength={100} />
              </Field>
              <Field label="PIN code" required error={errors.pincode}>
                <Input {...text("pincode")} autoComplete="postal-code" inputMode="numeric" pattern="[1-9]\d{5}" maxLength={6} />
              </Field>
            </div>
          </fieldset>
        </StepForm>
      )}

      {step === 2 && (
        <StepForm onSubmit={next} onBack={() => setStep(1)}>
          <p className="text-sm text-muted-foreground">Fill in at least one parent or guardian.</p>
          {(["father", "mother"] as const).map((who) => (
            <fieldset key={who} className="space-y-4">
              <legend className="mb-2 text-lg font-semibold">{RELATIONSHIPS[who]}</legend>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Full name" error={errors[`${who}_name`]}>
                  <Input {...text(`${who}_name`)} maxLength={100} />
                </Field>
                <Field label="Mobile number" error={errors[`${who}_phone`]} hint="10 digits">
                  <Input type="tel" {...text(`${who}_phone`)} inputMode="tel" maxLength={14} />
                </Field>
                <Field label="Email" error={errors[`${who}_email`]}>
                  <Input type="email" {...text(`${who}_email`)} autoCapitalize="off" spellCheck={false} />
                </Field>
                <Field label="Occupation" error={errors[`${who}_occupation`]}>
                  <Input {...text(`${who}_occupation`)} maxLength={100} />
                </Field>
                <Field label="Education" error={errors[`${who}_qualification`]}>
                  <Input {...text(`${who}_qualification`)} maxLength={100} />
                </Field>
                <Field label="Annual income (₹)" error={errors[`${who}_annual_income`]}>
                  <Input {...text(`${who}_annual_income`)} inputMode="numeric" pattern="\d{1,10}(\.\d{1,2})?" />
                </Field>
              </div>
            </fieldset>
          ))}
          <fieldset className="space-y-4">
            <legend className="mb-2 text-lg font-semibold">Guardian (if the child lives with someone else)</legend>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Full name" error={errors.guardian_name}>
                <Input {...text("guardian_name")} maxLength={100} />
              </Field>
              <Field label="Relationship to child" error={errors.guardian_relationship} hint="e.g. Uncle, Grandmother">
                <Input {...text("guardian_relationship")} maxLength={50} />
              </Field>
              <Field label="Mobile number" error={errors.guardian_phone}>
                <Input type="tel" {...text("guardian_phone")} inputMode="tel" maxLength={14} />
              </Field>
              <Field label="Email" error={errors.guardian_email}>
                <Input type="email" {...text("guardian_email")} autoCapitalize="off" spellCheck={false} />
              </Field>
            </div>
          </fieldset>
          <fieldset>
            <legend className="mb-1.5 font-semibold">Main contact for the school</legend>
            <p className="mb-2 text-sm text-muted-foreground">Fee reminders and school messages go to this person's mobile.</p>
            <div className="flex flex-wrap gap-4">
              {(["father", "mother", "guardian"] as const).map((who) => (
                <label key={who} className="flex min-h-11 items-center gap-2">
                  <input type="radio" name="primary_contact" value={who} checked={form.primary_contact === who}
                    onChange={() => set("primary_contact")(who)} className="h-4 w-4 accent-primary" />
                  {RELATIONSHIPS[who]}
                </label>
              ))}
            </div>
            {errors.primary_contact && <p className="text-sm text-destructive">{errors.primary_contact.join(" ")}</p>}
          </fieldset>
        </StepForm>
      )}

      {step === 3 && (
        <form onSubmit={submit} className="space-y-6" noValidate={false}>
          <Summary form={form} sessions={sessions} classes={classes} onEdit={setStep} />
          {/* Spam trap: hidden from people, filled in by bots. */}
          <div aria-hidden="true" className="absolute -left-[9999px]">
            <label>
              Website <input type="text" name="website" tabIndex={-1} autoComplete="off" />
            </label>
          </div>
          <div className="rounded-lg border bg-muted/50 p-4">
            <label className="flex items-start gap-3">
              <input type="checkbox" required checked={form.declaration_accepted}
                onChange={(e) => set("declaration_accepted")(e.target.checked)} className="mt-1 h-5 w-5 shrink-0 accent-primary" />
              <span className="text-sm">
                I am the parent or legal guardian of this child. The details given are true to the best of my knowledge.
                I agree that the school may store and use these details and documents for admission and school records,
                and contact me about them.
              </span>
            </label>
            {errors.declaration_accepted && <p className="mt-2 text-sm text-destructive">{errors.declaration_accepted.join(" ")}</p>}
          </div>
          <div className="flex justify-between gap-3">
            <Button type="button" variant="outline" onClick={() => setStep(2)}>Back</Button>
            <Button type="submit" disabled={submitting}>{submitting ? "Sending…" : "Submit application"}</Button>
          </div>
        </form>
      )}

      {step === 4 && submitted && <Documents submitted={submitted} />}
      </CaptchaGate>
    </div>
  );
}

function StepForm({ onSubmit, onBack, children }: { onSubmit: (e: FormEvent) => void; onBack: (() => void) | null; children: ReactNode }) {
  return (
    <form onSubmit={onSubmit} className="space-y-8">
      {children}
      <div className="flex justify-between gap-3">
        {onBack ? <Button type="button" variant="outline" onClick={onBack}>Back</Button> : <span />}
        <Button type="submit" enterKeyHint="next">Continue</Button>
      </div>
    </form>
  );
}

function ageHint(school_class: SchoolClass | undefined, session: AcademicSession | undefined) {
  if (!school_class || !session || (school_class.min_age_years == null && school_class.max_age_years == null)) return undefined;
  const on = formatDate(session.age_cutoff_date ?? session.start_date);
  if (school_class.min_age_years != null && school_class.max_age_years != null) {
    return `For ${school_class.name} the child should be ${school_class.min_age_years} to ${school_class.max_age_years} years old on ${on}.`;
  }
  if (school_class.min_age_years != null) return `For ${school_class.name} the child should be at least ${school_class.min_age_years} on ${on}.`;
  return `For ${school_class.name} the child should be at most ${school_class.max_age_years} on ${on}.`;
}

function Summary({ form, sessions, classes, onEdit }: { form: ApplicationForm; sessions: AcademicSession[]; classes: SchoolClass[]; onEdit: (step: number) => void }) {
  const rows: [string, string, number][] = [
    ["Session", sessions.find((s) => s.id === form.session)?.name ?? "", 0],
    ["Class", classes.find((c) => c.id === form.class_applied)?.name ?? "", 0],
    ["Child", `${form.first_name} ${form.last_name}`.trim(), 0],
    ["Date of birth", formatDate(form.date_of_birth), 0],
    ["Address", [form.address_line, form.city, form.district, form.state, form.pincode].filter(Boolean).join(", "), 1],
    ["Father", [form.father_name, form.father_phone].filter(Boolean).join(", "), 2],
    ["Mother", [form.mother_name, form.mother_phone].filter(Boolean).join(", "), 2],
    ["Guardian", [form.guardian_name, form.guardian_relationship, form.guardian_phone].filter(Boolean).join(", "), 2],
    ["Main contact", RELATIONSHIPS[form.primary_contact], 2],
  ];
  return (
    <section aria-labelledby="review-heading" className="space-y-3">
      <h2 id="review-heading" className="text-lg font-semibold">Check the details</h2>
      <dl className="divide-y rounded-lg border">
        {rows.filter(([, value]) => value).map(([label, value, step]) => (
          <div key={label} className="flex flex-wrap items-start justify-between gap-2 p-3">
            <div>
              <dt className="text-sm text-muted-foreground">{label}</dt>
              <dd className="font-medium">{value}</dd>
            </div>
            <Button type="button" variant="link" className="h-auto p-0" onClick={() => onEdit(step)}>
              Change<span className="sr-only"> {label.toLowerCase()}</span>
            </Button>
          </div>
        ))}
      </dl>
    </section>
  );
}

function Documents({ submitted }: { submitted: Submitted }) {
  const [uploaded, setUploaded] = useState<Record<number, UploadedState>>({});
  const types = useQuery({
    queryKey: ["public-document-types", submitted.application_number],
    queryFn: () => api.get<DocumentType[]>("/admissions/public/document-types/"),
  });
  const required = new Set(submitted.required_documents.map((d) => d.id));
  const relevant = (types.data ?? []).filter((t) => required.has(t.id) || !t.is_required);
  const missing = submitted.required_documents.filter((d) => !uploaded[d.id]);

  return (
    <div className="space-y-6">
      <Alert>
        <AlertTitle>Application received</AlertTitle>
        <AlertDescription className="space-y-2">
          <p>
            Application number: <strong className="font-mono text-base">{submitted.application_number}</strong>
          </p>
          <p>
            Access code for uploading documents: <strong className="break-all font-mono">{submitted.access_token}</strong>
          </p>
          <p>Write both down or take a screenshot. You need the application number to track your application.</p>
        </AlertDescription>
      </Alert>

      <section aria-labelledby="docs-heading" className="space-y-3">
        <h2 id="docs-heading" className="text-lg font-semibold">Upload documents</h2>
        <p className="text-sm text-muted-foreground">
          Clear photos taken on a phone are fine. The school will check each document and tell you if anything needs to be redone.
        </p>
        <DocumentUploader
          documentTypes={relevant}
          uploaded={uploaded}
          uploadPath={`/admissions/public/${encodeURIComponent(submitted.application_number)}/documents/`}
          headers={{ "X-Application-Token": submitted.access_token }}
          onUploaded={(id, state) => setUploaded((u) => ({ ...u, [id]: state }))}
        />
      </section>

      <div aria-live="polite">
        {missing.length === 0 ? (
          <Alert>
            <AlertTitle>All required documents are uploaded</AlertTitle>
            <AlertDescription>
              The school will review your application. You can check its progress any time on the{" "}
              <Link to="/track" className="underline">tracking page</Link>.
            </AlertDescription>
          </Alert>
        ) : (
          <p className="text-sm text-muted-foreground">
            Still needed: {missing.map((d) => d.name).join(", ")}.
          </p>
        )}
      </div>
    </div>
  );
}
