import { Copy } from "lucide-react";

import { Button } from "@/components/ui/button";
import { toast } from "@/hooks/use-toast";

/** A password or code shown once, with a copy button and a reminder that it won't be shown again. */
export function OneTimeSecret({ title, value, children, onDone }: { title: string; value: string; children?: React.ReactNode; onDone: () => void }) {
  return (
    <div role="status" className="space-y-2 rounded-lg border-2 border-primary bg-primary/5 p-4">
      <p className="font-semibold">{title}</p>
      <div className="flex flex-wrap items-center gap-2">
        <code className="rounded bg-background px-3 py-2 font-mono text-xl tracking-wider">{value}</code>
        <Button variant="outline" size="sm" onClick={() => void navigator.clipboard?.writeText(value).then(() => toast({ title: "Copied" }))}>
          <Copy className="mr-1 h-4 w-4" aria-hidden="true" /> Copy
        </Button>
      </div>
      {children}
      <p className="text-sm text-muted-foreground">This is shown only once. Note it down or pass it on now.</p>
      <Button size="sm" onClick={onDone}>Done</Button>
    </div>
  );
}
