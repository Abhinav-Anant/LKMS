import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight, BellRing, CalendarCheck, ClipboardCheck, Facebook, FileUp, GraduationCap, IndianRupee, Instagram, LogIn,
  Mail, MapPin, Phone, Search, ShieldCheck, Sparkles, Twitter, UserRound, Wallet, Youtube,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

import { Hero3D } from "@/components/landing/Hero3D";
import { SchoolName } from "@/components/SchoolName";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { galleryImageUrl, useBranding, type GalleryPhoto } from "@/lib/school";
import type { AcademicSession, SchoolClass } from "@/lib/types";
import ParentLogin from "@/pages/parent/Login";
import Apply from "@/pages/public/Apply";
import StaffLogin from "@/pages/staff/Login";

const SOCIAL = [
  { key: "facebook_url", label: "Facebook", icon: <Facebook /> },
  { key: "instagram_url", label: "Instagram", icon: <Instagram /> },
  { key: "youtube_url", label: "YouTube", icon: <Youtube /> },
  { key: "x_url", label: "X (Twitter)", icon: <Twitter /> },
] as const;

export default function Home() {
  const school = useBranding();
  const location = useLocation();
  const options = useQuery({
    queryKey: ["admission-options"],
    queryFn: () => api.get<{ sessions: AcademicSession[]; classes: SchoolClass[] }>("/academics/admission-options/"),
  });
  const classes = options.data?.classes ?? [];
  const session = options.data?.sessions[0];
  const classRange = classes.length > 1 ? `${classes[0].name} to ${classes[classes.length - 1].name}` : classes[0]?.name;
  const gallery = useQuery({ queryKey: ["gallery"], queryFn: () => api.get<GalleryPhoto[]>("/school/gallery/") });
  const photos = gallery.data ?? [];
  const nav = [
    { href: "#admissions", label: "Admissions" },
    ...(photos.length ? [{ href: "#gallery", label: "Gallery" }] : []),
    { href: "#parents", label: "For parents" },
    { href: "#sign-in", label: "Sign in" },
    { href: "#contact", label: "Contact" },
  ];

  // Links like /#sign-in from other pages land on the right section.
  useEffect(() => {
    if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
  }, [location.hash]);

  const brand = school?.brand_colour ?? "#1d4ed8";
  const place = [school?.district, school?.state].filter(Boolean).join(", ");
  const spot = school?.map_latitude != null && school.map_longitude != null ? `${school.map_latitude},${school.map_longitude}` : "";
  const mapQuery = spot || [school?.name, school?.address, place, school?.pincode].filter(Boolean).join(", ");
  const social = SOCIAL.filter((s) => school?.[s.key]);

  return (
    <div className="min-h-screen bg-[#fffaf3] text-foreground">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-background focus:px-4 focus:py-2">
        Skip to content
      </a>

      <header className="sticky top-0 z-40 border-b border-black/5 bg-[#fffaf3]/85 backdrop-blur-md">
        <div className="container flex h-16 items-center justify-between gap-3">
          <a href="#top" className="min-w-0 font-display text-lg font-semibold text-primary sm:text-xl">
            <SchoolName school={school} className="flex min-w-0 items-center gap-2 [&>span]:truncate [&_img]:h-9 [&_img]:w-9" />
          </a>
          <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
            {nav.map((n) => (
              <a key={n.href} href={n.href} className="rounded-full px-3 py-2 text-sm font-medium text-foreground/75 transition-colors hover:bg-primary-glow hover:text-primary">
                {n.label}
              </a>
            ))}
          </nav>
          <div className="flex shrink-0 items-center gap-2">
            <Button asChild variant="ghost" size="sm" className="rounded-full md:hidden">
              <a href="#sign-in"><LogIn aria-hidden /> Sign in</a>
            </Button>
            <Button asChild size="sm" className="rounded-full px-4 shadow-md shadow-primary/20">
              <a href="#admissions">Apply now</a>
            </Button>
          </div>
        </div>
      </header>

      <main id="main">
        {/* Hero */}
        <section id="top" className="relative overflow-hidden">
          <Blobs />
          <div className="container relative grid items-center gap-6 pb-12 pt-8 md:grid-cols-[1.05fr_1fr] md:gap-10 md:pb-20 md:pt-14">
            <div className="space-y-6 text-center md:text-left">
              {session && (
                <p className="inline-flex items-center gap-2 rounded-full border border-primary/15 bg-white/80 px-4 py-1.5 text-sm font-medium text-primary shadow-sm">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75 motion-reduce:animate-none" />
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
                  </span>
                  Admissions open for {session.name}
                </p>
              )}
              <h1 className="font-display text-4xl font-bold leading-[1.08] tracking-tight text-[#1f1a33] sm:text-5xl lg:text-6xl">
                {school?.name ?? " "}
              </h1>
              <p className="mx-auto max-w-xl text-lg leading-relaxed text-foreground/70 md:mx-0 md:text-xl">
                A warm, caring place where young children learn, play and grow with confidence
                {classRange ? <>, from <strong className="font-semibold text-foreground">{classRange}</strong></> : null}.
              </p>
              <div className="flex flex-col justify-center gap-3 sm:flex-row md:justify-start">
                <Button asChild size="lg" className="h-12 rounded-full px-7 text-base shadow-lg shadow-primary/25">
                  <a href="#admissions">Apply for admission <ArrowRight aria-hidden /></a>
                </Button>
                <Button asChild size="lg" variant="outline" className="h-12 rounded-full border-2 bg-white/70 px-7 text-base">
                  <a href="#sign-in">Parent &amp; staff sign in</a>
                </Button>
              </div>
              <ul className="flex flex-wrap justify-center gap-x-5 gap-y-2 text-sm text-foreground/70 md:justify-start">
                {school?.board_label && <Fact icon={<GraduationCap />}>{school.board_label}</Fact>}
                {place && <Fact icon={<MapPin />}>{place}</Fact>}
                <Fact icon={<ShieldCheck />}>Apply online in about 10 minutes</Fact>
              </ul>
            </div>
            <div className="mx-auto w-full max-w-[min(100%,34rem)]">
              <Hero3D brand={brand} />
            </div>
          </div>
          <Wave />
        </section>

        {/* Classes offered */}
        {classes.length > 0 && (
          <section aria-labelledby="classes-heading" className="bg-white">
            <div className="container pb-2 pt-10 md:pt-14">
              <div className="flex flex-col items-center gap-5 text-center">
                <h2 id="classes-heading" className="font-display text-2xl font-semibold text-[#1f1a33] md:text-3xl">Classes we offer</h2>
                <ul className="flex max-w-3xl flex-wrap justify-center gap-2.5">
                  {classes.map((c, i) => (
                    <li key={c.id} className="rounded-full px-4 py-2 text-sm font-semibold shadow-sm ring-1 ring-black/5"
                      style={{ backgroundColor: `${TINTS[i % TINTS.length]}22`, color: "#2a2340" }}>
                      {c.name}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        )}

        {photos.length > 0 && (
          <section id="gallery" aria-labelledby="gallery-heading" className="scroll-mt-16 bg-[#fffaf3]">
            <div className="container py-14 md:py-20">
              <SectionTitle id="gallery-heading" eyebrow="Gallery" title="Life at our school"
                text="Celebrations, activities and everyday moments with our children." />
              <Gallery photos={photos} />
            </div>
          </section>
        )}

        {/* For parents */}
        <section id="parents" aria-labelledby="parents-heading" className="scroll-mt-16 bg-white">
          <div className="container py-14 md:py-20">
            <SectionTitle id="parents-heading" eyebrow="For parents" title="Everything about your child, on your phone"
              text="From the first form to the last report card, you can do it online without visiting the office." />
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Feature tint={TINTS[0]} icon={<ClipboardCheck />} title="Easy admission">
                Fill in the form from your phone and upload clear photos of the documents.
              </Feature>
              <Feature tint={TINTS[1]} icon={<CalendarCheck />} title="Attendance and results">
                See daily attendance, marks and report cards as soon as teachers enter them.
              </Feature>
              <Feature tint={TINTS[2]} icon={<Wallet />} title="Simple fee payment">
                Pay fees by UPI and get the receipt straight away. No queues.
              </Feature>
              <Feature tint={TINTS[3]} icon={<BellRing />} title="Never miss a notice">
                School notices and fee reminders reach you on WhatsApp.
              </Feature>
            </div>
          </div>
        </section>

        {/* Admissions */}
        <section id="admissions" aria-labelledby="admissions-heading" className="relative scroll-mt-16 overflow-hidden bg-primary-glow">
          <div className="container relative grid gap-10 py-14 md:py-20 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
            <div className="space-y-8 lg:sticky lg:top-24 lg:self-start">
              <SectionTitle id="admissions-heading" eyebrow="Admissions" title="Apply for admission" align="left"
                text="Keep the child's birth certificate and a recent photo handy. You can upload the rest later." />
              <ol className="space-y-4">
                {[
                  { icon: <UserRound />, title: "Fill in the form", text: "Details of the child, your address and the parents." },
                  { icon: <FileUp />, title: "Upload documents", text: "Photos from your phone are fine." },
                  { icon: <Search />, title: "School reviews it", text: "Follow every step with your application number." },
                  { icon: <IndianRupee />, title: "Pay the fee and join", text: "Pay online once the school confirms the seat." },
                ].map((s, i) => (
                  <li key={s.title} className="flex gap-4">
                    <span className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-primary shadow-sm [&_svg]:h-5 [&_svg]:w-5">
                      {s.icon}
                      <span className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground">{i + 1}</span>
                    </span>
                    <div>
                      <p className="font-semibold text-[#1f1a33]">{s.title}</p>
                      <p className="text-sm text-foreground/70">{s.text}</p>
                    </div>
                  </li>
                ))}
              </ol>
              <div className="rounded-2xl border border-primary/10 bg-white/80 p-5">
                <p className="font-semibold text-[#1f1a33]">Already applied?</p>
                <p className="mt-1 text-sm text-foreground/70">Check where your application has reached.</p>
                <Button asChild variant="link" className="mt-1 h-auto p-0">
                  <Link to="/track">Track your application <ArrowRight aria-hidden /></Link>
                </Button>
              </div>
            </div>
            <div className="min-w-0 rounded-3xl bg-white p-5 shadow-xl shadow-primary/10 ring-1 ring-black/5 sm:p-8">
              <Apply embedded />
            </div>
          </div>
        </section>

        {/* Sign in */}
        <section id="sign-in" aria-labelledby="sign-in-heading" className="scroll-mt-16 bg-white">
          <div className="container grid items-center gap-10 py-14 md:py-20 lg:grid-cols-2">
            <div className="space-y-6">
              <SectionTitle id="sign-in-heading" eyebrow="Sign in" title="Welcome back" align="left"
                text="Parents sign in with the mobile number they gave the school. Teachers and office staff use the username from the school." />
              <ul className="space-y-3 text-foreground/75">
                <Tick>Parents: attendance, marks, report cards, fees and notices for all your children.</Tick>
                <Tick>Staff: admissions, students, attendance, exams, fees and messages.</Tick>
              </ul>
            </div>
            <div className="mx-auto w-full max-w-md rounded-3xl bg-white p-5 shadow-xl shadow-primary/10 ring-1 ring-black/5 sm:p-8">
              <SignIn />
            </div>
          </div>
        </section>

        {/* Contact */}
        <section id="contact" aria-labelledby="contact-heading" className="scroll-mt-16 bg-[#fffaf3]">
          <div className="container py-14 md:py-20">
            <SectionTitle id="contact-heading" eyebrow="Contact" title="Come and visit us" text="We would love to show you around. Call or write to the school office." />
            <div className="mx-auto mt-10 grid max-w-4xl gap-4 sm:grid-cols-3">
              {school?.phone && <Contact icon={<Phone />} label="Call" value={school.phone} href={`tel:${school.phone.replace(/\s/g, "")}`} />}
              {school?.email && <Contact icon={<Mail />} label="Email" value={school.email} href={`mailto:${school.email}`} />}
              {(school?.address || place) && (
                <Contact icon={<MapPin />} label="Address"
                  value={[school?.address, place, school?.pincode].filter(Boolean).join(", ")}
                  href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(mapQuery)}`} />
              )}
            </div>
          </div>
        </section>

        {spot && (
          <section aria-labelledby="map-heading" className="bg-[#fffaf3]">
            <div className="container pb-14 md:pb-20">
              <h2 id="map-heading" className="sr-only">Find us on the map</h2>
              <div className="overflow-hidden rounded-3xl shadow-xl shadow-black/5 ring-1 ring-black/5">
                <iframe title={`Map showing ${school?.name ?? "the school"}`} loading="lazy" referrerPolicy="no-referrer-when-downgrade"
                  src={`https://maps.google.com/maps?q=${encodeURIComponent(spot)}&z=17&output=embed`}
                  className="block h-80 w-full border-0 md:h-[28rem]" />
              </div>
              <p className="mt-3 text-center">
                <Button asChild variant="link">
                  <a href={`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(spot)}`} target="_blank" rel="noopener">
                    Get directions <ArrowRight aria-hidden />
                  </a>
                </Button>
              </p>
            </div>
          </section>
        )}
      </main>

      <footer className="bg-[#1f1a33] text-white/70">
        <div className="container flex flex-col items-center justify-between gap-4 py-8 text-sm md:flex-row">
          <div className="flex items-center gap-2 font-display text-base font-semibold text-white">
            <SchoolName school={school} />
          </div>
          <p className="text-center">
            {[school?.board_label, place].filter(Boolean).join(" · ")}
            {school?.website && (
              <> · <a href={school.website} className="underline-offset-4 hover:underline" rel="noopener">{school.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}</a></>
            )}
          </p>
          {social.length > 0 && (
            <ul aria-label="Follow us" className="flex items-center gap-2">
              {social.map((s) => (
                <li key={s.key}>
                  <a href={school?.[s.key]} target="_blank" rel="noopener" aria-label={s.label} title={s.label}
                    className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-primary [&_svg]:h-5 [&_svg]:w-5">
                    {s.icon}
                  </a>
                </li>
              ))}
            </ul>
          )}
          <p>© {new Date().getFullYear()} {school?.name}</p>
        </div>
      </footer>
    </div>
  );
}

const TINTS = ["#ff6b5e", "#45a6f2", "#2ec4a0", "#9b7cf2", "#ffc23d", "#ff8fb1"];

function SignIn() {
  const { user, signOut } = useAuth();
  if (user) {
    const home = user.role === "parent" ? "/parent" : "/staff";
    return (
      <div className="space-y-4 text-center">
        <Sparkles className="mx-auto h-8 w-8 text-primary" aria-hidden />
        <p className="text-lg font-semibold">You are signed in{user.first_name ? ` as ${user.first_name}` : ""}.</p>
        <Button asChild className="w-full rounded-full"><Link to={home}>Go to my dashboard</Link></Button>
        <Button variant="ghost" className="w-full" onClick={signOut}>Sign out</Button>
      </div>
    );
  }
  return (
    <Tabs defaultValue="parent" className="space-y-6">
      <TabsList className="grid h-12 w-full grid-cols-2 rounded-full p-1">
        <TabsTrigger value="parent" className="h-full rounded-full text-sm font-semibold">Parent</TabsTrigger>
        <TabsTrigger value="staff" className="h-full rounded-full text-sm font-semibold">Teacher / staff</TabsTrigger>
      </TabsList>
      <TabsContent value="parent" className="mt-0">
        <ParentLogin embedded />
      </TabsContent>
      <TabsContent value="staff" className="mt-0">
        <StaffLogin embedded />
      </TabsContent>
    </Tabs>
  );
}

function Gallery({ photos }: { photos: GalleryPhoto[] }) {
  const [open, setOpen] = useState<GalleryPhoto | null>(null);
  return (
    <>
      <ul className="mt-10 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {photos.map((p) => (
          <li key={p.id}>
            <button type="button" onClick={() => setOpen(p)}
              className="group block w-full overflow-hidden rounded-2xl bg-white ring-1 ring-black/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
              <img src={galleryImageUrl(p.id)} alt={p.caption || "School photo"} loading="lazy"
                className="aspect-square w-full object-cover transition duration-300 group-hover:scale-105 motion-reduce:transform-none" />
            </button>
          </li>
        ))}
      </ul>
      <Dialog open={open !== null} onOpenChange={(o) => !o && setOpen(null)}>
        <DialogContent className="max-w-4xl p-3 sm:p-4">
          <DialogTitle className={open?.caption ? "pr-8 text-base" : "sr-only"}>{open?.caption || "School photo"}</DialogTitle>
          {open && <img src={galleryImageUrl(open.id)} alt={open.caption || "School photo"} className="max-h-[80vh] w-full rounded-lg object-contain" />}
        </DialogContent>
      </Dialog>
    </>
  );
}

