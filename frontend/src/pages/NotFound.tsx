import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
      <h1 className="text-2xl font-bold">Page not found</h1>
      <p className="text-muted-foreground">The page you asked for does not exist.</p>
      <Link to="/" className="text-primary underline-offset-4 hover:underline">Go to the home page</Link>
    </main>
  );
}
