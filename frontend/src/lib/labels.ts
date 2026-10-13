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

export const INVOICE_STATUS_LABELS: Record<string, string> = {
  unpaid: "Unpaid",
  partly_paid: "Partly paid",
  paid: "Paid",
  cancelled: "Cancelled",
};

export const PAYMENT_MODES = [
  { value: "cash", label: "Cash" },
  { value: "cheque", label: "Cheque" },
  { value: "bank_transfer", label: "Bank transfer" },
  { value: "upi", label: "UPI to school account" },
];

export const UPI_STATUS_LABELS: Record<string, string> = {
  pending: "Waiting to be checked",
  approved: "Verified and receipted",
  rejected: "Not verified",
};

export const CONCESSION_STATUS_LABELS: Record<string, string> = {
  pending: "Waiting for approval",
  approved: "Approved",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

const rupee = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 0, maximumFractionDigits: 2 });

export function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "";
  return rupee.format(Number(value));
}

/** Today's date in the browser's time zone as YYYY-MM-DD. */
export function todayISO(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

export const ATTENDANCE_LABELS: Record<string, string> = {
  present: "Present",
  absent: "Absent",
  late: "Late",
  leave: "On leave",
};

export const WEEKDAYS: [number, string][] = [
  [1, "Monday"],
  [2, "Tuesday"],
  [3, "Wednesday"],
  [4, "Thursday"],
  [5, "Friday"],
  [6, "Saturday"],
];

export const ROLE_LABELS: Record<string, string> = {
  admin: "Administrator",
  principal: "Principal",
  office: "Office staff",
  accountant: "Accountant",
  teacher: "Teacher",
  parent: "Parent",
};

/** "08:00:00" to "8:00" */
export function formatTime(value: string): string {
  const [h, m] = value.split(":");
  return `${Number(h)}:${m}`;
}
