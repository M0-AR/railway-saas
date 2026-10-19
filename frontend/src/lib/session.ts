import type { Me, Member, Tenant, TokenResponse } from "@/lib/types";

const ACCESS_KEY = "rf_access_token";
const REFRESH_KEY = "rf_refresh_token";
const ME_KEY = "rf_me";
export const SESSION_EVENT = "rf:session";

export interface StoredSession {
  access_token: string;
  refresh_token: string;
  user: Member;
  tenant: Tenant;
}

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function loadSession(): StoredSession | null {
  if (!isBrowser()) return null;
  const access = window.localStorage.getItem(ACCESS_KEY);
  const refresh = window.localStorage.getItem(REFRESH_KEY);
  const rawMe = window.localStorage.getItem(ME_KEY);
  if (!access || !refresh || !rawMe) return null;
  try {
    const me = JSON.parse(rawMe) as Me;
    return { access_token: access, refresh_token: refresh, user: me.user, tenant: me.tenant };
  } catch {
    return null;
  }
}

export function saveSession(tokens: TokenResponse): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(ACCESS_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  window.localStorage.setItem(ME_KEY, JSON.stringify({ user: tokens.user, tenant: tokens.tenant }));
  window.dispatchEvent(new Event(SESSION_EVENT));
}

export function saveMe(me: Me): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(ME_KEY, JSON.stringify({ user: me.user, tenant: me.tenant }));
  window.dispatchEvent(new Event(SESSION_EVENT));
}

export function getAccessToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

export function updateAccessToken(access: string, refresh: string): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(ACCESS_KEY, access);
  window.localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearSession(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
  window.localStorage.removeItem(ME_KEY);
  window.dispatchEvent(new Event(SESSION_EVENT));
}
