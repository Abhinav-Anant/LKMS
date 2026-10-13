import { Link } from "react-router-dom";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ErrorNote } from "@/components/Panel";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useChildren } from "@/lib/parent";

export default function Children() {
  const { user } = useAuth();
  const children = useChildren();
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Namaste{user?.first_name ? `, ${user.first_name}` : ""}</h1>
      <ErrorNote error={children.error} />
      {children.data?.length === 0 && (
        <p className="rounded-lg border bg-background p-6 text-muted-foreground">
          No children studying at the school are linked to this mobile number. Please contact the school office.
        </p>
      )}
      <ul className="grid gap-3 sm:grid-cols-2">
        {children.data?.map((c) => (
          <li key={c.id}>
            <Link to={`/parent/children/${c.id}`} className="block space-y-1 rounded-lg border bg-background p-4 hover:bg-accent">
              <span className="block text-lg font-semibold">{c.full_name}</span>
              <span className="block text-sm text-muted-foreground">
                {c.class_label ?? "Class not assigned"}
                {c.roll_number ? ` · Roll ${c.roll_number}` : ""} · Adm. no. {c.admission_number}
              </span>
              {c.class_teacher && <span className="block text-sm">Class teacher: {c.class_teacher}</span>}
            </Link>
          </li>
        ))}
      </ul>
      <WhatsAppAlerts />
    </div>
  );
}

function WhatsAppAlerts() {
  const queryClient = useQueryClient();
  const pref = useQuery({ queryKey: ["parent-whatsapp"], queryFn: () => api.get<{ whatsapp_alerts: boolean }>("/parent/whatsapp/") });
  const save = useMutation({
    mutationFn: (on: boolean) => api.put<{ whatsapp_alerts: boolean }>("/parent/whatsapp/", { whatsapp_alerts: on }),
    // The box changes at once (see onChange); put it back if saving fails.
    onError: (_err, on) => queryClient.setQueryData(["parent-whatsapp"], { whatsapp_alerts: !on }),
    onSuccess: (data) => queryClient.setQueryData(["parent-whatsapp"], data),
  });
  if (!pref.data) return null;
  return (
    <div className="space-y-1 rounded-lg border bg-background p-4">
      <label className="flex items-start gap-3">
        <input type="checkbox" className="mt-1 h-5 w-5 accent-primary" checked={pref.data.whatsapp_alerts}
          onChange={(e) => {
            queryClient.setQueryData(["parent-whatsapp"], { whatsapp_alerts: e.target.checked });
            save.mutate(e.target.checked);
          }} />
        <span>
          <span className="font-medium">WhatsApp messages from school</span>
          <span className="block text-sm text-muted-foreground">
            Fee reminders, receipts, absence alerts and important notices. Sign-in codes are always sent.
          </span>
        </span>
      </label>
      <ErrorNote error={save.error} />
    </div>
  );
}
