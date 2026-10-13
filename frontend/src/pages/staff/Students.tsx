import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { NativeSelect } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { STUDENT_STATUS_LABELS, formatDate } from "@/lib/labels";
import type { Paginated, SchoolClass, Section, StudentListItem } from "@/lib/types";

export default function Students() {
  const [params, setParams] = useSearchParams();
  const filters = {
    status: params.get("status") ?? "active",
    class: params.get("class") ?? "",
    section: params.get("section") ?? "",
    search: params.get("search") ?? "",
    page: params.get("page") ?? "1",
  };
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    next.set(key, value);
    if (!value && key !== "status") next.delete(key);
    if (key === "class") next.delete("section");
    if (key !== "page") next.delete("page");
    setParams(next, { replace: true });
  };

  const classes = useQuery({ queryKey: ["classes"], queryFn: () => api.get<Paginated<SchoolClass>>("/academics/classes/") });
  const sections = useQuery({
    queryKey: ["sections", "current", filters.class],
    queryFn: () => api.get<Paginated<Section>>("/academics/sections/", { school_class: filters.class }),
    enabled: Boolean(filters.class),
  });
  const list = useQuery({
    queryKey: ["students", filters],
    queryFn: () =>
      api.get<Paginated<StudentListItem>>("/students/", {
        status: filters.status,
        enrollments__section__school_class: filters.class,
        enrollments__section: filters.section,
        search: filters.search,
        page: filters.page,
        ordering: "first_name",
      }),
    placeholderData: keepPreviousData,
  });
  const page = Number(filters.page);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Students</h1>
      <form role="search" className="grid gap-3 rounded-lg border bg-background p-4 sm:grid-cols-2 lg:grid-cols-4" onSubmit={(e) => e.preventDefault()}>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Search</span>
          <Input
            type="search"
            defaultValue={filters.search}
            placeholder="Name, admission no. or parent phone"
            onChange={(e) => update("search", e.target.value)}
            autoCorrect="off"
            spellCheck={false}
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Status</span>
          <NativeSelect value={filters.status} onChange={(e) => update("status", e.target.value)}>
            <option value="">All</option>
            {Object.entries(STUDENT_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </NativeSelect>
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Class</span>
          <NativeSelect value={filters.class} onChange={(e) => update("class", e.target.value)}>
            <option value="">All</option>
            {classes.data?.results.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </NativeSelect>
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Section</span>
          <NativeSelect value={filters.section} onChange={(e) => update("section", e.target.value)} disabled={!filters.class}>
            <option value="">All</option>
            {sections.data?.results.map((s) => (
              <option key={s.id} value={s.id}>{s.name} ({s.session_name})</option>
            ))}
          </NativeSelect>
        </label>
      </form>

      <div className="rounded-lg border bg-background">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Admission no.</TableHead>
              <TableHead scope="col">Name</TableHead>
              <TableHead scope="col">Class</TableHead>
              <TableHead scope="col">Date of birth</TableHead>
              <TableHead scope="col">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.data?.results.map((s) => (
              <TableRow key={s.id}>
                <TableCell>
                  <Link to={`/staff/students/${s.id}`} className="font-mono text-sm font-medium text-primary underline-offset-4 hover:underline">
                    {s.admission_number}
                  </Link>
                </TableCell>
                <TableCell>{s.first_name} {s.last_name}</TableCell>
                <TableCell>{s.class_name ? `${s.class_name}${s.section_name ? ` ${s.section_name}` : ""}` : <span className="text-muted-foreground">Not enrolled this session</span>}</TableCell>
                <TableCell>{formatDate(s.date_of_birth)}</TableCell>
                <TableCell>{STUDENT_STATUS_LABELS[s.status] ?? s.status}</TableCell>
              </TableRow>
            ))}
            {list.data && list.data.results.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                  No students match. Students appear here once an application is admitted.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      {list.isLoading && <p className="text-muted-foreground">Loading…</p>}
      {list.isError && <p className="text-destructive">Could not load students: {list.error.message}</p>}
      {list.data && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">{list.data.count} students</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={!list.data.previous} onClick={() => update("page", String(page - 1))}>Previous</Button>
            <Button variant="outline" size="sm" disabled={!list.data.next} onClick={() => update("page", String(page + 1))}>Next</Button>
          </div>
        </div>
      )}
    </div>
  );
}
