import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { Field } from "@/components/Field";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function ChangePassword({ forced = false }: { forced?: boolean }) {
  const { reload } = useAuth();
  const navigate = useNavigate();
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const next = String(form.get("new_password"));
    if (next !== String(form.get("confirm"))) {
      setErrors({ confirm: ["The two new passwords do not match."] });
      return;
    }
    setBusy(true);
    setErrors({});
    setError("");
    try {
      await api.post("/auth/change-password/", { current_password: form.get("current_password"), new_password: next });
      await reload();
      toast({ title: "Password changed" });
      navigate("/staff", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) setErrors(err.fieldErrors);
      setError(err instanceof Error ? err.message : "Could not change the password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm space-y-4">
      <h1 className="text-2xl font-bold">{forced ? "Choose your own password" : "Change password"}</h1>
      {forced && (
        <p className="text-sm text-muted-foreground">
          You signed in with a temporary password. Choose a new one before you continue. Use at least 10 characters.
        </p>
      )}
      {error && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form onSubmit={submit} className="space-y-4 rounded-lg border bg-background p-4">
        <Field label={forced ? "Temporary password" : "Current password"} required error={errors.current_password}>
          <Input name="current_password" type="password" autoComplete="current-password" />
        </Field>
        <Field label="New password" required error={errors.new_password} hint="At least 10 characters, not only numbers.">
          <Input name="new_password" type="password" autoComplete="new-password" minLength={10} />
        </Field>
        <Field label="New password again" required error={errors.confirm}>
          <Input name="confirm" type="password" autoComplete="new-password" />
        </Field>
        <Button type="submit" className="w-full" disabled={busy}>
          {busy ? "Saving…" : "Save new password"}
        </Button>
      </form>
    </div>
  );
}
