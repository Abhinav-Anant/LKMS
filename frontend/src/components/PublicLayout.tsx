import { Link, NavLink, Outlet } from "react-router-dom";

import { SchoolName } from "@/components/SchoolName";
import { useBranding } from "@/lib/school";
import { cn } from "@/lib/utils";

const navClass = ({ isActive }: { isActive: boolean }) =>
  cn("rounded-md px-3 py-2 text-sm font-medium hover:bg-accent", isActive && "bg-accent text-accent-foreground");

export function PublicLayout() {
  const school = useBranding();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b bg-background">
        <div className="container flex flex-wrap items-center justify-between gap-2 py-3">
          <Link to="/" className="text-lg font-semibold text-primary">
            <SchoolName school={school} />
          </Link>
          <nav aria-label="Main" className="flex flex-wrap gap-1">
            <NavLink to="/#admissions" className={navClass}>
              Apply
            </NavLink>
            <NavLink to="/track" className={navClass}>
              Track application
            </NavLink>
            <NavLink to="/#sign-in" className={navClass}>
              Sign in
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="container flex-1 py-8">
        <Outlet />
      </main>
      <footer className="border-t py-6 text-center text-sm text-muted-foreground">
        {school?.name}
        {school?.district ? `, ${school.district}` : ""}
        {school?.phone ? ` · ${school.phone}` : ""}
      </footer>
    </div>
  );
}
