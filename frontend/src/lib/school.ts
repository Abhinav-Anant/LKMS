import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { api, apiUrl } from "./api";

export interface PublicSchool {
  name: string;
  short_code: string;
  address: string;
  district: string;
  state: string;
  pincode: string;
  phone: string;
  email: string;
  website: string;
  board: string;
  board_label: string;
  brand_colour: string;
  has_logo: boolean;
  map_latitude: string | null;
  map_longitude: string | null;
  facebook_url: string;
  instagram_url: string;
  youtube_url: string;
  x_url: string;
}

export interface GalleryPhoto {
  id: number;
  caption: string;
  uploaded_at: string;
}

export const galleryImageUrl = (id: number) => apiUrl(`/school/gallery/${id}/image/`);

export const LOGO_URL = apiUrl("/school/logo/");
export const UPI_QR_URL = apiUrl("/school/upi-qr/");

export function useSchool() {
  const { data } = useQuery({
    queryKey: ["school"],
    queryFn: () => api.get<PublicSchool>("/school/"),
    staleTime: 60 * 60 * 1000,
  });
  return data;
}

/** "#1d4ed8" -> [hue, saturation %, lightness %] */
export function hexToHsl(hex: string): [number, number, number] | null {
  const match = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!match) return null;
  const n = parseInt(match[1], 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => v / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, Math.round(l * 100)];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [Math.round(h * 60), Math.round(s * 100), Math.round(l * 100)];
}

/** The school's colour as theme variables. Kept dark enough for white text on it and for links on white. */
export function brandVariables(hex: string): Record<string, string> | null {
  const hsl = hexToHsl(hex);
  if (!hsl) return null;
  const [h, s, l] = hsl;
  const main = `${h} ${s}% ${Math.min(l, 40)}%`;
  return {
    "--primary": main,
    "--ring": main,
    "--primary-light": `${h} ${s}% 92%`,
    "--primary-glow": `${h} ${s}% 96%`,
  };
}

const BRAND_KEY = "lkms.brandColour";

function applyColour(hex: string) {
  const vars = brandVariables(hex);
  if (vars) for (const [key, value] of Object.entries(vars)) document.documentElement.style.setProperty(key, value);
}

/** Use the colour remembered from the last visit straight away, so the page does not flash the default colour. */
export function applyRememberedBranding() {
  try {
    const hex = localStorage.getItem(BRAND_KEY);
    if (hex) applyColour(hex);
  } catch {
    // storage blocked: the colour arrives with the school's details instead
  }
}

/** Applies the school's name, colour and logo to the page title, theme and browser tab icon. */
export function useBranding() {
  const school = useSchool();
  useEffect(() => {
    if (!school) return;
    // Pages served with search-engine tags (core.seo) already carry a fuller title
    if (!document.querySelector('link[rel="canonical"]')) document.title = school.name;
    applyColour(school.brand_colour);
    try {
      localStorage.setItem(BRAND_KEY, school.brand_colour);
    } catch {
      // storage blocked; nothing to remember
    }
    if (school.has_logo) {
      let icon = document.querySelector<HTMLLinkElement>("link[rel='icon']");
      if (!icon) {
        icon = document.createElement("link");
        icon.rel = "icon";
        document.head.appendChild(icon);
      }
      icon.href = LOGO_URL;
    }
  }, [school]);
  return school;
}
