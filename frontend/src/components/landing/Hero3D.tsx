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
    <div className="relative aspect-square w-full">
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

/** A flat drawing of the stacked alphabet blocks. */
function HeroFallback({ brand }: { brand: string }) {
  const cube = (colour: string, letter: string, cls: string) => (
    <div
      className={cn("absolute flex aspect-square w-[22%] items-center justify-center rounded-[18%] font-display text-[clamp(2rem,9vw,4.5rem)] font-bold text-white shadow-[inset_0_-10px_0_rgba(0,0,0,0.12),0_18px_30px_-12px_rgba(40,30,60,0.35)]", cls)}
      style={{ backgroundColor: colour }}
    >
      <span className="flex h-[78%] w-[78%] items-center justify-center rounded-[16%] border-[3px] border-white/60">{letter}</span>
    </div>
  );
  return (
    <div className="relative h-full w-full" aria-hidden="true">
      <div className="absolute bottom-[14%] left-1/2 h-[6%] w-[52%] -translate-x-1/2 rounded-[50%] bg-[radial-gradient(closest-side,rgba(40,30,60,0.25),transparent)]" />
      {cube(PALETTE.coral, "B", "bottom-[18%] left-[27%] -rotate-3")}
      {cube(PALETTE.sky, "C", "bottom-[18%] left-[51%] rotate-3")}
      {cube(brand, "A", "bottom-[40%] left-[39%] rotate-6")}
      <div className="absolute left-[16%] top-[22%] aspect-square w-[16%] rounded-full bg-[conic-gradient(#ff6b5e_0_25%,#fff_0_33%,#ffc23d_0_58%,#fff_0_66%,#45a6f2_0_91%,#fff_0)] shadow-lg" />
      <div className="absolute right-[22%] top-[18%] font-display text-[clamp(2rem,8vw,4rem)] text-[#ffc23d] drop-shadow">★</div>
      <div className="absolute right-[14%] bottom-[24%] aspect-square w-[11%] rounded-full shadow-md" style={{ backgroundColor: PALETTE.coral }} />
    </div>
  );
}
