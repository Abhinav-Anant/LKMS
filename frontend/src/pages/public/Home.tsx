import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useSchool } from "@/lib/school";

export default function Home() {
  const school = useSchool();
  return (
    <div className="mx-auto max-w-2xl space-y-8 py-8">
      <div className="space-y-3">
        <h1 className="text-3xl font-bold tracking-tight">{school?.name}</h1>
        {school?.board_label && <p className="text-sm font-medium text-muted-foreground">Affiliated to {school.board_label}</p>}
        <p className="text-lg text-muted-foreground">
          Apply for admission online, upload documents, and follow your application's progress.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <section className="rounded-lg border p-5">
          <h2 className="font-semibold">New admission</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Takes about 10 minutes. Keep the child's birth certificate and a photo ready.
          </p>
          <Button asChild className="mt-4">
            <Link to="/apply">Start application</Link>
          </Button>
        </section>
        <section className="rounded-lg border p-5">
          <h2 className="font-semibold">Already applied?</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Check the status with your application number, the child's date of birth and your mobile number.
          </p>
          <Button asChild variant="outline" className="mt-4">
            <Link to="/track">Track application</Link>
          </Button>
        </section>
      </div>
    </div>
  );
}
