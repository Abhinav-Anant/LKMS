import { useQuery } from "@tanstack/react-query";

import { api } from "./api";

export interface PublicSchool {
  name: string;
  address: string;
  district: string;
  state: string;
  pincode: string;
  phone: string;
  email: string;
  website: string;
  board: string;
}

export function useSchool() {
  const { data } = useQuery({
    queryKey: ["school"],
    queryFn: () => api.get<PublicSchool>("/school/"),
    staleTime: 60 * 60 * 1000,
  });
  return data;
}
