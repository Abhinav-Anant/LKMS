import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";

import { Field } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";

interface Challenge {
  enabled: boolean;
  challenge?: string;
  image?: string;
}

/**
 * Shows a picture of letters the visitor must type before the form appears.
 * `pass` is null until solved; the form sends it as `captcha`. Set it back to null to ask again.
 * When the school has switched the CAPTCHA off, the form shows straight away with an empty pass.
 */
export function CaptchaGate({ pass, onPass, children }: { pass: string | null; onPass: (pass: string) => void; children: ReactNode }) {
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setAnswer("");
    try {
      const data = await api.get<Challenge>("/captcha/");
      if (!data.enabled) onPass("");
      else setChallenge(data);
    } catch {
      setError("The check could not be loaded. Please reload the page.");
    }
  }, [onPass]);

  useEffect(() => {
    if (pass === null) load();
  }, [pass, load]);

  if (pass !== null) return <>{children}</>;

  async function check(e: FormEvent) {
    e.preventDefault();
    if (!challenge?.challenge || busy) return;
    setBusy(true);
    setError("");
    try {
      const data = await api.post<{ pass: string }>("/captcha/", { challenge: challenge.challenge, answer }, { auth: false });
      onPass(data.pass);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429 ? "Too many tries. Please wait a while and try again." : "The letters did not match. Try this new picture.");
      load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={check} className="mx-auto max-w-sm space-y-4 rounded-lg border p-5">
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">First, a quick check</h2>
        <p className="text-sm text-muted-foreground">Type the letters you see in the picture. This keeps out automated spam.</p>
      </div>
      <div className="flex items-center gap-3">
        {challenge?.image ? (
          <img src={challenge.image} alt="Letters to type. If you cannot read them, ask for a new picture." width={200} height={70} className="rounded border" />
        ) : (
          <div className="h-[70px] w-[200px] animate-pulse rounded border bg-muted" />
        )}
        <Button type="button" variant="outline" size="sm" onClick={load}>
          New picture
        </Button>
      </div>
      <Field label="Letters in the picture" required error={error || undefined}>
        <Input value={answer} onChange={(e) => setAnswer(e.target.value)} autoComplete="off" autoCapitalize="characters"
          autoCorrect="off" spellCheck={false} maxLength={8} className="font-mono text-lg tracking-widest" />
      </Field>
      <Button type="submit" className="w-full" disabled={busy || answer.trim().length < 5}>
        {busy ? "Checking…" : "Continue"}
      </Button>
    </form>
  );
}
