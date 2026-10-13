import { STATUS_LABELS, VERIFICATION_LABELS } from "@/lib/labels";
import type { ApplicationStatus, Verification } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS_STYLE: Record<ApplicationStatus, string> = {
  submitted: "bg-muted text-foreground",
  under_review: "bg-blue-50 text-blue-800 ring-blue-200",
  documents_requested: "bg-amber-50 text-amber-900 ring-amber-200",
  approved: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  admitted: "bg-emerald-600 text-white ring-emerald-600",
  rejected: "bg-red-50 text-red-800 ring-red-200",
  withdrawn: "bg-muted text-muted-foreground",
};

export function StatusBadge({ status }: { status: ApplicationStatus }) {
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ring-border", STATUS_STYLE[status])}>
      {STATUS_LABELS[status]}
    </span>
  );
}

const VERIFICATION_STYLE: Record<Verification, string> = {
  pending: "bg-muted text-foreground",
  verified: "bg-emerald-50 text-emerald-800",
  rejected: "bg-red-50 text-red-800",
};

const VERIFICATION_ICON: Record<Verification, string> = { pending: "•", verified: "✓", rejected: "✕" };

export function VerificationBadge({ value }: { value: Verification }) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium", VERIFICATION_STYLE[value])}>
      <span aria-hidden="true">{VERIFICATION_ICON[value]}</span>
      {VERIFICATION_LABELS[value]}
    </span>
  );
}
