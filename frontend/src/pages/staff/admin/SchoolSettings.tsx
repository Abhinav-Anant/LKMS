import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";

import { Field, NativeSelect } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/hooks/use-toast";
import { ApiError, api } from "@/lib/api";
import { LOGO_URL, UPI_QR_URL } from "@/lib/school";

const URL_PATH = "/school/settings/";

const BOARDS = [
  ["cbse", "CBSE"],
  ["icse", "CISCE (ICSE)"],
  ["state", "State board"],
  ["other", "Other / not affiliated"],
] as const;

interface Settings {
  name: string;
  short_code: string;
  address: string;
  district: string;
  state: string;
  pincode: string;
  phone: string;
  email: string;
  website: string;
  udise_code: string;
  board: string;
  board_name: string;
  affiliation_number: string;
  admission_number_prefix: string;
  admission_number_width: number;
  next_admission_number: number;
  brand_colour: string;
  upi_id: string;
  upi_name: string;
  office_can_collect_fees: boolean;
  captcha_enabled: boolean;
  fee_reminder_days_before: number;
  fee_reminder_every_days: number;
  has_logo: boolean;
  has_upi_qr: boolean;
}

type Errors = Record<string, string[]>;

/** The school's own details, look and payment settings (administrator only). */
export default function SchoolSettings() {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["school-settings"], queryFn: () => api.get<Settings>(URL_PATH) });
  const [form, setForm] = useState<Settings>();
  const [errors, setErrors] = useState<Errors>({});
  const [version, setVersion] = useState(0); // changes the picture URLs after an upload

  useEffect(() => {
    if (settings.data) setForm(settings.data);
  }, [settings.data]);

  const save = useMutation({
    mutationFn: (body: Partial<Settings> | FormData) => api.patch<Settings>(URL_PATH, body),
    onSuccess: (data) => {
      setErrors({});
      setForm(data);
      setVersion((v) => v + 1);
      queryClient.setQueryData(["school-settings"], data);
      void queryClient.invalidateQueries({ queryKey: ["school"] });
      toast({ title: "Saved" });
    },
    onError: (err) => setErrors(err instanceof ApiError ? err.fieldErrors : {}),
  });

  if (settings.isLoading || !form) return <p className="text-muted-foreground">Loading…</p>;
  if (settings.isError) return <ErrorNote error={settings.error} />;

  const text = (key: keyof Settings) => ({
    value: String(form[key] ?? ""),
    onChange: (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value }),
  });
  const { has_logo: _logo, has_upi_qr: _qr, ...fields } = form;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate(fields);
  };
  const upload = (field: "logo" | "upi_qr", file?: File) => {
    if (!file) return;
    const body = new FormData();
    body.append(field, file);
    save.mutate(body);
  };

  return (
    <form className="space-y-4" onSubmit={submit} noValidate>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">School settings</h1>
        <Button type="submit" disabled={save.isPending}>{save.isPending ? "Saving…" : "Save"}</Button>
      </div>
      {save.isError && !Object.keys(errors).length && <ErrorNote error={save.error} />}

      <Panel title="The school">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="School name" required error={errors.name}><Input {...text("name")} maxLength={200} /></Field>
          <Field label="Short code" required hint="Starts application numbers, e.g. GVS-2026-27-00001" error={errors.short_code}>
            <Input {...text("short_code")} maxLength={10} />
          </Field>
          <Field label="Address" className="sm:col-span-2" error={errors.address}><Textarea {...text("address")} rows={2} /></Field>
          <Field label="District" error={errors.district}><Input {...text("district")} /></Field>
          <Field label="State" hint="Also filled in for parents on the admission form" error={errors.state}><Input {...text("state")} /></Field>
          <Field label="PIN code" error={errors.pincode}><Input {...text("pincode")} inputMode="numeric" maxLength={6} /></Field>
          <Field label="Phone" error={errors.phone}><Input {...text("phone")} type="tel" maxLength={15} /></Field>
          <Field label="Email" error={errors.email}><Input {...text("email")} type="email" /></Field>
          <Field label="Website" error={errors.website}><Input {...text("website")} type="url" placeholder="https://" /></Field>
          <Field label="UDISE+ code" error={errors.udise_code}><Input {...text("udise_code")} inputMode="numeric" maxLength={11} /></Field>
          <Field label="Affiliation number" error={errors.affiliation_number}><Input {...text("affiliation_number")} /></Field>
          <Field label="Board" required error={errors.board}>
            <NativeSelect {...text("board")}>
              {BOARDS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </NativeSelect>
          </Field>
          <Field label="Full name of the board" hint="Printed on report cards and certificates" error={errors.board_name}>
            <Input {...text("board_name")} maxLength={100} />
          </Field>
        </div>
      </Panel>

      <Panel title="Logo and colour">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <p className="text-sm font-medium">Logo</p>
            {form.has_logo ? (
              <img src={`${LOGO_URL}?v=${version}`} alt="Current logo" className="h-20 w-20 rounded border object-contain" />
            ) : (
              <p className="text-sm text-muted-foreground">No logo yet.</p>
            )}
            <Field label="Upload a logo" hint="PNG or JPEG. Shows on the website, receipts, report cards and certificates." error={errors.logo}>
              <Input type="file" accept="image/png,image/jpeg" onChange={(e) => upload("logo", e.target.files?.[0])} />
            </Field>
            {form.has_logo && (
              <Button type="button" variant="outline" size="sm" onClick={() => save.mutate({ remove_logo: true } as Partial<Settings>)}>
                Remove logo
              </Button>
            )}
          </div>
          <Field label="Main colour" required hint="Buttons, links and headings use it" error={errors.brand_colour}>
            <div className="flex items-center gap-2">
              <input
                type="color"
                aria-label="Pick the main colour"
                value={/^#[0-9a-f]{6}$/i.test(form.brand_colour) ? form.brand_colour : "#1d4ed8"}
                onChange={(e) => setForm({ ...form, brand_colour: e.target.value })}
                className="h-11 w-14 cursor-pointer rounded border"
              />
              <Input {...text("brand_colour")} maxLength={7} className="w-32 font-mono" />
            </div>
          </Field>
        </div>
      </Panel>

      <Panel title="Admission numbers">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Text before the number" error={errors.admission_number_prefix}><Input {...text("admission_number_prefix")} maxLength={10} /></Field>
          <Field label="Digits" required error={errors.admission_number_width}>
            <Input {...text("admission_number_width")} type="number" min={1} max={8} />
          </Field>
          <Field label="Next number" required error={errors.next_admission_number}>
            <Input {...text("next_admission_number")} type="number" min={1} />
          </Field>
        </div>
      </Panel>

      <Panel title="Fee payments">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="UPI ID" hint="Parents pay to this, e.g. 9876543210@SBI" error={errors.upi_id}><Input {...text("upi_id")} /></Field>
          <Field label="Name on the UPI account" error={errors.upi_name}><Input {...text("upi_name")} /></Field>
          <div className="space-y-2">
            <p className="text-sm font-medium">QR code shown to parents</p>
            {(form.has_upi_qr || form.upi_id) && (
              <img src={`${UPI_QR_URL}?v=${version}`} alt="UPI QR code" className="h-40 w-40 rounded border bg-white object-contain" />
            )}
            <p className="text-sm text-muted-foreground">
              {form.has_upi_qr ? "The bank's QR picture you uploaded." : "Made from the UPI ID. You can upload the bank's QR picture instead."}
            </p>
            <Field label="Upload the bank's QR picture" error={errors.upi_qr}>
              <Input type="file" accept="image/png,image/jpeg" onChange={(e) => upload("upi_qr", e.target.files?.[0])} />
            </Field>
            {form.has_upi_qr && (
              <Button type="button" variant="outline" size="sm" onClick={() => save.mutate({ remove_upi_qr: true } as Partial<Settings>)}>
                Use the QR made from the UPI ID
              </Button>
            )}
          </div>
          <div className="space-y-4">
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4"
                checked={form.office_can_collect_fees}
                onChange={(e) => setForm({ ...form, office_can_collect_fees: e.target.checked })}
              />
              <span>Office staff may record fees paid at the office (cash or cheque)</span>
            </label>
            <Field label="Remind parents this many days before a fee is due" required error={errors.fee_reminder_days_before}>
              <Input {...text("fee_reminder_days_before")} type="number" min={0} max={30} />
            </Field>
            <Field label="Remind again every this many days while overdue" required error={errors.fee_reminder_every_days}>
              <Input {...text("fee_reminder_every_days")} type="number" min={1} max={60} />
            </Field>
          </div>
        </div>
      </Panel>

      <Panel title="Website security">
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            className="mt-1 h-4 w-4"
            checked={form.captcha_enabled}
            onChange={(e) => setForm({ ...form, captcha_enabled: e.target.checked })}
          />
          <span>
            Ask visitors to type the letters from a picture (CAPTCHA) before they can use the admission form, application
            tracking and parent sign-in. Keeps out automated spam.
          </span>
        </label>
      </Panel>
    </form>
  );
}
