import { LOGO_URL, type PublicSchool } from "@/lib/school";

/** The school's logo (if it has one) and name, for page headers. */
export function SchoolName({ school, className }: { school?: PublicSchool; className?: string }) {
  return (
    <span className={className ?? "inline-flex items-center gap-2"}>
      {school?.has_logo && <img src={LOGO_URL} alt="" className="h-8 w-8 rounded object-contain" />}
      <span>{school?.name ?? ""}</span>
    </span>
  );
}
