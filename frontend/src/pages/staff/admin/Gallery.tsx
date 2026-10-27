import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { Field } from "@/components/Field";
import { ErrorNote, Panel } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { galleryImageUrl, type GalleryPhoto } from "@/lib/school";

/** Photos for the website's public gallery (administrator only). */
export default function Gallery() {
  const queryClient = useQueryClient();
  const photos = useQuery({ queryKey: ["gallery"], queryFn: () => api.get<GalleryPhoto[]>("/school/gallery/") });
  const [files, setFiles] = useState<File[]>([]);
  const [caption, setCaption] = useState("");
  const [picker, setPicker] = useState(0); // changing it empties the file picker

  const upload = useMutation({
    // One request per photo, so one bad picture does not stop the rest.
    mutationFn: async () => {
      const failed: string[] = [];
      for (const file of files) {
        const body = new FormData();
        body.append("image", file);
        body.append("caption", caption);
        try {
          await api.post("/school/gallery/", body);
        } catch (err) {
          failed.push(`${file.name}: ${err instanceof Error ? err.message : "could not upload"}`);
        }
      }
      return failed;
    },
    onSuccess: (failed) => {
      void queryClient.invalidateQueries({ queryKey: ["gallery"] });
      setFiles([]);
      setCaption("");
      setPicker((n) => n + 1);
      toast(failed.length ? { title: "Some photos were not added", description: failed.join(" "), variant: "destructive" } : { title: "Photos added" });
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/school/gallery/${id}/`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["gallery"] }),
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (files.length) upload.mutate();
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Photo gallery</h1>
      <p className="text-muted-foreground">
        Photos of school activities added here are shown to everyone in the Gallery on the website's front page.
        Only add photos the parents are happy to have on the website.
      </p>

      <Panel title="Add photos">
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={submit}>
          <Field label="Photos" required hint="JPEG or PNG, up to 9 MB each. You can choose several at once.">
            <Input key={picker} type="file" accept="image/png,image/jpeg" multiple required
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))} />
          </Field>
          <Field label="Caption" hint="Optional, e.g. Annual Day 2026">
            <Input value={caption} onChange={(e) => setCaption(e.target.value)} maxLength={200} />
          </Field>
          <div className="sm:col-span-2">
            <Button type="submit" disabled={!files.length || upload.isPending}>
              {upload.isPending ? "Uploading…" : files.length > 1 ? `Add ${files.length} photos` : "Add photo"}
            </Button>
          </div>
        </form>
      </Panel>

      <Panel title={`On the website (${photos.data?.length ?? 0})`}>
        {photos.isError && <ErrorNote error={photos.error} />}
        {remove.isError && <ErrorNote error={remove.error} />}
        {photos.data?.length === 0 && <p className="text-sm text-muted-foreground">No photos yet. The Gallery stays hidden until you add one.</p>}
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {photos.data?.map((p) => (
            <li key={p.id} className="space-y-2 rounded-lg border p-2">
              <img src={galleryImageUrl(p.id)} alt={p.caption || "School photo"} loading="lazy" className="aspect-square w-full rounded object-cover" />
              {p.caption && <p className="truncate text-sm">{p.caption}</p>}
              <Button type="button" variant="outline" size="sm" className="w-full" disabled={remove.isPending}
                onClick={() => window.confirm("Remove this photo from the website?") && remove.mutate(p.id)}>
                Remove
              </Button>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
