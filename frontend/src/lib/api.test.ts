import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, downloadFile, serverApi } from "@/lib/api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const tokens = { access_token: "new-access", refresh_token: "new-refresh" };

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  window.localStorage.clear();
  window.history.replaceState({}, "", "/");
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("request building", () => {
  it("serializes query params and skips empty values", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }));

    await api.get("/trains", {
      auth: false,
      query: { page: 2, q: "night owl", active: true, skip: undefined, nil: null, empty: "" },
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/trains?page=2&q=night+owl&active=true", {
      method: "GET",
      headers: {},
      body: undefined,
    });
  });

  it("attaches the bearer token when present", async () => {
    window.localStorage.setItem("rf_access_token", "stored-token");
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }));

    await api.get("/me");

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.authorization).toBe("Bearer stored-token");
  });

  it("supports JSON bodies and PATCH", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }));

    await api.patch("/settings", { default_currency: "EUR" });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("PATCH");
    expect(init.headers["content-type"]).toBe("application/json");
    expect(init.body).toBe(JSON.stringify({ default_currency: "EUR" }));
  });

  it("returns undefined for 204 responses and passes raw responses through", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await expect(api.delete("/bookings/1")).resolves.toBeUndefined();

    const raw = jsonResponse({ ok: true });
    fetchMock.mockResolvedValueOnce(raw);
    await expect(api.get<Response>("/export", { raw: true })).resolves.toBe(raw);
  });
});

describe("error handling", () => {
  it("maps API error envelopes onto ApiError", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: "quota_exceeded",
            message: "Your plan allows 10 trains.",
            details: { quota: "max_trains", limit: 10 },
          },
        },
        402,
      ),
    );

    const failure = await api.get("/trains").catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(ApiError);
    const error = failure as ApiError;
    expect(error.status).toBe(402);
    expect(error.code).toBe("quota_exceeded");
    expect(error.message).toBe("Your plan allows 10 trains.");
    expect(error.details).toEqual({ quota: "max_trains", limit: 10 });
    expect(error.isPlanGate).toBe(true);
  });

  it("falls back to FastAPI validation details", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          detail: [
            { loc: ["body", "email"], msg: "value is not a valid email address" },
            { loc: ["body", "password"], msg: "too short" },
          ],
        },
        422,
      ),
    );

    const error = (await api.post("/auth/register", {}).catch((err: unknown) => err)) as ApiError;

    expect(error.code).toBe("validation_error");
    expect(error.message).toBe(
      "email: value is not a valid email address · password: too short",
    );
    expect(error.details.errors).toHaveLength(2);
  });

  it("keeps a generic message when the body is not JSON", async () => {
    fetchMock.mockResolvedValue(new Response("nope", { status: 500 }));

    const error = (await api.get("/me").catch((err: unknown) => err)) as ApiError;

    expect(error.status).toBe(500);
    expect(error.message).toBe("Request failed (500)");
    expect(error.code).toBe("error");
  });
});

