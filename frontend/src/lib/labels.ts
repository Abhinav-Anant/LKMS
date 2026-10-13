import type { ApplicationStatus, Verification } from "./types";

export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  submitted: "Submitted",
  under_review: "Under review",
  documents_requested: "Documents requested",
  approved: "Approved",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  admitted: "Admitted",
};

export const VERIFICATION_LABELS: Record<Verification, string> = {
  pending: "Not checked yet",
  verified: "Verified",
  rejected: "Not acceptable",
};

export const GENDERS = [
  { value: "M", label: "Male" },
  { value: "F", label: "Female" },
  { value: "O", label: "Other" },
];

export const CATEGORIES = [
  { value: "general", label: "General" },
  { value: "obc", label: "OBC" },
  { value: "mbc", label: "MBC" },
  { value: "sc", label: "SC" },
  { value: "st", label: "ST" },
  { value: "ews", label: "EWS" },
];

export const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

export const RELATIONSHIPS: Record<string, string> = { father: "Father", mother: "Mother", guardian: "Guardian" };

export function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value.length === 10 ? `${value}T00:00:00` : value);
  return date.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "";
  return new Date(value).toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" });
}

export function formatBytes(size: number): string {
  return size > 1024 * 1024 ? `${(size / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(size / 1024)} KB`;
}

export const STUDENT_STATUS_LABELS: Record<string, string> = {
  active: "Studying",
  left: "Left school",
  tc_issued: "TC issued",
  alumni: "Passed out",
};

export const ENROLLMENT_STATUS_LABELS: Record<string, string> = {
  active: "Studying",
  promoted: "Promoted",
  detained: "Detained",
  left: "Left school",
};
