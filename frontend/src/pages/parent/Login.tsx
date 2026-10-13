import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { Field } from "@/components/Field";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { useAuth, type TokenPair } from "@/lib/auth";

export default function ParentLogin() {
  const { user, acceptTokens } = useAuth();
  const navigate = useNavigate();
  const [phone, setPhone] = useState("");
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user?.role === "parent") return <Navigate to="/parent" replace />;

  function explain(err: unknown) {
    if (err instanceof ApiError && err.status === 429) return "Too many tries. Please wait a while and try again.";
    return err instanceof Error ? err.message : "Something went wrong. Please try again.";
  }

  async function sendCode(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api.post<{ detail: string }>("/auth/parent/request-code/", { phone }, { auth: false });
      setMessage(data.detail);
      setStep("code");
    } catch (err) {
      setError(explain(err));
    } finally {
      setBusy(false);
    }
  }

  async function verify(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const code = String(new FormData(e.currentTarget).get("code")).trim();
    setBusy(true);
    setError("");
    try {
      acceptTokens(await api.post<TokenPair>("/auth/parent/verify-code/", { phone, code }, { auth: false }));
      navigate("/parent", { replace: true });
    } catch (err) {
      setError(explain(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm space-y-6 py-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">Parent sign in</h1>
        <p className="text-sm text-muted-foreground">
          Use the mobile number you gave the school. All your children at the school appear under one sign-in.
        </p>
      </div>
      {error && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {step === "phone" ? (
        <form onSubmit={sendCode} className="space-y-4">
          <Field label="Mobile number" required>
            <Input type="tel" inputMode="numeric" autoComplete="tel-national" maxLength={14} value={phone} onChange={(e) => setPhone(e.target.value)} />
          </Field>
          <Button type="submit" className="w-full" disabled={busy || phone.replace(/\D/g, "").length < 10}>
            {busy ? "Sending…" : "Get sign-in code"}
          </Button>
          <button type="button" className="w-full text-sm text-primary underline-offset-4 hover:underline" onClick={() => setStep("code")}>
            I already have a code from the school office
          </button>
        </form>
      ) : (
        <form onSubmit={verify} className="space-y-4">
          {message && <p role="status" className="rounded-md bg-muted p-3 text-sm">{message}</p>}
          <Field label="Mobile number" required>
            <Input type="tel" inputMode="numeric" maxLength={14} value={phone} onChange={(e) => setPhone(e.target.value)} />
          </Field>
          <Field label="6-digit code" required>
            <Input name="code" inputMode="numeric" autoComplete="one-time-code" pattern="\d{6}" maxLength={6} className="font-mono text-lg tracking-widest" />
          </Field>
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? "Checking…" : "Sign in"}
          </Button>
          <button type="button" className="w-full text-sm text-primary underline-offset-4 hover:underline" onClick={() => { setStep("phone"); setMessage(""); }}>
            Send a new code
          </button>
        </form>
      )}
    </div>
  );
}
