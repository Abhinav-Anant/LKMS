import { NavLink } from "react-router-dom";

import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

const tab = ({ isActive }: { isActive: boolean }) =>
  cn("border-b-2 px-3 py-2 text-sm font-medium", isActive ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground");

export function FeesNav() {
  const { can } = useAuth();
  return (
    <nav aria-label="Fees" className="flex flex-wrap gap-1 border-b">
      <NavLink to="/staff/fees" end className={tab}>Invoices</NavLink>
      <NavLink to="/staff/fees/concessions" className={tab}>Concessions</NavLink>
      <NavLink to="/staff/fees/reports" className={tab}>Reports</NavLink>
      {can("fees.manage") && <NavLink to="/staff/fees/setup" className={tab}>Fee setup</NavLink>}
    </nav>
  );
}
