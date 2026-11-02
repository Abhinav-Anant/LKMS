import { lazy, Suspense, useCallback, useEffect, useState } from "react";

import { cn } from "@/lib/utils";

import { PALETTE } from "./palette";

const HeroScene = lazy(() => import("./HeroScene"));

/** Phones on data saver, very low memory, or without WebGL get the flat picture instead of the 3D one. */
function canRun3D() {
  const nav = navigator as Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } };
  if (nav.connection?.saveData || (nav.deviceMemory !== undefined && nav.deviceMemory < 2)) return false;
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") ?? c.getContext("webgl"));
  } catch {
    return false;
  }
}

/** The hero picture: the 3D scene, loaded after the page has painted, over a flat version of the same picture. */
export function Hero3D({ brand }: { brand: string }) {
  const [load, setLoad] = useState(false);
  const [ready, setReady] = useState(false);
  const onReady = useCallback(() => setReady(true), []);

  useEffect(() => {
    if (!canRun3D()) return;
    const start = () => setLoad(true);
    const idle = window.requestIdleCallback?.(start, { timeout: 1500 });
    const timer = idle === undefined ? window.setTimeout(start, 300) : undefined;
    return () => {
      if (idle !== undefined) window.cancelIdleCallback(idle);
      clearTimeout(timer);
    };
  }, []);

  return (
    <div className="relative aspect-[2.1/1] w-full">
      <div className={cn("absolute inset-0 transition-opacity duration-700", ready && "opacity-0")}>
        <HeroFallback brand={brand} />
      </div>
      {load && (
        <Suspense fallback={null}>
          <div className={cn("absolute inset-0 opacity-0 transition-opacity duration-700", ready && "opacity-100")}>
            <HeroScene brand={brand} onReady={onReady} />
          </div>
        </Suspense>
      )}
    </div>
  );
}

/** A flat drawing of the row of alphabet blocks. */
function HeroFallback({ brand }: { brand: string }) {
  const cube = (colour: string, letter: string, cls: string) => (
    <div
      className={cn("absolute bottom-[16%] flex aspect-square w-[20%] items-center justify-center rounded-[18%] font-display text-[clamp(1.5rem,6vw,3rem)] font-bold text-white shadow-[inset_0_-8px_0_rgba(0,0,0,0.12),0_14px_24px_-10px_rgba(40,30,60,0.35)]", cls)}
      style={{ backgroundColor: colour }}
    >
      <span className="flex h-[78%] w-[78%] items-center justify-center rounded-[16%] border-[3px] border-white/60">{letter}</span>
    </div>
  );
  return (
    <div className="relative h-full w-full" aria-hidden="true">
      <div className="absolute bottom-[10%] left-1/2 h-[10%] w-[70%] -translate-x-1/2 rounded-[50%] bg-[radial-gradient(closest-side,rgba(40,30,60,0.25),transparent)]" />
      {cube(brand, "A", "left-[17%] -rotate-3")}
      {cube(PALETTE.coral, "B", "left-[40%] rotate-1")}
      {cube(PALETTE.sky, "C", "left-[63%] rotate-3")}
      <div className="absolute right-[4%] top-[8%] font-display text-[clamp(1.5rem,5vw,2.5rem)] text-[#ffc23d] drop-shadow">★</div>
    </div>
  );
}
