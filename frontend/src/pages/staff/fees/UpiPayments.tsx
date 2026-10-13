import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { NativeSelect } from "@/components/Field";
import { ErrorNote } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { UPI_STATUS_LABELS } from "@/lib/labels";
import type { Paginated, UpiSubmission } from "@/lib/types";

import { FeesNav } from "./FeesNav";
import { UpiCard } from "./UpiCard";

export default function UpiPayments() {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "pending";
  const page = Number(params.get("page") ?? "1");
  const list = useQuery({
    queryKey: ["upi-submissions", status, page],
    queryFn: () => api.get<Paginated<UpiSubmission>>("/fees/upi-submissions/", { status, page }),
    placeholderData: keepPreviousData,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Fees</h1>
      <FeesNav />
      <p className="text-sm text-muted-foreground">
        Parents who paid by scanning the school's UPI QR code send the transaction ID (UTR) and a screenshot here.
        Check each one in the school's bank statement before approving. Approving issues the school receipt.
      </p>
      <label className="block space-y-1 text-sm sm:w-64">
        <span className="font-medium">Show</span>
        <NativeSelect value={status} onChange={(e) => setParams({ status: e.target.value }, { replace: true })}>
          {Object.entries(UPI_STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </NativeSelect>
      </label>
      <ErrorNote error={list.error} />
      <ul className="space-y-3">
        {list.data?.results.map((s) => <UpiCard key={s.id} submission={s} showStudent />)}
        {list.data?.results.length === 0 && <li className="rounded-lg border bg-background p-6 text-center text-muted-foreground">Nothing here.</li>}
      </ul>
      {list.data && (list.data.next || list.data.previous) && (
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" disabled={!list.data.previous} onClick={() => setParams({ status, page: String(page - 1) })}>Previous</Button>
          <Button variant="outline" size="sm" disabled={!list.data.next} onClick={() => setParams({ status, page: String(page + 1) })}>Next</Button>
        </div>
      )}
    </div>
  );
}
