"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Loader2, TrainFront } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/toaster";
import { ApiError, api } from "@/lib/api";
import { saveSession } from "@/lib/session";
import { brandingStyle, logoTextOf } from "@/lib/tenant-branding";
import type { PublicTenant, TokenResponse } from "@/lib/types";

export function LoginForm({ initialSlug }: { initialSlug: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") || "/dashboard";

  const [slug, setSlug] = React.useState(initialSlug);
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const tenantQuery = useQuery({
    queryKey: ["public-tenant", slug],
    queryFn: () => api.get<PublicTenant>("/public/tenant", { query: { slug }, auth: false }),
    enabled: Boolean(slug),
    retry: false,
  });
  const tenant = tenantQuery.data ?? null;

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const tokens = await api.post<TokenResponse>(
        "/auth/login",
        { email, password, tenant_slug: slug },
        { auth: false },
      );
      saveSession(tokens);
      toast({ title: `Welcome back, ${tokens.user.full_name.split(" ")[0]}`, variant: "success" });
      router.replace(next);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(
          err.status === 404
            ? `No workspace found with the slug “${slug}”.`
            : err.message || "Invalid email or password.",
        );
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  function fillDemo() {
    setSlug("demo");
    setEmail("demo@railway.demo");
    setPassword("demo1234");
  }

  return (
    <div style={brandingStyle(tenant?.branding)} className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col justify-center px-6 py-12 sm:px-12 lg:px-16">
        <Link href="/" className="mb-10 flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-sm font-bold text-white">
            R
          </span>
          <span className="text-sm font-semibold">RailFlow</span>
        </Link>

        <h1 className="text-2xl font-semibold tracking-tight">Sign in to your workspace</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Enter your credentials and workspace slug to continue.
        </p>

        <form onSubmit={onSubmit} className="mt-8 max-w-md space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="slug">Workspace slug</Label>
            <Input
              id="slug"
              value={slug}
              onChange={(event) => setSlug(event.target.value.toLowerCase().trim())}
              placeholder="demo"
              autoComplete="organization"
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@company.com"
              autoComplete="email"
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          </div>

          {error ? (
            <p role="alert" className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">
              {error}
            </p>
          ) : null}

          <Button type="submit" size="lg" className="w-full" disabled={submitting}>
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Sign in <ArrowRight className="h-4 w-4" />
          </Button>
        </form>

        <p className="mt-6 text-xs text-muted-foreground">
          New here?{" "}
          <Link href="/register" className="text-brand-soft underline-offset-4 hover:underline">
            Create a workspace
          </Link>
        </p>

        <div className="mt-6 w-full max-w-md rounded-lg border border-border bg-surface-2 p-3 text-xs lg:hidden">
          <p className="text-muted-foreground">
            Demo workspace: slug <span className="font-mono text-foreground">demo</span> · email{" "}
            <span className="font-mono text-foreground">demo@railway.demo</span> · password{" "}
            <span className="font-mono text-foreground">demo1234</span>
          </p>
          <Button type="button" variant="secondary" size="sm" className="mt-2 w-full" onClick={fillDemo}>
            Use demo credentials
          </Button>
        </div>
      </div>

      <div className="relative hidden items-center justify-center overflow-hidden border-l border-border bg-card lg:flex">
        <div className="relative max-w-sm px-10 text-center">
          <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-lg bg-brand text-white">
            <TrainFront className="h-6 w-6" />
          </span>
          <h2 className="mt-6 text-xl font-semibold tracking-tight">
            {tenant ? logoTextOf(tenant.name, tenant.branding) : "Railway operations console"}
          </h2>
          <p className="mt-3 text-sm text-muted-foreground">
            {tenant
              ? `Signing in to ${tenant.name} · ${tenant.plan_code} plan`
              : "Schedules, seat inventory, reservations and analytics in one workspace."}
          </p>
          <div className="mt-8 space-y-2 rounded-lg border border-border bg-surface-2 p-4 text-left text-xs">
            <p className="font-medium text-foreground">Demo workspace</p>
            <p className="text-muted-foreground">
              slug <span className="font-mono text-foreground">demo</span>
            </p>
            <p className="text-muted-foreground">
              email <span className="font-mono text-foreground">demo@railway.demo</span>
            </p>
            <p className="text-muted-foreground">
              password <span className="font-mono text-foreground">demo1234</span>
            </p>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="mt-1 w-full"
              onClick={fillDemo}
            >
              Use demo credentials
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
