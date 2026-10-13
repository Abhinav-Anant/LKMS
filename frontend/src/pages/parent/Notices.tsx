import { useQuery } from "@tanstack/react-query";

import { ErrorNote } from "@/components/Panel";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/labels";
import type { ParentNotice } from "@/lib/types";

export default function ParentNotices() {
  const notices = useQuery({ queryKey: ["parent-notices"], queryFn: () => api.get<ParentNotice[]>("/parent/notices/") });
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Notices from school</h1>
      <ErrorNote error={notices.error} />
      <ul className="space-y-3">
        {notices.data?.map((n) => (
          <li key={n.id} className="space-y-1 rounded-lg border bg-background p-4">
            <h2 className="font-semibold">{n.title}</h2>
            {n.published_at && <p className="text-xs text-muted-foreground">{formatDate(n.published_at)}</p>}
            <p className="whitespace-pre-line text-sm">{n.body}</p>
          </li>
        ))}
        {notices.data?.length === 0 && <li className="rounded-lg border bg-background p-6 text-center text-muted-foreground">No notices right now.</li>}
      </ul>
    </div>
  );
}
