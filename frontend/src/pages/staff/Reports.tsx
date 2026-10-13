import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { NativeSelect } from "@/components/Field";
import { ErrorNote } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useSessions } from "@/lib/academics";
import type { ExamTerm, ReportInfo, ReportTable } from "@/lib/types";

function csvCell(value: unknown) {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** Download the table as CSV. The byte-order mark makes Excel read the file as UTF-8. */
function downloadCsv(table: ReportTable) {
  const lines = [table.columns.map((c) => csvCell(c.label)).join(",")];
  for (const row of table.rows) lines.push(table.columns.map((c) => csvCell(row[c.key])).join(","));
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${table.title.replace(/[^\w-]+/g, "-").replace(/-+$/, "")}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

export default function Reports() {
  const list = useQuery({ queryKey: ["report-list"], queryFn: () => api.get<ReportInfo[]>("/reports/tables/") });
  const sessions = useSessions();
  const terms = useQuery({ queryKey: ["exam-terms", "all"], queryFn: () => api.get<ExamTerm[]>("/exams/terms/") });
  const [name, setName] = useState("strength");
  const [session, setSession] = useState("");
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [term, setTerm] = useState("");
  const info = list.data?.find((r) => r.name === name);
  const params: Record<string, string> = {};
  if (info?.params.includes("session") && session) params.session = session;
  if (info?.params.includes("month")) params.month = month;
  if (info?.params.includes("term")) params.term = term;
  const ready = Boolean(info) && (!info?.params.includes("term") || Boolean(term));
  const table = useQuery({
    queryKey: ["report", name, params],
    queryFn: () => api.get<ReportTable>(`/reports/tables/${name}/`, params),
    enabled: ready,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Reports</h1>
      <div className="flex flex-wrap items-center gap-2">
        <NativeSelect aria-label="Report" className="h-10 w-96 max-w-full" value={name} onChange={(e) => setName(e.target.value)}>
          {list.data?.map((r) => <option key={r.name} value={r.name}>{r.title}</option>)}
        </NativeSelect>
        {info?.params.includes("session") && (
          <NativeSelect aria-label="Session" className="h-10 w-36" value={session} onChange={(e) => setSession(e.target.value)}>
            <option value="">Current session</option>
            {sessions.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </NativeSelect>
        )}
        {info?.params.includes("month") && (
          <Input aria-label="Month" type="month" className="h-10 w-44" value={month} onChange={(e) => setMonth(e.target.value)} />
        )}
        {info?.params.includes("term") && (
          <NativeSelect aria-label="Exam term" className="h-10 w-56" value={term} onChange={(e) => setTerm(e.target.value)}>
            <option value="">Choose an exam term…</option>
            {terms.data?.map((t) => <option key={t.id} value={t.id}>{t.name} {t.session_name}</option>)}
          </NativeSelect>
        )}
        {table.data && (
          <Button variant="outline" onClick={() => downloadCsv(table.data)} disabled={table.data.rows.length === 0}>
            Download CSV
          </Button>
        )}
        {table.data && <Button variant="ghost" onClick={() => window.print()}>Print</Button>}
      </div>
      <ErrorNote error={list.error ?? table.error} />
      {table.data && (
        <section aria-label={table.data.title} className="space-y-2">
          <h2 className="font-semibold">{table.data.title}</h2>
          <div className="overflow-x-auto rounded-lg border bg-background">
            <table className="w-full text-sm">
              <thead className="text-left text-muted-foreground">
                <tr>{table.data.columns.map((c) => <th key={c.key} className="p-2">{c.label}</th>)}</tr>
              </thead>
              <tbody>
                {table.data.rows.map((row, i) => (
                  <tr key={i} className="border-t">
                    {table.data.columns.map((c, j) => (
                      <td key={c.key} className={j === 0 ? "p-2 font-medium" : "p-2"}>{row[c.key] ?? "–"}</td>
                    ))}
                  </tr>
                ))}
                {table.data.rows.length === 0 && (
                  <tr><td colSpan={table.data.columns.length} className="p-6 text-center text-muted-foreground">Nothing to show.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}
      <p className="text-sm text-muted-foreground">Fee collection by day and the list of fee defaulters are under Fees, Reports.</p>
    </div>
  );
}
