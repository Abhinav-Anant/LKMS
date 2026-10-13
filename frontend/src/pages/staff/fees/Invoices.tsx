import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { NativeSelect } from "@/components/Field";
import { ErrorNote } from "@/components/Panel";
import { InvoiceBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { INVOICE_STATUS_LABELS, formatDate, formatMoney, todayISO } from "@/lib/labels";
import type { Installment, InvoiceListItem, Paginated, SchoolClass } from "@/lib/types";

import { FeesNav } from "./FeesNav";

export default function Invoices() {
  const [params, setParams] = useSearchParams();
  const filters = {
    status: params.get("status") ?? "",
    installment: params.get("installment") ?? "",
    school_class: params.get("school_class") ?? "",
    student: params.get("student") ?? "",
    overdue: params.get("overdue") ?? "",
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

  const installments = useQuery({ queryKey: ["installments"], queryFn: () => api.get<Installment[]>("/fees/installments/") });
  const classes = useQuery({ queryKey: ["classes"], queryFn: () => api.get<Paginated<SchoolClass>>("/academics/classes/") });
  const list = useQuery({
    queryKey: ["invoices", filters],
    queryFn: () => api.get<Paginated<InvoiceListItem>>("/fees/invoices/", { ...filters, ordering: "due_date" }),
    placeholderData: keepPreviousData,
  });
  const page = Number(filters.page);
  const today = todayISO();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Fees</h1>
      <FeesNav />
      <form role="search" className="grid gap-3 rounded-lg border bg-background p-4 sm:grid-cols-2 lg:grid-cols-5" onSubmit={(e) => e.preventDefault()}>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Search</span>
          <Input type="search" defaultValue={filters.search} placeholder="Name, admission or invoice no." onChange={(e) => update("search", e.target.value)} autoCorrect="off" spellCheck={false} />
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Status</span>
          <NativeSelect value={filters.status} onChange={(e) => update("status", e.target.value)}>
            <option value="">All</option>
            {Object.entries(INVOICE_STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </NativeSelect>
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Installment</span>
          <NativeSelect value={filters.installment} onChange={(e) => update("installment", e.target.value)}>
            <option value="">All</option>
            {installments.data?.map((i) => <option key={i.id} value={i.id}>{i.name} ({i.session_name})</option>)}
          </NativeSelect>
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Class</span>
          <NativeSelect value={filters.school_class} onChange={(e) => update("school_class", e.target.value)}>
            <option value="">All</option>
            {classes.data?.results.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </NativeSelect>
        </label>
        <label className="flex items-end gap-2 pb-3 text-sm">
          <input type="checkbox" className="h-4 w-4" checked={filters.overdue === "1"} onChange={(e) => update("overdue", e.target.checked ? "1" : "")} />
          <span className="font-medium">Overdue only</span>
        </label>
      </form>
      {filters.student && (
        <p className="text-sm">
          Showing one student's invoices. <button type="button" className="text-primary underline" onClick={() => update("student", "")}>Show all</button>
        </p>
      )}

      <div className="overflow-x-auto rounded-lg border bg-background">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Invoice</TableHead>
              <TableHead scope="col">Student</TableHead>
              <TableHead scope="col">Class</TableHead>
              <TableHead scope="col">Due</TableHead>
              <TableHead scope="col" className="text-right">Amount</TableHead>
              <TableHead scope="col" className="text-right">Balance</TableHead>
              <TableHead scope="col">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.data?.results.map((inv) => (
              <TableRow key={inv.id}>
                <TableCell>
                  <Link to={`/staff/fees/invoices/${inv.id}`} className="font-mono text-sm font-medium text-primary underline-offset-4 hover:underline">{inv.number}</Link>
                  <div className="text-xs text-muted-foreground">{inv.installment_name}</div>
                </TableCell>
                <TableCell>{inv.student_name} <span className="text-muted-foreground">({inv.admission_number})</span></TableCell>
                <TableCell>{inv.class_name}</TableCell>
                <TableCell>{formatDate(inv.due_date)}</TableCell>
                <TableCell className="text-right tabular-nums">{formatMoney(inv.net_amount)}</TableCell>
                <TableCell className="text-right tabular-nums">{formatMoney(inv.balance)}</TableCell>
                <TableCell><InvoiceBadge status={inv.status} overdue={inv.due_date < today} /></TableCell>
              </TableRow>
            ))}
            {list.data && list.data.results.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                  No invoices match. Invoices are created from Fee setup, one installment at a time.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      {list.isLoading && <p className="text-muted-foreground">Loading…</p>}
      <ErrorNote error={list.error} />
      {list.data && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">{list.data.count} invoices</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={!list.data.previous} onClick={() => update("page", String(page - 1))}>Previous</Button>
            <Button variant="outline" size="sm" disabled={!list.data.next} onClick={() => update("page", String(page + 1))}>Next</Button>
          </div>
        </div>
      )}
    </div>
  );
}
