import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  SESSION_EVENT,
  clearSession,
  getAccessToken,
  getRefreshToken,
  loadSession,
  saveMe,
  saveSession,
  updateAccessToken,
} from "@/lib/session";
import type { Me, TokenResponse } from "@/lib/types";

const session = {
  access_token: "access-1",
  refresh_token: "refresh-1",
  user: { id: "member-1", email: "owner@acme.example", full_name: "Ada Owner" },
  tenant: { id: "tenant-1", slug: "acme", name: "Acme Rail" },
} as unknown as TokenResponse;

const me = {
  user: { ...session.user, full_name: "Ada Updated" },
  tenant: session.tenant,
} as unknown as Me;

describe("session storage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("round-trips a saved session", () => {
    saveSession(session);

    expect(getAccessToken()).toBe("access-1");
    expect(getRefreshToken()).toBe("refresh-1");
    expect(loadSession()).toEqual({
      access_token: "access-1",
      refresh_token: "refresh-1",
      user: session.user,
      tenant: session.tenant,
    });
  });

  it("broadcasts a session event when saving", () => {
    const listener = vi.fn();
    window.addEventListener(SESSION_EVENT, listener);

    saveSession(session);
    saveMe(me);
    clearSession();

    expect(listener).toHaveBeenCalledTimes(3);
    window.removeEventListener(SESSION_EVENT, listener);
  });

  it("refreshes profile data without touching tokens", () => {
    saveSession(session);
    saveMe(me);

    const stored = loadSession();
    expect(stored?.user.full_name).toBe("Ada Updated");
    expect(stored?.access_token).toBe("access-1");
  });

  it("rotates tokens in place", () => {
    saveSession(session);
    updateAccessToken("access-2", "refresh-2");

    expect(getAccessToken()).toBe("access-2");
    expect(getRefreshToken()).toBe("refresh-2");
    expect(loadSession()?.user).toEqual(session.user);
  });

  it("returns null for incomplete or corrupt storage", () => {
    expect(loadSession()).toBeNull();

    saveSession(session);
    window.localStorage.setItem("rf_me", "{not-json");
    expect(loadSession()).toBeNull();

    window.localStorage.removeItem("rf_refresh_token");
    window.localStorage.setItem("rf_me", JSON.stringify({ user: me.user, tenant: me.tenant }));
    expect(loadSession()).toBeNull();
  });

  it("no-ops without a window (server rendering)", () => {
    const browserWindow = globalThis.window;
    vi.stubGlobal("window", undefined);
    try {
      expect(loadSession()).toBeNull();
      expect(getAccessToken()).toBeNull();
      expect(getRefreshToken()).toBeNull();
      expect(() => saveSession(session)).not.toThrow();
      expect(() => saveMe(me)).not.toThrow();
      expect(() => updateAccessToken("a", "b")).not.toThrow();
      expect(() => clearSession()).not.toThrow();
    } finally {
      vi.stubGlobal("window", browserWindow);
    }
  });

  it("clears every key on sign out", () => {
    saveSession(session);
    clearSession();

    expect(loadSession()).toBeNull();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });
});
