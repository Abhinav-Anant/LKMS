import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { Field, NativeSelect } from "@/components/Field";
import { OneTimeSecret } from "@/components/OneTimeSecret";
import { ErrorNote, Panel } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ROLE_LABELS, formatDateTime } from "@/lib/labels";
import type { PermissionMatrix, StaffUser, TemporaryPassword } from "@/lib/types";

const STAFF_ROLES = ["teacher", "office", "accountant", "principal", "admin"];

export default function Users() {
  const { user: me } = useAuth();
  const queryClient = useQueryClient();
  const users = useQuery({ queryKey: ["staff-users"], queryFn: () => api.get<StaffUser[]>("/auth/users/") });
  const [secret, setSecret] = useState<TemporaryPassword | null>(null);
  const [editing, setEditing] = useState<StaffUser | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [search, setSearch] = useState("");
  const canTouchAdmins = me?.role === "admin";
  const roles = STAFF_ROLES.filter((r) => r !== "admin" || canTouchAdmins);
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["staff-users"] });

  const create = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post<TemporaryPassword>("/auth/users/", body),
    onSuccess: (data) => {
      setSecret(data);
      setFieldErrors({});
      refresh();
    },
    onError: (err) => setFieldErrors(err instanceof ApiError ? err.fieldErrors : {}),
  });
  const update = useMutation({
    mutationFn: ({ id, ...body }: Partial<StaffUser> & { id: number }) => api.patch<StaffUser>(`/auth/users/${id}/`, body),
    onSuccess: () => {
      setEditing(null);
      refresh();
    },
  });
  const reset = useMutation({
    mutationFn: (id: number) => api.post<TemporaryPassword>(`/auth/users/${id}/reset-password/`),
    onSuccess: (data) => {
      setSecret(data);
      refresh();
    },
  });

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    create.mutate(Object.fromEntries(new FormData(form)), { onSuccess: () => form.reset() });
  }

  const q = search.trim().toLowerCase();
  const shown = users.data?.filter((u) => !q || `${u.full_name} ${u.username} ${u.phone}`.toLowerCase().includes(q));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Staff accounts</h1>
      {secret && (
        <OneTimeSecret title={`Temporary password for ${secret.username}`} value={secret.temporary_password} onDone={() => setSecret(null)}>
          <p className="text-sm">They sign in at the staff sign-in page and must choose their own password straight away.</p>
        </OneTimeSecret>
      )}
      <Panel title="Add a staff member">
        <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Field label="First name" required error={fieldErrors.first_name}><Input name="first_name" maxLength={150} /></Field>
          <Field label="Last name" error={fieldErrors.last_name}><Input name="last_name" maxLength={150} /></Field>
          <Field label="Username" required hint="Used to sign in, e.g. sunita.rao" error={fieldErrors.username}>
            <Input name="username" autoCapitalize="off" autoCorrect="off" spellCheck={false} maxLength={30} />
          </Field>
          <Field label="Role" required error={fieldErrors.role}>
            <NativeSelect name="role" defaultValue="teacher">
              {roles.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
            </NativeSelect>
          </Field>
          <Field label="Mobile" error={fieldErrors.phone}><Input name="phone" type="tel" inputMode="numeric" maxLength={14} /></Field>
          <Field label="Email" error={fieldErrors.email}><Input name="email" type="email" /></Field>
          <div className="sm:col-span-2 lg:col-span-3">
            <ErrorNote error={create.error && !Object.keys(fieldErrors).length ? create.error : null} />
            <Button type="submit" disabled={create.isPending}>{create.isPending ? "Adding…" : "Add and create temporary password"}</Button>
          </div>
        </form>
      </Panel>

      <Panel title="All staff" actions={<Input type="search" placeholder="Search" aria-label="Search staff" className="h-9 w-48" value={search} onChange={(e) => setSearch(e.target.value)} />}>
        <ErrorNote error={users.error ?? update.error ?? reset.error} />
        <ul className="divide-y">
          {shown?.map((u) => (
            <li key={u.id} className="space-y-2 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="font-medium">{u.full_name}</span>{" "}
                  <span className="text-sm text-muted-foreground">@{u.username}</span>
                  <span className="block text-sm text-muted-foreground">
                    {u.role_label}{u.phone && ` · ${u.phone}`} · last sign-in {u.last_login ? formatDateTime(u.last_login) : "never"}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {!u.is_active && <Badge variant="destructive">Deactivated</Badge>}
                  {u.must_change_password && u.is_active && <Badge variant="outline">Temporary password</Badge>}
                  {u.id !== me?.id && (u.role !== "admin" || canTouchAdmins) && (
                    <>
                      <Button variant="outline" size="sm" onClick={() => setEditing(editing?.id === u.id ? null : u)}>Edit</Button>
                      <Button variant="outline" size="sm" disabled={reset.isPending}
                        onClick={() => window.confirm(`Reset the password for ${u.full_name}? Their old password stops working.`) && reset.mutate(u.id)}>
                        Reset password
                      </Button>
                    </>
                  )}
                </div>
              </div>
              {editing?.id === u.id && (
                <form className="flex flex-wrap items-end gap-3 rounded-md bg-muted/50 p-3"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    update.mutate({ id: u.id, role: f.get("role") as StaffUser["role"], is_active: f.get("is_active") === "on" });
                  }}>
                  <label className="space-y-1 text-sm">
                    <span className="block font-medium">Role</span>
                    <NativeSelect name="role" defaultValue={u.role} className="h-9 w-44">
                      {roles.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                    </NativeSelect>
                  </label>
                  <label className="flex items-center gap-2 pb-2 text-sm">
                    <input type="checkbox" name="is_active" defaultChecked={u.is_active} className="h-4 w-4 accent-primary" />
                    Can sign in
                  </label>
                  <Button type="submit" size="sm" disabled={update.isPending}>Save</Button>
                </form>
              )}
            </li>
          ))}
        </ul>
      </Panel>
      <PermissionsTable />
    </div>
  );
}

function PermissionsTable() {
  const matrix = useQuery({ queryKey: ["permission-matrix"], queryFn: () => api.get<PermissionMatrix>("/auth/permissions/") });
  return (
    <Panel title="What each role can do">
      <p className="text-sm text-muted-foreground">Fixed in the system for now. Teachers are further limited to their own classes and subjects.</p>
      <ErrorNote error={matrix.error} />
      {matrix.data && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="p-2 text-left">Permission</th>
                {matrix.data.roles.map((r) => <th key={r.value} className="p-2">{r.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {matrix.data.capabilities.map((c) => (
                <tr key={c.key} className="border-t">
                  <td className="p-2 font-mono text-xs">{c.key}</td>
                  {matrix.data.roles.map((r) => (
                    <td key={r.value} className="p-2 text-center">
                      {c.roles.includes(r.value) ? <span aria-label="Yes">✓</span> : <span className="text-muted-foreground" aria-label="No">–</span>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
