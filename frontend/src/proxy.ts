import { NextResponse, type NextRequest } from "next/server";

const APP_DOMAIN = (
  process.env.NEXT_PUBLIC_APP_DOMAIN ||
  process.env.APP_DOMAIN ||
  "localhost"
).toLowerCase();
const RESERVED = new Set(["www", "app", "api", "admin", "static"]);

export function proxy(request: NextRequest) {
  const { nextUrl } = request;
  let slug = nextUrl.searchParams.get("tenant")?.trim().toLowerCase() ?? "";

  if (!slug) {
    const host = (request.headers.get("host") ?? "").split(":")[0].toLowerCase();
    const base = APP_DOMAIN.split(":")[0];
    if (base && host.endsWith(`.${base}`)) {
      const candidate = host.slice(0, -(base.length + 1));
      if (candidate && !candidate.includes(".") && !RESERVED.has(candidate)) {
        slug = candidate;
      }
    }
  }

  const requestHeaders = new Headers(request.headers);
  if (slug) {
    requestHeaders.set("x-tenant-slug", slug);
  }

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  if (slug) {
    response.cookies.set("rf_slug", slug, {
      path: "/",
      maxAge: 60 * 60 * 24,
      sameSite: "lax",
    });
  }
  return response;
}

export const config = {
  matcher: ["/((?!_next/|favicon\\.ico|.*\\.(?:png|jpg|jpeg|svg|gif|webp|ico|css|js|woff|woff2|ttf|map)$).*)"],
};