describe("token refresh", () => {
  it("refreshes once and replays the failed request", async () => {
    window.localStorage.setItem("rf_access_token", "old-access");
    window.localStorage.setItem("rf_refresh_token", "old-refresh");

    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({ error: { code: "unauthorized", message: "expired" } }, 401),
      )
      .mockResolvedValueOnce(jsonResponse(tokens))
      .mockResolvedValueOnce(jsonResponse({ slug: "demo" }));

    await expect(api.get("/me")).resolves.toEqual({ slug: "demo" });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    const [refreshUrl, refreshInit] = fetchMock.mock.calls[1];
    expect(refreshUrl).toBe("/api/v1/auth/refresh");
    expect(JSON.parse(refreshInit.body)).toEqual({ refresh_token: "old-refresh" });

    const [retryUrl, retryInit] = fetchMock.mock.calls[2];
    expect(retryUrl).toBe("/api/v1/me");
    expect(retryInit.headers.authorization).toBe("Bearer new-access");
    expect(window.localStorage.getItem("rf_refresh_token")).toBe("new-refresh");
  });

  it("shares one refresh between concurrent 401s", async () => {
    window.localStorage.setItem("rf_access_token", "old-access");
    window.localStorage.setItem("rf_refresh_token", "old-refresh");
    let refreshCalls = 0;

    fetchMock.mockImplementation(async (url: string, init: { headers: Record<string, string> }) => {
      if (url.endsWith("/auth/refresh")) {
        refreshCalls += 1;
        return jsonResponse(tokens);
      }
      if (init.headers.authorization === "Bearer new-access") {
        return jsonResponse({ ok: true });
      }
      return jsonResponse({ error: { code: "unauthorized", message: "expired" } }, 401);
    });

    await expect(Promise.all([api.get("/a"), api.get("/b")])).resolves.toEqual([
      { ok: true },
      { ok: true },
    ]);
    expect(refreshCalls).toBe(1);
  });

  it("clears the session when refresh fails without redirecting on /login", async () => {
    window.localStorage.setItem("rf_access_token", "old-access");
    window.localStorage.setItem("rf_refresh_token", "old-refresh");
    window.history.replaceState({}, "", "/login");

    fetchMock.mockImplementation(async (url: string) => {
      if (url.endsWith("/auth/refresh")) return jsonResponse({}, 401);
      return jsonResponse({ error: { code: "unauthorized", message: "expired" } }, 401);
    });

    const error = (await api.get("/me").catch((err: unknown) => err)) as ApiError;

    expect(error.status).toBe(401);
    expect(error.message).toBe("Your session has expired. Please sign in again.");
    expect(window.localStorage.getItem("rf_access_token")).toBeNull();
    expect(window.localStorage.getItem("rf_refresh_token")).toBeNull();
  });

  it("redirects to login with a next hop when refresh fails elsewhere", async () => {
    window.localStorage.setItem("rf_access_token", "old-access");
    window.localStorage.setItem("rf_refresh_token", "old-refresh");
    const replace = vi.fn();
    vi.stubGlobal("window", {
      localStorage: window.localStorage,
      location: { pathname: "/trains", search: "?page=2", replace },
      dispatchEvent: vi.fn(),
    });
    fetchMock.mockImplementation(async (url: string) => {
      if (url.endsWith("/auth/refresh")) return jsonResponse({}, 401);
      return jsonResponse({ error: { code: "unauthorized", message: "expired" } }, 401);
    });

    await api.get("/me").catch(() => undefined);

    expect(replace).toHaveBeenCalledWith("/login?next=%2Ftrains%3Fpage%3D2");
  });

  it("expires the session when no refresh token is stored", async () => {
    window.history.replaceState({}, "", "/login");
    fetchMock.mockResolvedValue(
      jsonResponse({ error: { code: "unauthorized", message: "expired" } }, 401),
    );

    const error = (await api.get("/me").catch((err: unknown) => err)) as ApiError;

    expect(error.status).toBe(401);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("expires the session when the refresh call fails at the network level", async () => {
    window.localStorage.setItem("rf_access_token", "old-access");
    window.localStorage.setItem("rf_refresh_token", "old-refresh");
    window.history.replaceState({}, "", "/login");
    fetchMock.mockImplementation(async (url: string) => {
      if (url.endsWith("/auth/refresh")) throw new Error("offline");
      return jsonResponse({ error: { code: "unauthorized", message: "expired" } }, 401);
    });

    const error = (await api.get("/me").catch((err: unknown) => err)) as ApiError;

    expect(error.status).toBe(401);
    expect(window.localStorage.getItem("rf_refresh_token")).toBeNull();
  });

  it("does not attempt refresh on unauthenticated requests", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ error: { code: "unauthorized", message: "nope" } }, 401),
    );

    await expect(api.get("/public/tenant", { auth: false })).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("downloads and server-side fetches", () => {
  it("uses the server-provided filename", async () => {
    const blob = new Blob(["number,pnr\n"]);
    fetchMock.mockResolvedValue(
      new Response(blob, {
        status: 200,
        headers: { "content-disposition": 'attachment; filename="bookings.csv"' },
      }),
    );
    const createObjectURL = vi.fn(() => "blob:mock");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    await downloadFile("/bookings/export", "fallback.csv");

    expect(click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock");
  });

  it("falls back to the provided filename without a disposition header", async () => {
    fetchMock.mockResolvedValue(new Response(new Blob(["x"]), { status: 200 }));
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:mock"),
      revokeObjectURL: vi.fn(),
    });
    let download = "";
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      download = this.download;
    });

    await downloadFile("/bookings/export", "fallback.csv");

    expect(download).toBe("fallback.csv");
  });

  it("returns parsed payloads and null on failures", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ name: "Demo Rail" }));
    await expect(serverApi("/public/tenant?slug=demo")).resolves.toEqual({ name: "Demo Rail" });

    fetchMock.mockResolvedValueOnce(new Response(null, { status: 500 }));
    await expect(serverApi("/public/tenant?slug=demo")).resolves.toBeNull();

    fetchMock.mockRejectedValueOnce(new Error("offline"));
    await expect(serverApi("/public/tenant?slug=demo")).resolves.toBeNull();
  });
});
