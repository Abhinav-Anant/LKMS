import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { NativeSelect } from "@/components/Field";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { STATUS_LABELS, formatDate } from "@/lib/labels";
import type { AcademicSession, ApplicationListItem, Paginated, SchoolClass } from "@/lib/types";

export default function Applications() {
  const [params, setParams] = useSearchParams();
  const filters = {
    status: params.get("status") ?? "",
    session: params.get("session") ?? "",
    class_applied: params.get("class_applied") ?? "",
    search: params.get("search") ?? "",
    page: params.get("page") ?? "1",
  };
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setParams(next, { replace: true });
  };

  const sessions = useQuery({ queryKey: ["sessions"], queryFn: () => api.get<Paginated<AcademicSession>>("/academics/sessions/") });
  const classes = useQuery({ queryKey: ["classes"], queryFn: () => api.get<Paginated<SchoolClass>>("/academics/classes/") });
  const list = useQuery({
    queryKey: ["applications", filters],
    queryFn: () => api.get<Paginated<ApplicationListItem>>("/admissions/applications/", { ...filters, ordering: "-submitted_at" }),
    placeholderData: keepPreviousData,
  });
  const page = Number(filters.page);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Admission applications</h1>
      <form role="search" className="grid gap-3 rounded-lg border bg-background p-4 sm:grid-cols-2 lg:grid-cols-4" onSubmit={(e) => e.preventDefault()}>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Search</span>
          <Input
            type="search"
            defaultValue={filters.search}
            placeholder="Name, number or phone"
            onChange={(e) => update("search", e.target.value)}
            autoCorrect="off"
            spellCheck={false}
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Status</span>
          <NativeSelect value={filters.status} onChange={(e) => update("status", e.target.value)}>
            <option value="">All</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </NativeSelect>
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Session</span>
          <NativeSelect value={filters.session} onChange={(e) => update("session", e.target.value)}>
            <option value="">All</option>
            {sessions.data?.results.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </NativeSelect>
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Class</span>
          <NativeSelect value={filters.class_applied} onChange={(e) => update("class_applied", e.target.value)}>
            <option value="">All</option>
            {classes.data?.results.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </NativeSelect>
        </label>
      </form>

      <div className="rounded-lg border bg-background">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Application</TableHead>
              <TableHead scope="col">Child</TableHead>
              <TableHead scope="col">Class</TableHead>
              <TableHead scope="col">Phone</TableHead>
              <TableHead scope="col">Submitted</TableHead>
              <TableHead scope="col">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.data?.results.map((a) => (
              <TableRow key={a.id}>
                <TableCell>
                  <Link to={`/staff/applications/${a.id}`} className="font-mono text-sm font-medium text-primary underline-offset-4 hover:underline">
                    {a.application_number}
                  </Link>
                </TableCell>
                <TableCell>{a.child_name}</TableCell>
                <TableCell>{a.class_name} <span className="text-muted-foreground">({a.session_name})</span></TableCell>
                <TableCell>{a.primary_phone}</TableCell>
                <TableCell>{formatDate(a.submitted_at)}</TableCell>
                <TableCell><StatusBadge status={a.status} /></TableCell>
              </TableRow>
            ))}
            {list.data && list.data.results.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">No applications match.</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      {list.isLoading && <p className="text-muted-foreground">Loading…</p>}
      {list.data && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">{list.data.count} applications</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={!list.data.previous} onClick={() => update("page", String(page - 1))}>Previous</Button>
            <Button variant="outline" size="sm" disabled={!list.data.next} onClick={() => update("page", String(page + 1))}>Next</Button>
          </div>
        </div>
      )}
    </div>
  );
}
