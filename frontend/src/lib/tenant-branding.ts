import type { CSSProperties } from "react";

import type { Branding } from "@/lib/types";

export const DEFAULT_PRIMARY = "#6d5efc";
export const DEFAULT_ACCENT = "#22d3ee";

const HEX_RE = /^#[0-9a-f]{6}$/i;

function safeColor(value: string | undefined, fallback: string): string {
  return value && HEX_RE.test(value) ? value : fallback;
}

export function primaryOf(branding?: Branding): string {
  return safeColor(branding?.primary_color, DEFAULT_PRIMARY);
}

export function accentOf(branding?: Branding): string {
  return safeColor(branding?.accent_color, DEFAULT_ACCENT);
}

export function brandingStyle(branding?: Branding): CSSProperties {
  return {
    "--brand": primaryOf(branding),
    "--brand-2": accentOf(branding),
  } as CSSProperties;
}

export function logoTextOf(name: string, branding?: Branding): string {
  const logo = branding?.logo_text?.trim();
  return logo || name;
}
