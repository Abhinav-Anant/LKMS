import { useState } from "react";

import { Button } from "@/components/ui/button";
import { VerificationBadge } from "@/components/StatusBadge";
import { ApiError, api } from "@/lib/api";
import type { DocumentType, Verification } from "@/lib/types";

export interface UploadedState {
  verification: Verification;
  note?: string;
  fileName?: string;
}

interface Props {
  documentTypes: DocumentType[];
  uploaded: Record<number, UploadedState>;
  /** Path to POST the file to, e.g. /admissions/public/LK-.../documents/ */
  uploadPath: string;
  headers?: Record<string, string>;
  onUploaded: (documentTypeId: number, state: UploadedState) => void;
  maxSizeMb?: number;
}

const ACCEPT: Record<string, string> = { pdf: "application/pdf,.pdf", jpg: "image/jpeg,.jpg,.jpeg", png: "image/png,.png" };

export function DocumentUploader({ documentTypes, uploaded, uploadPath, headers, onUploaded, maxSizeMb = 5 }: Props) {
  const [busy, setBusy] = useState<number | null>(null);
  const [errors, setErrors] = useState<Record<number, string>>({});

  async function upload(type: DocumentType, file: File | undefined) {
    if (!file) return;
    if (file.size > maxSizeMb * 1024 * 1024) {
      setErrors((e) => ({ ...e, [type.id]: `The file is larger than ${maxSizeMb} MB. Take a smaller photo or scan.` }));
      return;
    }
    setBusy(type.id);
    setErrors((e) => ({ ...e, [type.id]: "" }));
    const body = new FormData();
    body.append("document_type", String(type.id));
    body.append("file", file);
    try {
      await api.post(uploadPath, body, { headers, auth: !headers });
      onUploaded(type.id, { verification: "pending", fileName: file.name });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Upload failed. Check your connection and try again.";
      setErrors((e) => ({ ...e, [type.id]: message }));
    } finally {
      setBusy(null);
    }
  }

  return (
    <ul className="divide-y rounded-lg border">
      {documentTypes.map((type) => {
        const state = uploaded[type.id];
        const inputId = `doc-${type.id}`;
        const errorId = `${inputId}-error`;
        return (
          <li key={type.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p className="font-medium">
                {type.name}
                {type.is_required ? (
                  <span className="text-destructive"> *</span>
                ) : (
                  <span className="font-normal text-muted-foreground"> (optional)</span>
                )}
              </p>
              {type.description && <p className="text-sm text-muted-foreground">{type.description}</p>}
              <p className="text-xs text-muted-foreground">
                {type.allowed_formats.map((f) => f.toUpperCase()).join(", ")}, up to {maxSizeMb} MB
              </p>
              {state && (
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <VerificationBadge value={state.verification} />
                  {state.fileName && <span className="text-muted-foreground">{state.fileName}</span>}
                  {state.note && <span className="text-destructive">{state.note}</span>}
                </div>
              )}
              {errors[type.id] && (
                <p id={errorId} role="alert" className="text-sm font-medium text-destructive">
                  {errors[type.id]}
                </p>
              )}
            </div>
            <div className="shrink-0">
              <input
                id={inputId}
                type="file"
                className="sr-only"
                accept={type.allowed_formats.map((f) => ACCEPT[f]).join(",")}
                aria-describedby={errors[type.id] ? errorId : undefined}
                onChange={(e) => {
                  void upload(type, e.target.files?.[0]);
                  e.target.value = "";
                }}
                disabled={busy !== null}
              />
              <Button asChild variant={state ? "outline" : "default"} disabled={busy !== null}>
                <label htmlFor={inputId} className="cursor-pointer">
                  {busy === type.id ? "Uploading…" : state ? "Replace file" : "Choose file"}
                  <span className="sr-only"> for {type.name}</span>
                </label>
              </Button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