function SectionTitle({ id, eyebrow, title, text, align = "center" }: { id: string; eyebrow: string; title: string; text: string; align?: "center" | "left" }) {
  return (
    <div className={align === "center" ? "mx-auto max-w-2xl space-y-3 text-center" : "space-y-3"}>
      <p className="text-sm font-semibold uppercase tracking-[0.14em] text-primary">{eyebrow}</p>
      <h2 id={id} className="font-display text-3xl font-bold tracking-tight text-[#1f1a33] md:text-4xl">{title}</h2>
      <p className="text-lg text-foreground/70">{text}</p>
    </div>
  );
}

function Feature({ icon, title, tint, children }: { icon: ReactNode; title: string; tint: string; children: ReactNode }) {
  return (
    <div className="group rounded-3xl bg-[#fffaf3] p-6 ring-1 ring-black/5 transition duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/5 motion-reduce:transform-none">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl text-white shadow-md [&_svg]:h-6 [&_svg]:w-6" style={{ backgroundColor: tint }}>
        {icon}
      </span>
      <h3 className="mt-5 font-display text-lg font-semibold text-[#1f1a33]">{title}</h3>
      <p className="mt-1.5 text-[0.95rem] leading-relaxed text-foreground/70">{children}</p>
    </div>
  );
}

