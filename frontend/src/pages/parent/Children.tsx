import { Link } from "react-router-dom";

import { ErrorNote } from "@/components/Panel";
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
    </div>
  );
}
