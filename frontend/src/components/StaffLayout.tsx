import { KeyRound, LogOut } from "lucide-react";
import { Link, NavLink, Navigate, Outlet, useLocation } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { ROLE_LABELS } from "@/lib/labels";
import { cn } from "@/lib/utils";
import ChangePassword from "@/pages/staff/ChangePassword";

const navClass = ({ isActive }: { isActive: boolean }) =>
  cn("rounded-md px-3 py-2 text-sm font-medium hover:bg-accent", isActive && "bg-accent text-accent-foreground");

export function StaffLayout() {
  const { user, loading, signOut, can } = useAuth();
  const location = useLocation();

  if (loading) return <p className="p-8 text-muted-foreground">Loading…</p>;
  if (!user) return <Navigate to="/staff/login" replace state={{ from: location.pathname }} />;
  if (user.role === "parent") return <Navigate to="/parent" replace />;

  const teaches = can("attendance.mark") || can("marks.enter");

  return (
    <div className="flex min-h-screen flex-col bg-muted/40">
      <header className="border-b bg-background">
        <div className="container flex flex-wrap items-center justify-between gap-2 py-3">
          <div className="flex flex-wrap items-center gap-4">
            <Link to="/staff" className="text-lg font-semibold text-primary">
              LKMS
            </Link>
            {!user.must_change_password && (
              <nav aria-label="Staff" className="flex flex-wrap gap-1">
                {can("reports.view") && (
                  <NavLink to="/staff/dashboard" className={navClass}>
                    Dashboard
                  </NavLink>
                )}
                {teaches && (
                  <NavLink to="/staff/classes" className={navClass}>
                    My classes
                  </NavLink>
                )}
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
                {can("fees.view") && (
                  <NavLink to="/staff/fees" className={navClass}>
                    Fees
                  </NavLink>
                )}
                {can("notices.post") && (
                  <NavLink to="/staff/notices" className={navClass}>
                    Notices
                  </NavLink>
                )}
                {can("messaging.view") && (
                  <NavLink to="/staff/whatsapp" className={navClass}>
                    WhatsApp
                  </NavLink>
                )}
                {can("academics.manage") && (
                  <NavLink to="/staff/setup" className={navClass}>
                    School setup
                  </NavLink>
                )}
                {can("users.manage") && (
                  <NavLink to="/staff/users" className={navClass}>
                    Users
                  </NavLink>
                )}
              </nav>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-muted-foreground">
              {user.first_name || user.username} · {ROLE_LABELS[user.role] ?? user.role}
            </span>
            {!user.must_change_password && (
              <Button asChild variant="ghost" size="sm">
                <Link to="/staff/password">
                  <KeyRound className="mr-1 h-4 w-4" aria-hidden="true" />
                  Password
                </Link>
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={() => void signOut()}>
              <LogOut className="mr-1 h-4 w-4" aria-hidden="true" />
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="container flex-1 py-6">{user.must_change_password ? <ChangePassword forced /> : <Outlet />}</main>
    </div>
  );
}

export function StaffHome() {
  const { can } = useAuth();
  if (can("reports.view")) return <Navigate to="/staff/dashboard" replace />;
  if (can("attendance.mark") || can("marks.enter")) return <Navigate to="/staff/classes" replace />;
  if (can("admissions.view")) return <Navigate to="/staff/applications" replace />;
  if (can("students.view")) return <Navigate to="/staff/students" replace />;
  if (can("fees.view")) return <Navigate to="/staff/fees" replace />;
  return <p className="text-muted-foreground">Your account is set up, but no screens are open to your role yet.</p>;
}
