import { useQueryClient } from "@tanstack/react-query";
import { unzipSync } from "fflate";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { Field } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "@/hooks/use-toast";
import { ApiError, api, fetchFileUrl } from "@/lib/api";

interface ImportReport {
  session: string | null;
  total: number;
  ok: boolean;
  imported: boolean;
  errors: { row: number; column: string; message: string }[];
  students: { row: number; name: string; admission_number: string; class: string; photo: string }[];
  new_sections: string[];
  photos_matched: number;
  photos_unused: string[];
}

interface PhotoResult {
  saved: { file: string; admission_number: string; name: string }[];
  skipped: string[];
  unmatched: string[];
  errors: { file: string; message: string }[];
}

const PHOTO = /\.(jpe?g|png)$/i;
// Nginx takes requests up to 10 MB; stay well under it.
const BATCH_BYTES = 7 * 1024 * 1024;
const BATCH_FILES = 25;

const baseName = (path: string) => path.split(/[\\/]/).pop() ?? path;

/** The photos the user picked: image files as they are, ZIP files unpacked here in the browser. */
async function collectPhotos(files: File[]): Promise<File[]> {
  const out: File[] = [];
  for (const file of files) {
    if (/\.zip$/i.test(file.name)) {
      const entries = unzipSync(new Uint8Array(await file.arrayBuffer()), {
        filter: (f) => PHOTO.test(f.name) && !f.name.startsWith("__MACOSX/") && !baseName(f.name).startsWith("."),
      });
      for (const [path, bytes] of Object.entries(entries)) {
        const type = /\.png$/i.test(path) ? "image/png" : "image/jpeg";
        out.push(new File([bytes], baseName(path), { type }));
      }
    } else if (PHOTO.test(file.name)) {
      out.push(file);
    }
  }
  return out;
}

/** Send photos in small batches. Each file is sent under `name` (an admission number plus extension). */
async function uploadPhotos(items: { file: File; name: string }[], replace: boolean, onProgress: (done: number) => void) {
  const total: PhotoResult = { saved: [], skipped: [], unmatched: [], errors: [] };
  let batch: typeof items = [];
  let bytes = 0;
  let done = 0;
  const flush = async () => {
    if (!batch.length) return;
    const body = new FormData();
    for (const item of batch) body.append("photos", item.file, item.name);
    body.append("replace", String(replace));
    try {
      const result = await api.post<PhotoResult>("/students/import/photos/", body);
      total.saved.push(...result.saved);
      total.skipped.push(...result.skipped);
      total.unmatched.push(...result.unmatched);
      total.errors.push(...result.errors);
    } catch (err) {
      for (const item of batch) total.errors.push({ file: item.name, message: err instanceof Error ? err.message : "Could not upload" });
    }
    done += batch.length;
    onProgress(done);
    batch = [];
    bytes = 0;
  };
  for (const item of items) {
    if (batch.length && (bytes + item.file.size > BATCH_BYTES || batch.length >= BATCH_FILES)) await flush();
    batch.push(item);
    bytes += item.file.size;
  }
  await flush();
  return total;
}