function Fact({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <li className="flex items-center gap-1.5 [&_svg]:h-4 [&_svg]:w-4 [&_svg]:text-primary">
      {icon}
      {children}
    </li>
  );
}

function Tick({ children }: { children: ReactNode }) {
  return (
    <li className="flex gap-3">
      <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary-light text-xs font-bold text-primary" aria-hidden>✓</span>
      <span>{children}</span>
    </li>
  );
}

function Contact({ icon, label, value, href }: { icon: ReactNode; label: string; value: string; href: string }) {
  return (
    <a href={href} className="group flex flex-col items-center gap-3 rounded-3xl bg-white p-6 text-center ring-1 ring-black/5 transition hover:shadow-lg hover:shadow-black/5"
      {...(href.startsWith("http") ? { target: "_blank", rel: "noopener" } : {})}>
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-light text-primary [&_svg]:h-5 [&_svg]:w-5">{icon}</span>
      <span className="text-sm font-semibold uppercase tracking-wider text-foreground/60">{label}</span>
      <span className="break-words font-medium text-[#1f1a33] group-hover:text-primary">{value}</span>
    </a>
  );
}

/** Soft colour shapes behind the hero. */
function Blobs() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0">
      <div className="absolute -left-24 -top-24 h-80 w-80 rounded-full bg-primary/15 blur-3xl" />
      <div className="absolute right-[-6rem] top-10 h-96 w-96 rounded-full bg-[#ffc23d]/25 blur-3xl" />
      <div className="absolute bottom-0 left-1/3 h-72 w-72 rounded-full bg-[#ff8fb1]/20 blur-3xl" />
    </div>
  );
}

function Wave() {
  return (
    <svg aria-hidden viewBox="0 0 1440 80" preserveAspectRatio="none" className="relative block h-10 w-full text-white md:h-16">
      <path fill="currentColor" d="M0 48c160 26 320 32 480 18S800 14 960 14s320 30 480 44v22H0z" />
    </svg>
  );
}
