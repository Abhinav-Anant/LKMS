import { useQuery } from "@tanstack/react-query";

import { api } from "./api";
import type { AcademicSession, Paginated, SectionDetail } from "./types";

export const ALL = { page_size: 500 };

export function useSessions() {
  return useQuery({
    queryKey: ["sessions", "all"],
    queryFn: () => api.get<Paginated<AcademicSession>>("/academics/sessions/", ALL).then((p) => p.results),
  });
}

/** Sections of one session (the current session when none is given), in class order. */
export function useSections(sessionId?: number) {
  const sessions = useSessions();
  const id = sessionId ?? sessions.data?.find((s) => s.is_current)?.id;
  const sections = useQuery({
    queryKey: ["sections", id],
    queryFn: () => api.get<Paginated<SectionDetail>>("/academics/sections/", { ...ALL, session: id }).then((p) => p.results),
    enabled: Boolean(id),
  });
  return { sessions, sessionId: id, sections };
}

export const sectionLabel = (s: { class_name: string; name: string }) => `${s.class_name} ${s.name}`;
