import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { Field, NativeSelect } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/hooks/use-toast";
import { ALL, sectionLabel, useSections, useSessions } from "@/lib/academics";
import { ApiError, api } from "@/lib/api";
import { formatDate, formatTime } from "@/lib/labels";
import type { Paginated, PeriodSlot, SchoolClass, StaffUser, Subject, TeachingAssignment } from "@/lib/types";

import Timetable from "./Timetable";

function useTeachers() {
  return useQuery({
    queryKey: ["staff-users"],
    queryFn: () => api.get<StaffUser[]>("/auth/users/"),
    select: (users) => users.filter((u) => u.is_active && ["teacher", "principal", "admin"].includes(u.role)),
  });
}

function useSaver(keys: unknown[][]) {
  const queryClient = useQueryClient();
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const mutation = useMutation({
    mutationFn: ({ method, path, body }: { method: "post" | "patch" | "delete"; path: string; body?: unknown }) =>
      method === "delete" ? api.delete(path) : api[method](path, body),
    onSuccess: () => {
      setErrors({});
      keys.forEach((queryKey) => void queryClient.invalidateQueries({ queryKey }));
      toast({ title: "Saved" });
    },
    onError: (err) => setErrors(err instanceof ApiError ? err.fieldErrors : {}),
  });
  return { ...mutation, errors };
}

export default function Setup() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">School setup</h1>
      <Tabs defaultValue="sections">
        <TabsList className="flex h-auto flex-wrap">
          <TabsTrigger value="sections">Classes and teachers</TabsTrigger>
          <TabsTrigger value="subjects">Subject teachers</TabsTrigger>
          <TabsTrigger value="timetable">Timetable</TabsTrigger>
          <TabsTrigger value="periods">Bell times</TabsTrigger>
          <TabsTrigger value="subject-list">Subjects</TabsTrigger>
          <TabsTrigger value="sessions">Sessions</TabsTrigger>
        </TabsList>
        <TabsContent value="sections"><Sections /></TabsContent>
        <TabsContent value="subjects"><Assignments /></TabsContent>
        <TabsContent value="timetable"><Timetable /></TabsContent>
        <TabsContent value="periods"><Periods /></TabsContent>
        <TabsContent value="subject-list"><Subjects /></TabsContent>
        <TabsContent value="sessions"><Sessions /></TabsContent>
      </Tabs>
    </div>
  );
}

function SessionPicker({ value, onChange }: { value?: number; onChange: (id: number) => void }) {
  const sessions = useSessions();
  return (
    <label className="block space-y-1 text-sm sm:w-56">
      <span className="font-medium">Session</span>
      <NativeSelect value={value ?? ""} onChange={(e) => onChange(Number(e.target.value))}>
        {sessions.data?.map((s) => <option key={s.id} value={s.id}>{s.name}{s.is_current ? " (current)" : ""}</option>)}
      </NativeSelect>
    </label>
  );
}