async function downloadSample() {
  const url = await fetchFileUrl("/students/import/");
  const link = document.createElement("a");
  link.href = url;
  link.download = "student-import-sample.xlsx";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

/** Bulk import of students and their photos (administrator and principal). */
export default function StudentImport() {
  const queryClient = useQueryClient();
  const [sheet, setSheet] = useState<File | null>(null);
  const [photos, setPhotos] = useState<File[]>([]);
  const [reading, setReading] = useState(false);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [busy, setBusy] = useState<"" | "check" | "import" | "photos">("");
  const [progress, setProgress] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [photoResult, setPhotoResult] = useState<PhotoResult | null>(null);
  const [picker, setPicker] = useState(0);

  const pickPhotos = async (list: FileList | null) => {
    setReport(null);
    setReading(true);
    try {
      setPhotos(await collectPhotos(Array.from(list ?? [])));
    } catch {
      setError(new Error("The ZIP file could not be opened. Make it again and retry."));
    } finally {
      setReading(false);
    }
  };

  const send = async (commit: boolean) => {
    if (!sheet) return null;
    const body = new FormData();
    body.append("file", sheet);
    if (photos.length) body.append("photo_names", JSON.stringify(photos.map((p) => p.name)));
    if (commit) body.append("commit", "true");
    try {
      return await api.post<ImportReport>("/students/import/", body);
    } catch (err) {
      // A rejected import comes back as a report too.
      if (err instanceof ApiError && err.data && typeof err.data === "object" && "errors" in err.data) return err.data as ImportReport;
      throw err;
    }
  };

  const check = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setPhotoResult(null);
    setBusy("check");
    try {
      setReport(await send(false));
    } catch (err) {
      setError(err);
      setReport(null);
    } finally {
      setBusy("");
    }
  };

  const runImport = async () => {
    setError(null);
    setBusy("import");
    setProgress("Saving students…");
    try {
      const result = await send(true);
      setReport(result);
      if (!result?.imported) return;
      const byName = new Map(photos.map((p) => [p.name.toLowerCase(), p]));
      const items = result.students
        .filter((s) => s.photo && byName.has(s.photo.toLowerCase()))
        .map((s) => {
          const file = byName.get(s.photo.toLowerCase())!;
          return { file, name: `${s.admission_number}.${/\.png$/i.test(file.name) ? "png" : "jpg"}` };
        });
      if (items.length) {
        setProgress(`Uploading photos 0 of ${items.length}…`);
        setPhotoResult(await uploadPhotos(items, true, (n) => setProgress(`Uploading photos ${n} of ${items.length}…`)));
      }
      void queryClient.invalidateQueries({ queryKey: ["students"] });
      toast({ title: `${result.total} students imported` });
      setSheet(null);
      setPhotos([]);
      setPicker((n) => n + 1);
    } catch (err) {
      setError(err);
    } finally {
      setBusy("");
      setProgress("");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">Import students</h1>
        <Button asChild variant="outline"><Link to="/staff/students">Back to students</Link></Button>
      </div>
      <p className="text-muted-foreground">
        Add many students at once from an Excel sheet, with their photos. Use this when starting with LKMS for children already
        in the school. New admissions should still come through the admission form.
      </p>

      <Panel title="1. Get the sample file">
        <p className="text-sm">
          The sample has the columns LKMS needs, two example rows, help on each column and drop-down lists of your classes.
          Fill one row per student and delete the examples. Columns marked * are required, including the parent's Aadhaar.
        </p>
        <Button type="button" variant="outline" onClick={() => downloadSample().catch(setError)}>Download sample (.xlsx)</Button>
      </Panel>

      <Panel title="2. Upload the sheet and photos">
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={check}>
          <Field label="Filled-in sheet" required hint="The sample file (.xlsx) or a CSV with the same column names.">
            <Input key={`s${picker}`} type="file" accept=".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
              onChange={(e) => { setSheet(e.target.files?.[0] ?? null); setReport(null); }} />
          </Field>
          <Field label="Photos" hint="A ZIP file, or select many JPEG/PNG photos. Name each by admission number (0101.jpg) or write its name in the Photo File column.">
            <Input key={`p${picker}`} type="file" multiple accept=".zip,application/zip,image/jpeg,image/png"
              onChange={(e) => void pickPhotos(e.target.files)} />
          </Field>
          <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
            <Button type="submit" disabled={!sheet || reading || Boolean(busy)}>{busy === "check" ? "Checking…" : "Check sheet"}</Button>
            {reading && <span className="text-sm text-muted-foreground">Reading photos…</span>}
            {!reading && photos.length > 0 && <span className="text-sm text-muted-foreground">{photos.length} photos chosen</span>}
          </div>
        </form>
        <ErrorNote error={error} />
      </Panel>

      {report && <ReportPanel report={report} busy={busy} progress={progress} onImport={() => void runImport()} />}
      {photoResult && <PhotoResultPanel result={photoResult} />}

      <ExistingPhotos />
    </div>
  );
}

function ReportPanel({ report, busy, progress, onImport }: { report: ImportReport; busy: string; progress: string; onImport: () => void }) {
  const withPhoto = report.students.filter((s) => s.photo).length;
  return (
    <Panel title={report.imported ? "Imported" : "3. Check result"}>
      {report.imported ? (
        <p className="rounded-md border border-green-600/40 bg-green-50 p-3 text-sm dark:bg-green-950">
          {report.total} students were added to {report.session}.{" "}
          <Link to="/staff/students" className="font-medium text-primary underline">See the students</Link>
        </p>
      ) : report.ok ? (
        <div className="space-y-2 text-sm">
          <p className="font-medium text-green-700 dark:text-green-400">
            All {report.total} rows are correct. They will join session {report.session}; {withPhoto} have a photo.
          </p>
          {report.new_sections.length > 0 && <p>These sections will be created: {report.new_sections.join(", ")}.</p>}
          {report.photos_unused.length > 0 && (
            <p className="text-muted-foreground">
              {report.photos_unused.length} photos match no row and will be left out: {report.photos_unused.slice(0, 15).join(", ")}
              {report.photos_unused.length > 15 ? "…" : ""}
            </p>
          )}
          <div className="flex items-center gap-3">
            <Button type="button" onClick={onImport} disabled={Boolean(busy)}>
              {busy === "import" ? "Importing…" : `Import ${report.total} students`}
            </Button>
            {progress && <span className="text-muted-foreground" role="status">{progress}</span>}
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm font-medium text-destructive">
            {report.errors.length === 1 ? "1 problem" : `${report.errors.length} problems`} in {report.total} rows. Nothing has been saved. Correct the sheet and check it again.
          </p>
          <div className="max-h-[28rem] overflow-auto rounded border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Row</TableHead>
                  <TableHead scope="col">Column</TableHead>
                  <TableHead scope="col">Problem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.errors.map((e, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-mono">{e.row || "-"}</TableCell>
                    <TableCell>{e.column}</TableCell>
                    <TableCell>{e.message}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <p className="text-xs text-muted-foreground">Row numbers are the row numbers in Excel (row 1 is the heading).</p>
        </div>
      )}
    </Panel>
  );
}

function PhotoResultPanel({ result }: { result: PhotoResult }) {
  return (
    <Panel title="Photos">
      <p className="text-sm">
        {result.saved.length} photos saved
        {result.skipped.length > 0 && `, ${result.skipped.length} kept as they were (student already had a photo)`}.
      </p>
      {result.unmatched.length > 0 && (
        <p className="text-sm text-muted-foreground">
          No student has these admission numbers: {result.unmatched.slice(0, 30).join(", ")}{result.unmatched.length > 30 ? "…" : ""}
        </p>
      )}
      {result.errors.length > 0 && (
        <ul className="list-disc pl-5 text-sm text-destructive">
          {result.errors.map((e) => <li key={e.file}>{e.file}: {e.message}</li>)}
        </ul>
      )}
    </Panel>
  );
}

/** Photos for students already in LKMS, named by admission number. */
function ExistingPhotos() {
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<File[]>([]);
  const [replace, setReplace] = useState(true);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [result, setResult] = useState<PhotoResult | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [picker, setPicker] = useState(0);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const photos = await collectPhotos(files);
      if (!photos.length) throw new Error("No JPEG or PNG photos found in what you chose.");
      const items = photos.map((file) => ({ file, name: file.name }));
      setResult(await uploadPhotos(items, replace, (n) => setProgress(`Uploading ${n} of ${items.length}…`)));
      void queryClient.invalidateQueries({ queryKey: ["student"] });
      setFiles([]);
      setPicker((n) => n + 1);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
      setProgress("");
    }
  };

  return (
    <Panel title="Add photos for students already in LKMS">
      <form className="grid gap-4 sm:grid-cols-2" onSubmit={(e) => void submit(e)}>
        <Field label="Photos" required hint="Name each photo by the student's admission number, e.g. 0101.jpg. A ZIP or many photos at once.">
          <Input key={picker} type="file" multiple accept=".zip,application/zip,image/jpeg,image/png"
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))} />
        </Field>
        <label className="flex items-center gap-2 self-center text-sm">
          <input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} className="h-4 w-4" />
          Replace photos students already have
        </label>
        <div className="flex items-center gap-3 sm:col-span-2">
          <Button type="submit" disabled={!files.length || busy}>{busy ? "Uploading…" : "Upload photos"}</Button>
          {progress && <span className="text-sm text-muted-foreground" role="status">{progress}</span>}
        </div>
      </form>
      <ErrorNote error={error} />
      {result && <PhotoResultPanel result={result} />}
    </Panel>
  );
}
