import { useQuery } from "@tanstack/react-query";

import { api } from "./api";
import type { Child } from "./types";

export function useChildren() {
  return useQuery({ queryKey: ["parent-children"], queryFn: () => api.get<Child[]>("/parent/children/") });
}
