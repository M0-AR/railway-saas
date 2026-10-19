import { afterEach, describe, expect, it, vi } from "vitest";

import {
  compactMoney,
  formatDate,
  formatDateTime,
  formatShortDate,
  formatTime,
  initials,
  money,
  percent,
  relativeTime,
  slugify,
  titleCase,
  todayISO,
} from "@/lib/format";

afterEach(() => {
  vi.useRealTimers();
});

describe("money", () => {
  it("formats cents as currency", () => {
    expect(money(4500)).toBe("$45.00");
    expect(money(0)).toBe("$0.00");
    expect(money(123456)).toBe("$1,234.56");
  });

  it("supports other currencies", () => {
    expect(money(4500, "EUR")).toBe("€45.00");
  });

  it("treats missing values as zero", () => {
    expect(money(undefined as unknown as number)).toBe("$0.00");
  });
});

describe("compactMoney", () => {
  it("treats missing values as zero", () => {
    expect(compactMoney(undefined as unknown as number)).toBe("$0");
  });

  it("compacts large amounts", () => {
    expect(compactMoney(123456)).toBe("$1.2K");
    expect(compactMoney(123456789)).toBe("$1.2M");
  });
});

describe("date helpers", () => {
  const stamp = "2026-03-05T12:00:00Z";

  it("formats full, short and date-time variants", () => {
    expect(formatDate(stamp)).toBe("Mar 5, 2026");
    expect(formatShortDate(stamp)).toBe("Mar 5");
    expect(formatDateTime(stamp)).toContain("Mar 5");
    expect(formatShortDate(new Date(stamp))).toBe("Mar 5");
    expect(formatDateTime(new Date(stamp))).toContain("Mar 5");
  });

  it("accepts Date objects", () => {
    expect(formatDate(new Date(stamp))).toBe("Mar 5, 2026");
  });

  it("renders an em dash for empty values", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate(undefined)).toBe("—");
    expect(formatShortDate(null)).toBe("—");
    expect(formatDateTime(null)).toBe("—");
  });

  it("slices HH:MM:SS down to HH:MM", () => {
    expect(formatTime("08:30:00")).toBe("08:30");
    expect(formatTime("23:59")).toBe("23:59");
    expect(formatTime(null)).toBe("—");
  });
});

describe("relativeTime", () => {
  it("describes recent and distant moments", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-05T12:00:00Z"));

    expect(relativeTime(new Date("2026-03-05T11:59:30Z"))).toBe("just now");
    expect(relativeTime(new Date("2026-03-05T11:55:00Z"))).toBe("5 minutes ago");
    expect(relativeTime(new Date("2026-03-03T12:00:00Z"))).toBe("2 days ago");
    expect(relativeTime(new Date("2026-03-05T09:00:00Z"))).toBe("3 hours ago");
    expect(relativeTime(new Date("2026-03-05T14:00:00Z"))).toBe("in 2 hours");
    expect(relativeTime(new Date("2025-12-05T12:00:00Z"))).toBe("3 months ago");
    expect(relativeTime(new Date("2028-03-05T12:00:00Z"))).toBe("in 2 years");
    expect(relativeTime(new Date("2026-06-05T12:00:00Z"))).toBe("in 3 months");
    expect(relativeTime(null)).toBe("—");
  });
});

describe("percent", () => {
  it("renders rates with configurable precision", () => {
    expect(percent(0.075)).toBe("8%");
    expect(percent(0.5, 1)).toBe("50.0%");
    expect(percent(0, 2)).toBe("0.00%");
  });
});

describe("initials", () => {
  it("uses the first two words", () => {
    expect(initials("Ada Lovelace")).toBe("AL");
    expect(initials("Grace Brewster Hopper")).toBe("GB");
  });

  it("handles single names and extra whitespace", () => {
    expect(initials("Ada")).toBe("A");
    expect(initials("  Ada   Lovelace  ")).toBe("AL");
    expect(initials("")).toBe("");
  });
});

describe("titleCase", () => {
  it("turns snake_case and dotted actions into labels", () => {
    expect(titleCase("custom_domain")).toBe("Custom Domain");
    expect(titleCase("booking.cancelled")).toBe("Booking Cancelled");
    expect(titleCase("already Title")).toBe("Already Title");
  });
});

describe("todayISO", () => {
  it("returns the local calendar date", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 2, 5, 12, 0, 0));
    expect(todayISO()).toBe("2026-03-05");
  });
});

describe("slugify", () => {
  it("normalizes workspace names", () => {
    expect(slugify("  Hello World!  ")).toBe("hello-world");
    expect(slugify("Night Owl Rail")).toBe("night-owl-rail");
    expect(slugify("A--B__C")).toBe("a-b-c");
  });

  it("strips unsupported characters and caps length", () => {
    expect(slugify("Café Rail")).toBe("caf-rail");
    expect(slugify("x".repeat(40))).toHaveLength(32);
  });
});
