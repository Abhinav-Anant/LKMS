import { LogOut } from "lucide-react";
import { Link, NavLink, Navigate, Outlet } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { SchoolName } from "@/components/SchoolName";
import { useBranding } from "@/lib/school";
import { cn } from "@/lib/utils";

const navClass = ({ isActive }: { isActive: boolean }) =>
  cn("rounded-md px-3 py-2 text-sm font-medium hover:bg-accent", isActive && "bg-accent text-accent-foreground");

export function ParentLayout() {
  const { user, loading, signOut } = useAuth();
  const school = useBranding();
  if (loading) return <p className="p-8 text-muted-foreground">Loading…</p>;
  if (!user) return <Navigate to="/parent/login" replace />;
  if (user.role !== "parent") return <Navigate to="/staff" replace />;

  return (
    <div className="flex min-h-screen flex-col bg-muted/40">
      <header className="border-b bg-background">
        <div className="container flex flex-wrap items-center justify-between gap-2 py-3">
          <div className="flex flex-wrap items-center gap-4">
            <Link to="/parent" className="text-lg font-semibold text-primary"><SchoolName school={school} /></Link>
            <nav aria-label="Parent" className="flex gap-1">
              <NavLink to="/parent" end className={navClass}>My children</NavLink>
              <NavLink to="/parent/notices" className={navClass}>Notices</NavLink>
            </nav>
          </div>
          <Button variant="outline" size="sm" onClick={() => void signOut()}>
            <LogOut className="mr-1 h-4 w-4" aria-hidden="true" />
            Sign out
          </Button>
        </div>
      </header>
      <main className="container flex-1 py-6">
        <Outlet />
      </main>
    </div>
  );
}
