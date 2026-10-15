import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { Field } from "@/components/Field";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function Login({ embedded = false }: { embedded?: boolean }) {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const from = (location.state as { from?: string } | null)?.from ?? "/staff";

  if (user) return <Navigate to={from} replace />;

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    const data = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await signIn(String(data.get("username")), String(data.get("password")));
      navigate(from, { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "Username or password is wrong."
          : err instanceof ApiError && err.status === 429
            ? "Too many attempts. Wait a minute and try again."
            : "Could not sign in. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={embedded ? "space-y-6" : "mx-auto max-w-sm space-y-6 py-8"}>
      {!embedded && <h1 className="text-2xl font-bold">Staff sign in</h1>}
      {error && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form onSubmit={submit} method="post" className="space-y-4">
        <Field label="Username" required>
          <Input name="username" autoComplete="username" autoCapitalize="off" autoCorrect="off" spellCheck={false} />
        </Field>
        <Field label="Password" required>
          <Input name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" />
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={showPassword} onChange={(e) => setShowPassword(e.target.checked)} className="h-4 w-4 accent-primary" />
          Show password
        </label>
        <Button type="submit" className="w-full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </div>
  );
}
