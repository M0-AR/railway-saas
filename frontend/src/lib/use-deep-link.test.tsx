import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useDeepLinkFlag } from "@/lib/use-deep-link";

afterEach(() => {
  window.history.replaceState({}, "", "/");
});

describe("useDeepLinkFlag", () => {
  it("fires once and strips the flag from the URL", () => {
    window.history.replaceState({}, "", "/bookings?new=1&page=2");
    const onMatch = vi.fn();

    renderHook(() => useDeepLinkFlag("new", onMatch));

    expect(onMatch).toHaveBeenCalledTimes(1);
    expect(`${window.location.pathname}${window.location.search}`).toBe("/bookings?page=2");
  });

  it("does nothing when the flag is absent", () => {
    window.history.replaceState({}, "", "/bookings?page=2");
    const onMatch = vi.fn();

    renderHook(() => useDeepLinkFlag("new", onMatch));

    expect(onMatch).not.toHaveBeenCalled();
    expect(window.location.search).toBe("?page=2");
  });

  it("waits for enabled and uses the latest callback", () => {
    window.history.replaceState({}, "", "/bookings?new=1");
    const first = vi.fn();
    const second = vi.fn();
    const { rerender } = renderHook(
      ({ enabled, callback }) => useDeepLinkFlag("new", callback, enabled),
      { initialProps: { enabled: false, callback: first } },
    );

    expect(first).not.toHaveBeenCalled();

    rerender({ enabled: true, callback: second });

    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledTimes(1);
  });

  it("ignores other values for the same key", () => {
    window.history.replaceState({}, "", "/bookings?new=0");
    const onMatch = vi.fn();

    renderHook(() => useDeepLinkFlag("new", onMatch));

    expect(onMatch).not.toHaveBeenCalled();
    expect(window.location.search).toBe("?new=0");
  });
});
