"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, CheckCircle2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/toaster";
import { ApiError, api } from "@/lib/api";
import { slugify } from "@/lib/format";
import { saveSession } from "@/lib/session";
import { brandingStyle } from "@/lib/tenant-branding";
import type { TokenResponse } from "@/lib/types";

const PERKS = [
  "Starter plan, free forever",
  "Up to 10 trains and 3 team members",
  "Core reports and availability lookup",
  "White-label branding built in",
];

export default function RegisterPage() {
  const router = useRouter();
  const [orgName, setOrgName] = React.useState("");
  const [slugInput, setSlugInput] = React.useState("");
  const [slugTouched, setSlugTouched] = React.useState(false);
  const slug = slugTouched ? slugInput : slugify(orgName);
  const [fullName, setFullName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const tokens = await api.post<TokenResponse>(
        "/auth/register",
        { org_name: orgName, slug, full_name: fullName, email, password },
        { auth: false },
      );
      saveSession(tokens);
      toast({ title: "Workspace created", description: `Welcome aboard, ${fullName.split(" ")[0]}!`, variant: "success" });
      router.replace("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || "Could not create the workspace.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  const slugValid = /^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$/.test(slug);

  return (
    <div style={brandingStyle()} className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col justify-center px-6 py-12 sm:px-12 lg:px-16">
        <Link href="/" className="mb-10 flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-sm font-bold text-white">
            R
          </span>
          <span className="text-sm font-semibold">RailFlow</span>
        </Link>

        <h1 className="text-2xl font-semibold tracking-tight">Create your workspace</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          You&apos;ll be the owner. Invite your team afterwards.
        </p>

        <form onSubmit={onSubmit} className="mt-8 max-w-md space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="org">Company / railway name</Label>
            <Input
              id="org"
              value={orgName}
              onChange={(event) => setOrgName(event.target.value)}
              placeholder="Blue Ridge Rail"
              required
              minLength={2}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="slug">Workspace slug</Label>
            <Input
              id="slug"
              value={slug}
              onChange={(event) => {
                setSlugTouched(true);
                setSlugInput(slugify(event.target.value));
              }}
              placeholder="blue-ridge-rail"
              required
            />
            <p className={slug && !slugValid ? "text-[11px] text-danger" : "text-[11px] text-muted-foreground"}>
              {slug && !slugValid
                ? "3–32 characters: lowercase letters, numbers and hyphens."
                : `Your console lives at ${slug || "your-slug"}.railflow.app`}
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="name">Your full name</Label>
            <Input
              id="name"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="Amara Diallo"
              autoComplete="name"
              required
              minLength={2}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="email">Work email</Label>
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
              placeholder="At least 8 characters"
              autoComplete="new-password"
              minLength={8}
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
            Create workspace <ArrowRight className="h-4 w-4" />
          </Button>
        </form>

        <p className="mt-6 text-xs text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="text-brand-soft underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </div>

      <div className="relative hidden items-center justify-center overflow-hidden border-l border-border bg-card lg:flex">
        <div className="relative max-w-sm px-10">
          <h2 className="text-xl font-semibold tracking-tight">Launch in minutes</h2>
          <ul className="mt-6 space-y-3">
            {PERKS.map((perk) => (
              <li key={perk} className="flex items-start gap-2.5 text-sm">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                <span className="text-muted-foreground">{perk}</span>
              </li>
            ))}
          </ul>
          <div className="mt-8 rounded-lg border border-border bg-surface-2 p-4 text-xs text-muted-foreground">
            Seeded demo data (trains, bookings, reports) is available in the{" "}
            <span className="font-mono text-foreground">demo</span> workspace — your new workspace
            starts clean.
          </div>
        </div>
      </div>
    </div>
  );
}