function Sections() {
  const [chosen, setChosen] = useState<number>();
  const { sessionId, sections } = useSections(chosen);
  const classes = useQuery({
    queryKey: ["classes", "all"],
    queryFn: () => api.get<Paginated<SchoolClass>>("/academics/classes/", ALL).then((p) => p.results),
  });
  const teachers = useTeachers();
  const save = useSaver([["sections"], ["my-sections"]]);

  function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    save.mutate({ method: "post", path: "/academics/sections/", body: { session: sessionId, ...Object.fromEntries(f) } });
  }

  return (
    <Panel title="Classes, sections and class teachers">
      <SessionPicker value={sessionId} onChange={setChosen} />
      <p className="text-sm text-muted-foreground">The class teacher marks daily attendance for their section.</p>
      <ErrorNote error={sections.error ?? save.error} />
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-muted-foreground">
            <tr><th className="p-2">Section</th><th className="p-2">Students</th><th className="p-2">Capacity</th><th className="p-2">Class teacher</th></tr>
          </thead>
          <tbody>
            {sections.data?.map((s) => (
              <tr key={s.id} className="border-t">
                <td className="p-2 font-medium">{sectionLabel(s)}</td>
                <td className="p-2">{s.strength}</td>
                <td className="p-2">
                  <Input type="number" min={1} defaultValue={s.capacity} className="h-9 w-20" aria-label={`Capacity of ${sectionLabel(s)}`}
                    onBlur={(e) => Number(e.target.value) !== s.capacity && save.mutate({ method: "patch", path: `/academics/sections/${s.id}/`, body: { capacity: Number(e.target.value) } })} />
                </td>
                <td className="p-2">
                  <NativeSelect className="h-9" aria-label={`Class teacher of ${sectionLabel(s)}`} value={s.class_teacher ?? ""}
                    onChange={(e) => save.mutate({ method: "patch", path: `/academics/sections/${s.id}/`, body: { class_teacher: e.target.value ? Number(e.target.value) : null } })}>
                    <option value="">Not assigned</option>
                    {teachers.data?.map((t) => <option key={t.id} value={t.id}>{t.full_name}</option>)}
                  </NativeSelect>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <form onSubmit={add} className="flex flex-wrap items-end gap-3 border-t pt-3">
        <Field label="Class" required error={save.errors.school_class}>
          <NativeSelect name="school_class" className="w-44">
            {classes.data?.filter((c) => c.is_active).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </NativeSelect>
        </Field>
        <Field label="Section name" required hint="e.g. B" error={save.errors.name}>
          <Input name="name" maxLength={10} className="w-24" />
        </Field>
        <Button type="submit" disabled={save.isPending}>Add section</Button>
      </form>
    </Panel>
  );
}

function Assignments() {
  const [sectionId, setSectionId] = useState<number>();
  const { sections } = useSections();
  const subjects = useQuery({ queryKey: ["subjects"], queryFn: () => api.get<Subject[]>("/academics/subjects/") });
  const teachers = useTeachers();
  const current = sectionId ?? sections.data?.[0]?.id;
  const assignments = useQuery({
    queryKey: ["teaching-assignments", current],
    queryFn: () => api.get<TeachingAssignment[]>("/academics/teaching-assignments/", { section: current }),
    enabled: Boolean(current),
  });
  const save = useSaver([["teaching-assignments"], ["my-sections"]]);

  function setTeacher(subject: number, teacher: string) {
    const existing = assignments.data?.find((a) => a.subject === subject);
    if (!teacher && existing) save.mutate({ method: "delete", path: `/academics/teaching-assignments/${existing.id}/` });
    else if (existing) save.mutate({ method: "patch", path: `/academics/teaching-assignments/${existing.id}/`, body: { teacher: Number(teacher) } });
    else if (teacher) save.mutate({ method: "post", path: "/academics/teaching-assignments/", body: { section: current, subject, teacher: Number(teacher) } });
  }

  return (
    <Panel title="Who teaches each subject">
      <label className="block space-y-1 text-sm sm:w-56">
        <span className="font-medium">Section (current session)</span>
        <NativeSelect value={current ?? ""} onChange={(e) => setSectionId(Number(e.target.value))}>
          {sections.data?.map((s) => <option key={s.id} value={s.id}>{sectionLabel(s)}</option>)}
        </NativeSelect>
      </label>
      <p className="text-sm text-muted-foreground">A subject teacher can set tests and enter marks for that subject in this section.</p>
      <ErrorNote error={assignments.error ?? save.error} />
      <ul className="divide-y">
        {subjects.data?.filter((s) => s.is_active).map((s) => (
          <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span className="font-medium">{s.name}</span>
            <NativeSelect className="h-9 w-56" aria-label={`Teacher for ${s.name}`} disabled={save.isPending}
              value={assignments.data?.find((a) => a.subject === s.id)?.teacher ?? ""} onChange={(e) => setTeacher(s.id, e.target.value)}>
              <option value="">Not taught / not assigned</option>
              {teachers.data?.map((t) => <option key={t.id} value={t.id}>{t.full_name}</option>)}
            </NativeSelect>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function Subjects() {
  const subjects = useQuery({ queryKey: ["subjects"], queryFn: () => api.get<Subject[]>("/academics/subjects/") });
  const save = useSaver([["subjects"]]);
  function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const name = String(new FormData(form).get("name")).trim();
    const code = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 20);
    save.mutate({ method: "post", path: "/academics/subjects/", body: { name, code, order: (subjects.data?.length ?? 0) + 1 } }, { onSuccess: () => form.reset() });
  }
  return (
    <Panel title="Subjects">
      <ErrorNote error={subjects.error ?? save.error} />
      <ul className="divide-y">
        {subjects.data?.map((s) => (
          <li key={s.id} className="flex items-center justify-between gap-2 py-2">
            <span className={s.is_active ? "" : "text-muted-foreground line-through"}>{s.name}</span>
            <Button variant="outline" size="sm" disabled={save.isPending}
              onClick={() => save.mutate({ method: "patch", path: `/academics/subjects/${s.id}/`, body: { is_active: !s.is_active } })}>
              {s.is_active ? "Stop using" : "Use again"}
            </Button>
          </li>
        ))}
      </ul>
      <form onSubmit={add} className="flex flex-wrap items-end gap-3 border-t pt-3">
        <Field label="New subject" required error={save.errors.name ?? save.errors.code}><Input name="name" maxLength={60} className="w-56" /></Field>
        <Button type="submit" disabled={save.isPending}>Add subject</Button>
      </form>
    </Panel>
  );
}

function Periods() {
  const periods = useQuery({ queryKey: ["periods"], queryFn: () => api.get<PeriodSlot[]>("/academics/periods/") });
  const save = useSaver([["periods"]]);
  function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    save.mutate({ method: "post", path: "/academics/periods/", body: Object.fromEntries(new FormData(form)) }, { onSuccess: () => form.reset() });
  }
  return (
    <Panel title="Bell times">
      <ErrorNote error={periods.error ?? save.error} />
      <ul className="divide-y">
        {periods.data?.map((p) => (
          <li key={p.id} className="flex items-center justify-between gap-2 py-2">
            <span>Period {p.number}: {formatTime(p.start_time)}–{formatTime(p.end_time)} {p.label && <Badge variant="secondary">{p.label}</Badge>}</span>
            <Button variant="ghost" size="sm" className="text-destructive" disabled={save.isPending}
              onClick={() => window.confirm(`Remove period ${p.number}? Its timetable entries are removed too.`) && save.mutate({ method: "delete", path: `/academics/periods/${p.id}/` })}>
              Remove
            </Button>
          </li>
        ))}
      </ul>
      <form onSubmit={add} className="flex flex-wrap items-end gap-3 border-t pt-3">
        <Field label="Period number" required error={save.errors.number}><Input name="number" type="number" min={1} className="w-24" /></Field>
        <Field label="Starts" required error={save.errors.start_time}><Input name="start_time" type="time" className="w-32" /></Field>
        <Field label="Ends" required error={save.errors.end_time}><Input name="end_time" type="time" className="w-32" /></Field>
        <Field label="Label" error={save.errors.label}><Input name="label" maxLength={30} className="w-36" /></Field>
        <Button type="submit" disabled={save.isPending}>Add period</Button>
      </form>
    </Panel>
  );
}

function Sessions() {
  const sessions = useSessions();
  const save = useSaver([["sessions"]]);
  function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    save.mutate({ method: "post", path: "/academics/sessions/", body: Object.fromEntries(new FormData(form)) }, { onSuccess: () => form.reset() });
  }
  return (
    <Panel title="Academic sessions">
      <ErrorNote error={sessions.error ?? save.error} />
      <ul className="divide-y">
        {sessions.data?.map((s) => (
          <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span>
              <span className="font-medium">{s.name}</span>{" "}
              <span className="text-sm text-muted-foreground">{formatDate(s.start_date)} to {formatDate(s.end_date)}</span>{" "}
              {s.is_current && <Badge>Current</Badge>} {s.admissions_open && <Badge variant="secondary">Admissions open</Badge>}
            </span>
            <span className="flex flex-wrap gap-2">
              {!s.is_current && (
                <Button variant="outline" size="sm" disabled={save.isPending}
                  onClick={() => window.confirm(`Make ${s.name} the current session? Attendance, marks and timetables switch to it.`) &&
                    save.mutate({ method: "patch", path: `/academics/sessions/${s.id}/`, body: { is_current: true } })}>
                  Make current
                </Button>
              )}
              <Button variant="outline" size="sm" disabled={save.isPending}
                onClick={() => save.mutate({ method: "patch", path: `/academics/sessions/${s.id}/`, body: { admissions_open: !s.admissions_open } })}>
                {s.admissions_open ? "Close admissions" : "Open admissions"}
              </Button>
            </span>
          </li>
        ))}
      </ul>
      <form onSubmit={add} className="flex flex-wrap items-end gap-3 border-t pt-3">
        <Field label="Name" required hint="e.g. 2027-28" error={save.errors.name}><Input name="name" maxLength={20} className="w-28" /></Field>
        <Field label="Starts" required error={save.errors.start_date}><Input name="start_date" type="date" /></Field>
        <Field label="Ends" required error={save.errors.end_date}><Input name="end_date" type="date" /></Field>
        <Button type="submit" disabled={save.isPending}>Add session</Button>
      </form>
    </Panel>
  );
}
