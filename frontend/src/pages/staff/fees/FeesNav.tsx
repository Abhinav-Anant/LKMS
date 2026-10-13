import { useQuery } from "@tanstack/react-query";
import { NavLink } from "react-router-dom";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Paginated, UpiSubmission } from "@/lib/types";
import { cn } from "@/lib/utils";

const tab = ({ isActive }: { isActive: boolean }) =>
  cn("border-b-2 px-3 py-2 text-sm font-medium", isActive ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground");

export function FeesNav() {
  const { can } = useAuth();
  const pending = useQuery({
    queryKey: ["upi-submissions", "pending", 1],
    queryFn: () => api.get<Paginated<UpiSubmission>>("/fees/upi-submissions/", { status: "pending", page: 1 }),
  });
  const waiting = pending.data?.count ?? 0;
  return (
    <nav aria-label="Fees" className="flex flex-wrap gap-1 border-b">
      <NavLink to="/staff/fees" end className={tab}>Invoices</NavLink>
      <NavLink to="/staff/fees/upi" className={tab}>
        UPI payments
        {waiting > 0 && <span className="ml-1.5 rounded-full bg-amber-100 px-1.5 py-0.5 text-xs text-amber-900">{waiting}<span className="sr-only"> waiting</span></span>}
      </NavLink>
      <NavLink to="/staff/fees/concessions" className={tab}>Concessions</NavLink>
      <NavLink to="/staff/fees/reports" className={tab}>Reports</NavLink>
      {can("fees.manage") && <NavLink to="/staff/fees/setup" className={tab}>Fee setup</NavLink>}
    </nav>
  );
}
