import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  updateAccessToken,
} from "@/lib/session";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api/v1";
export const API_INTERNAL = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  code: string;
  details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }

  get isPlanGate(): boolean {
    return this.status === 402;
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

interface RequestOptions {
  query?: Query;
  json?: unknown;
  form?: FormData;
  auth?: boolean;
  raw?: boolean;
}

function buildUrl(path: string, query?: Query): string {
  const base = path.startsWith("http") ? path : `${API_BASE}${path}`;
  if (!query) return base;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
}

let refreshInFlight: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const response = await fetch(buildUrl("/auth/refresh"), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!response.ok) return false;
    const tokens = (await response.json()) as { access_token: string; refresh_token: string };
    updateAccessToken(tokens.access_token, tokens.refresh_token);
    return true;
  } catch {
    return false;
  }
}

function expireSession(): void {
  clearSession();
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.replace(`/login?next=${next}`);
  }
}

async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  const { query, json, form, auth = true } = options;
  const headers: Record<string, string> = {};
  if (json !== undefined) headers["content-type"] = "application/json";
  if (auth) {
    const token = getAccessToken();
    if (token) headers.authorization = `Bearer ${token}`;
  }

  const doFetch = () =>
    fetch(buildUrl(path, query), {
      method,
      headers,
      body: json !== undefined ? JSON.stringify(json) : form,
    });

  let response = await doFetch();

  if (response.status === 401 && auth) {
    refreshInFlight = refreshInFlight ?? refreshTokens().finally(() => {
      refreshInFlight = null;
    });
    const refreshed = await refreshInFlight;
    if (refreshed) {
      const token = getAccessToken();
      if (token) headers.authorization = `Bearer ${token}`;
      response = await doFetch();
    } else {
      expireSession();
      throw new ApiError(401, "unauthorized", "Your session has expired. Please sign in again.");
    }
  }

  if (!response.ok) {
    let code = "error";
    let message = `Request failed (${response.status})`;
    let details: Record<string, unknown> = {};
    try {
      const body = await response.json();
      if (body?.error) {
        code = body.error.code ?? code;
        message = body.error.message ?? message;
        details = body.error.details ?? {};
      } else if (Array.isArray(body?.detail)) {
        code = "validation_error";
        message = body.detail
          .map((item: { loc?: string[]; msg?: string }) => `${item.loc?.slice(1).join(".") ?? ""}: ${item.msg ?? ""}`)
          .join(" · ");
        details = { errors: body.detail };
      }
    } catch {
      // keep defaults
    }
    throw new ApiError(response.status, code, message, details);
  }

  if (options.raw) return response as unknown as T;
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, options: Omit<RequestOptions, "json" | "form"> = {}) =>
    request<T>("GET", path, options),
  post: <T>(path: string, json?: unknown, options: RequestOptions = {}) =>
    request<T>("POST", path, { ...options, json }),
  patch: <T>(path: string, json?: unknown, options: RequestOptions = {}) =>
    request<T>("PATCH", path, { ...options, json }),
  delete: <T>(path: string, options: RequestOptions = {}) => request<T>("DELETE", path, options),
};

export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const response = await api.get<Response>(path, { raw: true });
  const blob = await (response as unknown as Response).blob();
  const disposition = (response as unknown as Response).headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = match?.[1] ?? fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function serverApi<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    const response = await fetch(`${API_INTERNAL}/api/v1${path}`, {
      ...init,
      headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}
