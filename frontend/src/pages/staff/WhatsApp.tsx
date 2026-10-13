import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { Field, NativeSelect } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { WHATSAPP_EVENT_LABELS, formatDateTime } from "@/lib/labels";
import type { OptOut, OutgoingMessage, Paginated, WhatsAppStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATE_TEXT: Record<WhatsAppStatus["state"], string> = {
  off: "Switched off. Messages are logged but not sent.",
  unreachable: "The WhatsApp server is not reachable.",
  connected: "Connected and sending.",
  connecting: "Connecting…",
  disconnected: "Not linked to a phone.",
  qr_ready: "Waiting for the school's phone to scan the QR code.",
  error: "The WhatsApp server reported an error.",
};

const STATUS_STYLE: Record<OutgoingMessage["status"], string> = {
  queued: "bg-amber-100 text-amber-900",
  sending: "bg-amber-100 text-amber-900",
  sent: "bg-green-100 text-green-900",
  failed: "bg-red-100 text-red-900",
  skipped: "bg-slate-200 text-slate-800",
};

export default function WhatsApp() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">WhatsApp</h1>
      <Connection />
      <MessageLog />
      <OptOuts />
    </div>
  );
}

function Connection() {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const status = useQuery({
    queryKey: ["whatsapp-status"],
    queryFn: () => api.get<WhatsAppStatus>("/whatsapp/status/"),
    refetchInterval: (q) => (q.state.data?.state === "qr_ready" || q.state.data?.state === "connecting" ? 5_000 : 60_000),
  });
  const [showQr, setShowQr] = useState(false);
  const qr = useQuery({
    queryKey: ["whatsapp-qr"],
    queryFn: () => api.get<{ qr: string | null }>("/whatsapp/qr/"),
    enabled: showQr,
    refetchInterval: showQr ? 15_000 : false,
  });
  const reconnect = useMutation({
    mutationFn: () => api.post("/whatsapp/reconnect/"),
    onSuccess: () => {
      setShowQr(true);
      void queryClient.invalidateQueries({ queryKey: ["whatsapp-status"] });
    },
  });
  const s = status.data;
  const good = s?.state === "connected";

  return (
    <Panel title="Connection">
      <ErrorNote error={status.error} />
      {s && (
        <>
          <p className={cn("rounded-md p-3 text-sm font-medium", good ? "bg-green-100 text-green-900" : "bg-amber-100 text-amber-900")} role="status">
            {STATE_TEXT[s.state] ?? s.state}
            {s.phone && ` Number: +${s.phone}.`}
            {s.error && <span className="block font-normal">{s.error}</span>}
          </p>
          <dl className="grid gap-3 text-sm sm:grid-cols-4">
            <div><dt className="text-muted-foreground">Waiting to send</dt><dd className="text-xl font-bold">{s.queued}</dd></div>
            <div><dt className="text-muted-foreground">Sent in 24 hours</dt><dd className="text-xl font-bold">{s.sent_24h}</dd></div>
            <div><dt className="text-muted-foreground">Failed in 24 hours</dt><dd className={cn("text-xl font-bold", s.failed_24h > 0 && "text-destructive")}>{s.failed_24h}</dd></div>
            <div><dt className="text-muted-foreground">Numbers opted out</dt><dd className="text-xl font-bold">{s.opted_out}</dd></div>
          </dl>
          <p className="text-sm text-muted-foreground">
            Sends at most {s.rate_per_minute} messages a minute, with pauses in between.
            {s.quiet_hours && ` No alerts from ${s.quiet_hours}; sign-in codes go any time.`} If WhatsApp is down, the office can still give parents a sign-in code from the student's page.
          </p>
          {s.enabled && can("messaging.manage") && !good && (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => setShowQr(true)}>Link the school's phone</Button>
                <Button variant="outline" disabled={reconnect.isPending} onClick={() => reconnect.mutate()}>Reconnect</Button>
              </div>
              <ErrorNote error={reconnect.error ?? qr.error} />
              {showQr && (
                <div className="space-y-2 rounded-md border p-3">
                  <p className="text-sm">
                    On the school's phone open WhatsApp, then Settings, Linked devices, Link a device, and scan this code.
                  </p>
                  {qr.data?.qr ? (
                    <img src={qr.data.qr} alt="WhatsApp QR code to scan" className="h-64 w-64" />
                  ) : (
                    <p className="text-sm text-muted-foreground">No code yet. Press Reconnect, then wait a few seconds.</p>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </Panel>
  );
}

function MessageLog() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState("");
  const [event, setEvent] = useState("");
  const [page, setPage] = useState(1);
  const log = useQuery({
    queryKey: ["whatsapp-messages", status, event, page],
    queryFn: () => api.get<Paginated<OutgoingMessage>>("/whatsapp/messages/", { status, event, page }),
    placeholderData: keepPreviousData,
  });
  const retry = useMutation({
    mutationFn: (id: number) => api.post<OutgoingMessage>(`/whatsapp/messages/${id}/retry/`),
    onSuccess: () => {
      toast({ title: "Will be sent again" });
      void queryClient.invalidateQueries({ queryKey: ["whatsapp-messages"] });
      void queryClient.invalidateQueries({ queryKey: ["whatsapp-status"] });
    },
  });

  return (
    <Panel title="Send log">
      <div className="flex flex-wrap gap-3">
        <label className="space-y-1 text-sm">
          <span className="block font-medium">Status</span>
          <NativeSelect className="h-9 w-40" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
            <option value="">All</option>
            <option value="queued">Waiting to send</option>
            <option value="sent">Sent</option>
            <option value="failed">Failed</option>
            <option value="skipped">Not sent</option>
          </NativeSelect>
        </label>
        <label className="space-y-1 text-sm">
          <span className="block font-medium">Type</span>
          <NativeSelect className="h-9 w-52" value={event} onChange={(e) => { setEvent(e.target.value); setPage(1); }}>
            <option value="">All</option>
            {Object.entries(WHATSAPP_EVENT_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </NativeSelect>
        </label>
      </div>
      <ErrorNote error={log.error ?? retry.error} />
      <ul className="divide-y">
        {log.data?.results.map((m) => (
          <li key={m.id} className="space-y-1 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm">
                <span className="font-medium">{WHATSAPP_EVENT_LABELS[m.event] ?? m.event}</span> to {m.phone}
                {m.student_name && ` about ${m.student_name}`}
                <span className="block text-xs text-muted-foreground">
                  {formatDateTime(m.created_at)}{m.sent_at && ` · sent ${formatDateTime(m.sent_at)}`}
                  {m.attempts > 1 && ` · ${m.attempts} tries`}
                </span>
              </span>
              <span className="flex items-center gap-2">
                <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", STATUS_STYLE[m.status])}>{m.status_label}</span>
                {m.status === "failed" && m.kind === "alert" && (
                  <Button size="sm" variant="outline" disabled={retry.isPending} onClick={() => retry.mutate(m.id)}>Send again</Button>
                )}
              </span>
            </div>
            <p className="whitespace-pre-line text-sm text-muted-foreground">{m.text}</p>
            {(m.skip_reason || m.last_error) && <p className="text-xs text-destructive">{m.skip_reason || m.last_error}</p>}
          </li>
        ))}
        {log.data?.results.length === 0 && <li className="py-6 text-center text-muted-foreground">No messages.</li>}
      </ul>
      {log.data && (log.data.next || log.data.previous) && (
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" disabled={!log.data.previous} onClick={() => setPage(page - 1)}>Previous</Button>
          <Button variant="outline" size="sm" disabled={!log.data.next} onClick={() => setPage(page + 1)}>Next</Button>
        </div>
      )}
    </Panel>
  );
}

function OptOuts() {
  const queryClient = useQueryClient();
  const list = useQuery({ queryKey: ["whatsapp-opt-outs"], queryFn: () => api.get<OptOut[]>("/whatsapp/opt-outs/") });
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["whatsapp-opt-outs"] });
    void queryClient.invalidateQueries({ queryKey: ["whatsapp-status"] });
  };
  const add = useMutation({
    mutationFn: (body: Record<string, FormDataEntryValue>) => api.post<OptOut>("/whatsapp/opt-outs/", body),
    onSuccess: () => {
      setErrors({});
      refresh();
    },
    onError: (err) => setErrors(err instanceof ApiError ? err.fieldErrors : {}),
  });
  const remove = useMutation({ mutationFn: (id: number) => api.delete(`/whatsapp/opt-outs/${id}/`), onSuccess: refresh });

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    add.mutate(Object.fromEntries(new FormData(form)), { onSuccess: () => form.reset() });
  }

  return (
    <Panel title="Numbers that do not want alerts">
      <p className="text-sm text-muted-foreground">
        These numbers get no fee, attendance, admission or notice messages. Parents can also switch alerts off themselves in
        the parent portal. Sign-in codes they ask for are still sent.
      </p>
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
        <Field label="Mobile number" required error={errors.phone}><Input name="phone" type="tel" inputMode="numeric" maxLength={14} className="w-44" /></Field>
        <Field label="Note" error={errors.note}><Input name="note" maxLength={200} className="w-64" /></Field>
        <Button type="submit" disabled={add.isPending}>Stop alerts</Button>
      </form>
      <ErrorNote error={list.error ?? remove.error} />
      <ul className="divide-y">
        {list.data?.map((o) => (
          <li key={o.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
            <span>
              <span className="font-medium">{o.phone}</span> {o.note && `· ${o.note}`}
              <span className="block text-xs text-muted-foreground">{formatDateTime(o.created_at)}{o.created_by_name && ` by ${o.created_by_name}`}</span>
            </span>
            <span className="flex items-center gap-2">
              <Badge variant="outline">No alerts</Badge>
              <Button size="sm" variant="ghost" disabled={remove.isPending} onClick={() => remove.mutate(o.id)}>Allow again</Button>
            </span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
