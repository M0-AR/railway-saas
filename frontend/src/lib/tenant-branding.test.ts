import { describe, expect, it } from "vitest";

import {
  DEFAULT_ACCENT,
  DEFAULT_PRIMARY,
  accentOf,
  brandingStyle,
  logoTextOf,
  primaryOf,
} from "@/lib/tenant-branding";
import type { Branding } from "@/lib/types";

describe("tenant branding", () => {
  it("falls back to the default palette", () => {
    expect(primaryOf()).toBe(DEFAULT_PRIMARY);
    expect(accentOf()).toBe(DEFAULT_ACCENT);
    expect(primaryOf({} as Branding)).toBe(DEFAULT_PRIMARY);
    expect(accentOf({ accent_color: "not-a-color" } as Branding)).toBe(DEFAULT_ACCENT);
  });

  it("accepts six-digit hex colors in any case", () => {
    expect(primaryOf({ primary_color: "#aabbcc" } as Branding)).toBe("#aabbcc");
    expect(accentOf({ accent_color: "#22D3EE" } as Branding)).toBe("#22D3EE");
  });

  it("rejects shorthand, named and malformed colors", () => {
    expect(primaryOf({ primary_color: "#abc" } as Branding)).toBe(DEFAULT_PRIMARY);
    expect(primaryOf({ primary_color: "red" } as Branding)).toBe(DEFAULT_PRIMARY);
    expect(primaryOf({ primary_color: "#gggggg" } as Branding)).toBe(DEFAULT_PRIMARY);
  });

  it("exposes brand colors as CSS variables", () => {
    expect(brandingStyle({ primary_color: "#112233", accent_color: "#445566" } as Branding)).toEqual({
      "--brand": "#112233",
      "--brand-2": "#445566",
    });
  });

  it("prefers custom logo text and falls back to the workspace name", () => {
    expect(logoTextOf("Acme Rail", { logo_text: "  Acme  " } as Branding)).toBe("Acme");
    expect(logoTextOf("Acme Rail", { logo_text: "   " } as Branding)).toBe("Acme Rail");
    expect(logoTextOf("Acme Rail", {} as Branding)).toBe("Acme Rail");
    expect(logoTextOf("Acme Rail")).toBe("Acme Rail");
  });
});
