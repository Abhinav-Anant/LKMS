import { LogOut } from "lucide-react";
import { Link, NavLink, Navigate, Outlet, useLocation } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

const navClass = ({ isActive }: { isActive: boolean }) =>
  cn("rounded-md px-3 py-2 text-sm font-medium hover:bg-accent", isActive && "bg-accent text-accent-foreground");

export function StaffLayout() {
  const { user, loading, signOut, can } = useAuth();
  const location = useLocation();

  if (loading) return <p className="p-8 text-muted-foreground">Loading…</p>;
  if (!user) return <Navigate to="/staff/login" replace state={{ from: location.pathname }} />;

  return (
    <div className="flex min-h-screen flex-col bg-muted/40">
      <header className="border-b bg-background">
        <div className="container flex flex-wrap items-center justify-between gap-2 py-3">
          <div className="flex flex-wrap items-center gap-4">
            <Link to="/staff" className="text-lg font-semibold text-primary">
              LKMS
            </Link>
            <nav aria-label="Staff" className="flex flex-wrap gap-1">
              {can("admissions.view") && (
                <NavLink to="/staff/applications" className={navClass}>
                  Admissions
                </NavLink>
              )}
              {can("students.view") && (
                <NavLink to="/staff/students" className={navClass}>
                  Students
                </NavLink>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-muted-foreground">
              {user.first_name || user.username} · {user.role}
            </span>
            <Button variant="outline" size="sm" onClick={() => void signOut()}>
              <LogOut className="mr-1 h-4 w-4" aria-hidden="true" />
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="container flex-1 py-6">
        <Outlet />
      </main>
    </div>
  );
}

export function StaffHome() {
  const { can } = useAuth();
  if (can("admissions.view")) return <Navigate to="/staff/applications" replace />;
  if (can("students.view")) return <Navigate to="/staff/students" replace />;
  return (
    <p className="text-muted-foreground">
      Your account is set up. The screens for your role arrive in a later phase.
    </p>
  );
}
