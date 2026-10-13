import { useId, type ReactElement, cloneElement } from "react";

import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface FieldProps {
  label: string;
  required?: boolean;
  hint?: string;
  error?: string[] | string;
  className?: string;
  children: ReactElement<{ id?: string; "aria-describedby"?: string; "aria-invalid"?: boolean; required?: boolean }>;
}

/** Label above the control, optional hint, and an error linked with aria-describedby. */
export function Field({ label, required, hint, error, className, children }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errors = Array.isArray(error) ? error : error ? [error] : [];
  const errorId = errors.length ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={cn("space-y-1.5", className)}>
      <Label htmlFor={id} className="text-sm font-medium">
        {label}
        {required ? (
          <span className="text-destructive" aria-hidden="true">
            {" "}
            *
          </span>
        ) : (
          <span className="font-normal text-muted-foreground"> (optional)</span>
        )}
      </Label>
      {cloneElement(children, {
        id,
        required,
        "aria-describedby": describedBy,
        "aria-invalid": errors.length ? true : undefined,
      })}
      {hint && (
        <p id={hintId} className="text-sm text-muted-foreground">
          {hint}
        </p>
      )}
      {errors.length > 0 && (
        <p id={errorId} className="text-sm font-medium text-destructive">
          {errors.join(" ")}
        </p>
      )}
    </div>
  );
}

/** Native select styled like the shadcn input. Native keeps autofill, keyboard and mobile pickers working. */
export function NativeSelect(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cn(
        "flex h-11 w-full rounded-md border border-input bg-background px-3 text-base ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
        props.className,
      )}
    />
  );
}
