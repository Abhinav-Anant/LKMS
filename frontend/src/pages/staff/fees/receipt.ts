import { fetchFileUrl } from "@/lib/api";

/** Open a protected PDF in a new tab. The tab is opened first so pop-up blockers allow it. */
export async function openPdf(path: string) {
  const win = window.open("", "_blank");
  try {
    const url = await fetchFileUrl(path);
    if (win) win.location.href = url;
    else window.location.href = url;
  } catch (err) {
    win?.close();
    throw err;
  }
}
