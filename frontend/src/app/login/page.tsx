import { Suspense } from "react";
import { cookies } from "next/headers";

import { LoginForm } from "./login-form";

async function LoginFormLoader({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [params, cookieStore] = await Promise.all([searchParams, cookies()]);
  const tenantParam = params.tenant;
  const slugFromQuery = typeof tenantParam === "string" ? tenantParam : undefined;
  const slug = (slugFromQuery || cookieStore.get("rf_slug")?.value || "demo").toLowerCase();
  return <LoginForm initialSlug={slug} />;
}

function LoginFallback() {
  return (
    <div className="grid min-h-screen place-items-center">
      <div className="flex items-center gap-2.5 text-sm text-muted-foreground">
        <span className="flex h-8 w-8 animate-pulse items-center justify-center rounded-lg bg-brand text-sm font-bold text-white">
          R
        </span>
        Loading workspace…
      </div>
    </div>
  );
}

export default function LoginPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  return (
    <Suspense fallback={<LoginFallback />}>
      <LoginFormLoader searchParams={searchParams} />
    </Suspense>
  );
}
