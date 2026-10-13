import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Panel({ title, children, className, actions }: { title: string; children: ReactNode; className?: string; actions?: ReactNode }) {
  return (
    <section className={cn("space-y-3 rounded-lg border bg-background p-4", className)} aria-label={title}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">{title}</h2>
        {actions}
      </div>
      {children}
    </section>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
      {message}
    </p>
  );
}
