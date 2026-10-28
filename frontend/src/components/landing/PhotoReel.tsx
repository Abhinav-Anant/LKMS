import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { galleryImageUrl, type GalleryPhoto } from "@/lib/school";

const SECONDS = 5;

/** The gallery as a slideshow that moves on by itself. Stops on hover, on focus, when paused, or for reduced motion. */
export function PhotoReel({ photos }: { photos: GalleryPhoto[] }) {
  const [index, setIndex] = useState(0);
  const [previous, setPrevious] = useState<number | null>(null);
  const [paused, setPaused] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [held, setHeld] = useState(false); // pointer or keyboard focus is on the reel
  const count = photos.length;

  const go = (step: number) => {
    setPrevious(index);
    setIndex((index + step + count) % count);
  };

  useEffect(() => {
    if (paused || held || count < 2) return;
    const timer = window.setTimeout(() => !document.hidden && go(1), SECONDS * 1000);
    return () => window.clearTimeout(timer);
  });

  if (!count) return null;
  const photo = photos[index % count];
  const next = photos[(index + 1) % count];
  const src = galleryImageUrl(photo.id);

  return (
    <div
      role="region" aria-roledescription="carousel" aria-label="School photos"
      className="group relative overflow-hidden rounded-3xl bg-[#1f1a33] shadow-2xl shadow-primary/20 ring-1 ring-black/5"
      onMouseEnter={() => setHeld(true)} onMouseLeave={() => setHeld(false)}
      onFocus={() => setHeld(true)} onBlur={() => setHeld(false)}
    >
      <div className="relative aspect-[4/5] sm:aspect-[16/9]">
        {previous !== null && previous !== index && (
          <img src={galleryImageUrl(photos[previous % count].id)} alt="" className="absolute inset-0 h-full w-full object-contain" />
        )}
        <div key={photo.id} className="absolute inset-0 duration-700 animate-in fade-in motion-reduce:animate-none">
          {/* The same photo, blurred, fills the frame around portrait pictures. */}
          <img src={src} alt="" aria-hidden className="absolute inset-0 h-full w-full scale-110 object-cover opacity-60 blur-2xl" />
          <img src={src} alt={photo.caption || `School photo ${index + 1} of ${count}`}
            className={`relative h-full w-full object-contain ${paused ? "" : "animate-slow-zoom"} motion-reduce:animate-none`} />
        </div>
        <link rel="preload" as="image" href={galleryImageUrl(next.id)} />
        {photo.caption && (
          <p className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent px-5 pb-12 pt-10 text-center font-display text-lg font-semibold text-white sm:text-xl">
            {photo.caption}
          </p>
        )}
      </div>

      {count > 1 && (
        <div className="absolute inset-x-0 bottom-3 flex items-center justify-center gap-2">
          <ReelButton label="Previous photo" onClick={() => go(-1)}><ChevronLeft /></ReelButton>
          <ReelButton label={paused ? "Play slideshow" : "Pause slideshow"} onClick={() => setPaused(!paused)}>
            {paused ? <Play /> : <Pause />}
          </ReelButton>
          <span className="min-w-[4.5rem] rounded-full bg-black/45 px-3 py-1.5 text-center text-sm font-medium text-white tabular-nums" aria-live={paused ? "polite" : "off"}>
            {index + 1} / {count}
          </span>
          <ReelButton label="Next photo" onClick={() => go(1)}><ChevronRight /></ReelButton>
        </div>
      )}
    </div>
  );
}

function ReelButton({ label, onClick, children }: { label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" aria-label={label} title={label} onClick={onClick}
      className="flex h-10 w-10 items-center justify-center rounded-full bg-black/45 text-white backdrop-blur transition-colors hover:bg-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white [&_svg]:h-5 [&_svg]:w-5">
      {children}
    </button>
  );
}
