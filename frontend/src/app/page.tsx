"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BarChart3,
  CalendarCheck,
  CheckCircle2,
  ChevronDown,
  Layers,
  ShieldCheck,
  Ticket,
  TrainFront,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { FALLBACK_PLANS, FEATURE_LABELS, quotaLabel } from "@/lib/plans";
import { brandingStyle } from "@/lib/tenant-branding";
import type { PlanPublic } from "@/lib/types";

const FEATURES = [
  {
    icon: <TrainFront />,
    title: "Fleet management",
    description: "Trains, routes, weekly schedules and seat capacity — with CSV import for fast onboarding.",
  },
  {
    icon: <Ticket />,
    title: "Reservation engine",
    description: "Concurrency-safe booking with PNR codes, per-date inventory and overbooking protection.",
  },
  {
    icon: <CalendarCheck />,
    title: "Availability lookup",
    description: "Check seats left per date in one click, right from the booking dialog.",
  },
  {
    icon: <BarChart3 />,
    title: "Revenue analytics",
    description: "Revenue trends, top trains, occupancy and cancellation rates — updated live.",
  },
  {
    icon: <ShieldCheck />,
    title: "Tenant isolation",
    description: "Row-level security in Postgres keeps every operator's data strictly separated.",
  },
  {
    icon: <Layers />,
    title: "White-label branding",
    description: "Your logo, your colors, your domain — the console becomes your product.",
  },
];

const FAQ = [
  {
    question: "Can I switch plans later?",
    answer:
      "Yes. Change plans anytime from the Billing page — upgrades take effect immediately, and annual billing is arranged with our team. Starter stays free forever.",
  },
  {
    question: "Is my data isolated from other operators?",
    answer:
      "Yes. Every tenant table enforces Postgres row-level security keyed to your workspace, and the API refuses to boot if that isolation is ever misconfigured.",
  },
  {
    question: "Can I bring my existing schedule data?",
    answer:
      "Growth and Enterprise include CSV import for trains, routes and schedules. The seeded demo workspace shows the exact column format.",
  },
  {
    question: "Do you support custom domains and branding?",
    answer:
      "Yes — set your logo and colors on any plan; Growth and Enterprise add your own domain so the console matches your brand end to end.",
  },
];

const ANNUAL_MONTHS = 10;

const PLAN_EXTRAS: Record<string, string[]> = {
  enterprise: [
    "Priority support & onboarding",
    "Custom quota limits",
    "Invoice billing on annual plans",
  ],
};

function priceDisplay(plan: PlanPublic, annual: boolean) {
  if (plan.price_cents === 0) return { amount: "Free", note: "free forever" };
  const monthly = annual ? Math.round((plan.price_cents * ANNUAL_MONTHS) / 12) : plan.price_cents;
  const amount = (monthly / 100).toLocaleString("en-US", {
    style: "currency",
    currency: plan.currency,
    maximumFractionDigits: 0,
  });
  const yearly = ((plan.price_cents * ANNUAL_MONTHS) / 100).toLocaleString("en-US", {
    style: "currency",
    currency: plan.currency,
    maximumFractionDigits: 0,
  });
  return { amount, note: annual ? `per month · billed ${yearly} yearly` : "per month" };
}

function CtaFor({ plan, highlighted }: { plan: PlanPublic; highlighted: boolean }) {
  if (plan.code === "enterprise") {
    return (
      <Button asChild variant="secondary" className="mt-6 w-full">
        <a href="mailto:sales@railflow.app?subject=RailFlow%20Enterprise">Talk to sales</a>
      </Button>
    );
  }
  return (
    <Button asChild variant={highlighted ? "default" : "secondary"} className="mt-6 w-full">
      <Link href="/register">{plan.price_cents === 0 ? "Start free" : "Get started"}</Link>
    </Button>
  );
}

export default function LandingPage() {
  const plans = useQuery({
    queryKey: ["public", "plans"],
    queryFn: () => api.get<PlanPublic[]>("/public/plans"),
    retry: 0,
    staleTime: 5 * 60 * 1000,
  });
  const planList = plans.data && plans.data.length > 0 ? plans.data : FALLBACK_PLANS;
  const [annual, setAnnual] = React.useState(false);

  return (
    <div style={brandingStyle()} className="min-h-screen">
      <header className="scroll-edge sticky top-0 z-30 bg-white/[0.06] backdrop-blur-[20px] backdrop-saturate-[1.8]">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-sm font-bold text-white">
              R
            </span>
            <span className="text-sm font-semibold">RailFlow</span>
          </Link>
          <nav className="flex items-center gap-2">
            <Button asChild variant="ghost" size="sm">
              <Link href="/login">Sign in</Link>
            </Button>
            <Button asChild size="sm">
              <Link href="/register">
                Get started <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </nav>
        </div>
      </header>

      <section className="relative overflow-hidden">
        <div className="mx-auto grid max-w-6xl gap-12 px-4 pb-20 pt-16 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:pt-24">
          <div className="animate-fade-up">
            <Badge className="mb-5">Multi-tenant railway SaaS</Badge>
            <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
              Sell more seats on every departure
            </h1>
            <p className="mt-5 max-w-xl text-base text-muted-foreground">
              RailFlow is the reservation console for passenger railways: schedules, seat inventory,
              bookings, reports and your own branding — isolated per operator, production-ready from
              day one.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button asChild size="lg">
                <Link href="/register">
                  Start free <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="secondary" size="lg">
                <Link href="/login">See the live demo</Link>
              </Button>
            </div>
            <p className="mt-4 text-xs text-muted-foreground">
              Demo workspace: <span className="font-mono text-foreground">demo</span> ·{" "}
              <span className="font-mono text-foreground">demo@railway.demo</span> ·{" "}
              <span className="font-mono text-foreground">demo1234</span>
            </p>
          </div>

          <div className="animate-fade-up rounded-lg border border-border bg-card p-2">
            <div className="rounded-lg border border-border bg-surface-2 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-danger/70" />
                  <span className="h-2.5 w-2.5 rounded-full bg-warning/70" />
                  <span className="h-2.5 w-2.5 rounded-full bg-success/70" />
                </div>
                <span className="text-[11px] text-muted-foreground">
                  demo.railflow.app/dashboard · last 30 days
                </span>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3">
                {[
                  { label: "Revenue", value: "$18,420" },
                  { label: "Bookings", value: "1,284" },
                  { label: "Occupancy", value: "82%" },
                ].map((stat) => (
                  <div key={stat.label} className="rounded-lg border border-border bg-card p-3">
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                      {stat.label}
                    </p>
                    <p className="mt-1.5 text-lg font-semibold tabular-nums">{stat.value}</p>
                  </div>
                ))}
              </div>
              <div className="mt-3 rounded-lg border border-border bg-card p-3">
                <div className="flex h-28 items-end gap-1.5">
                  {[38, 52, 44, 66, 58, 74, 62, 80, 70, 88, 76, 94].map((height, index) => (
                    <div
                      key={index}
                      className="flex-1 rounded-t-md bg-brand/70"
                      style={{ height: `${height}%` }}
                    />
                  ))}
                </div>
              </div>
              <div className="mt-3 space-y-2">
                {[
                  { pnr: "KQ7MPL", route: "RC-101 · Capital Express", status: "confirmed" },
                  { pnr: "4XT9NB", route: "RC-204 · Coastal Line", status: "confirmed" },
                ].map((row) => (
                  <div
                    key={row.pnr}
                    className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card px-3 py-2 text-xs"
                  >
                    <span className="font-mono text-brand-soft">{row.pnr}</span>
                    <span className="truncate text-muted-foreground">{row.route}</span>
                    <span className="flex shrink-0 items-center gap-1.5 text-success">
                      <span className="h-1.5 w-1.5 rounded-full bg-success" />
                      {row.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-border">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <h2 className="text-2xl font-semibold tracking-tight">Everything an operator needs</h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Built on a hardened multi-tenant core: every query is scoped by Postgres row-level
            security, every plan limit is enforced server-side.
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <div key={feature.title} className="rounded-lg border border-border bg-card p-5">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand/15 text-brand-soft [&_svg]:h-5 [&_svg]:w-5">
                  {feature.icon}
                </span>
                <h3 className="mt-4 text-sm font-semibold">{feature.title}</h3>
                <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing" className="border-t border-border">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <div className="flex flex-wrap items-end justify-between gap-6">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Simple, per-workspace pricing</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Start free. Upgrade when you grow — quotas scale with your fleet.
              </p>
            </div>
            <div
              role="group"
              aria-label="Billing period"
              className="inline-flex items-center gap-1 rounded-lg border border-border bg-card p-1"
            >
              <button
                type="button"
                aria-pressed={!annual}
                onClick={() => setAnnual(false)}
                className={
                  annual
                    ? "h-7 rounded-md px-3 text-xs text-muted-foreground transition-colors hover:text-foreground"
                    : "h-7 rounded-md bg-white/10 px-3 text-xs font-medium text-foreground"
                }
              >
                Monthly
              </button>
              <button
                type="button"
                aria-pressed={annual}
                onClick={() => setAnnual(true)}
                className={
                  annual
                    ? "h-7 rounded-md bg-white/10 px-3 text-xs font-medium text-foreground"
                    : "h-7 rounded-md px-3 text-xs text-muted-foreground transition-colors hover:text-foreground"
                }
              >
                Annual · 2 months free
              </button>
            </div>
          </div>

          <div className="mt-10 grid gap-5 lg:grid-cols-3">
            {planList.map((plan, index) => {
              const highlighted = plan.code === "growth";
              const previous = planList[index - 1];
              const inherited = previous
                ? Object.keys(plan.features).filter(
                    (key) => Boolean(plan.features[key]) && !Boolean(previous.features[key]),
                  )
                : [];
              const listed = previous
                ? inherited
                : Object.keys(plan.features).filter((key) => Boolean(plan.features[key]));
              const price = priceDisplay(plan, annual);
              return (
                <div
                  key={plan.code}
                  className={
                    highlighted
                      ? "relative rounded-lg border border-brand/50 bg-card p-6"
                      : "rounded-lg border border-border bg-card p-6"
                  }
                >
                  {highlighted ? (
                    <Badge className="absolute -top-2.5 left-6">Most popular</Badge>
                  ) : null}
                  <h3 className="text-sm font-semibold">{plan.name}</h3>
                  <p className="mt-3 text-3xl font-semibold tracking-tight tabular-nums">
                    {price.amount}
                  </p>
                  <p className="mt-1.5 text-[11px] text-muted-foreground">{price.note}</p>
                  <p className="mt-3 text-xs text-muted-foreground">{plan.description}</p>
                  <ul className="mt-5 space-y-2">
                    {previous ? (
                      <li className="text-xs font-medium text-foreground">
                        Everything in {previous.name}, plus:
                      </li>
                    ) : null}
                    {(PLAN_EXTRAS[plan.code] ?? []).map((extra) => (
                      <li key={extra} className="flex items-center gap-2 text-xs">
                        <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" />
                        {extra}
                      </li>
                    ))}
                    {listed.map((key) => (
                      <li key={key} className="flex items-center gap-2 text-xs">
                        <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" />
                        {FEATURE_LABELS[key] ?? key}
                      </li>
                    ))}
                    <li className="flex items-center gap-2 text-xs">
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" />
                      {plan.quotas.max_trains === -1
                        ? "Unlimited trains"
                        : `Up to ${quotaLabel(plan.quotas.max_trains)} trains`}{" "}
                      ·{" "}
                      {plan.quotas.max_users === -1
                        ? "unlimited members"
                        : `up to ${quotaLabel(plan.quotas.max_users)} members`}
                    </li>
                    <li className="flex items-center gap-2 text-xs">
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" />
                      {plan.quotas.max_bookings_per_month === -1
                        ? "Unlimited bookings"
                        : `${Number(plan.quotas.max_bookings_per_month).toLocaleString("en-US")} bookings / month`}
                    </li>
                  </ul>
                  <CtaFor plan={plan} highlighted={highlighted} />
                </div>
              );
            })}
          </div>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            No credit card required · Cancel anytime · Every workspace runs in its own isolated data
            space
          </p>
        </div>
      </section>

      <section className="border-t border-border">
        <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
          <h2 className="text-2xl font-semibold tracking-tight">Questions, answered</h2>
          <div className="mt-6 divide-y divide-border overflow-hidden rounded-lg border border-border bg-card">
            {FAQ.map((item) => (
              <details key={item.question} className="group px-4 py-3">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-medium [&::-webkit-details-marker]:hidden">
                  {item.question}
                  <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
                </summary>
                <p className="mt-2 max-w-2xl text-xs leading-relaxed text-muted-foreground">
                  {item.answer}
                </p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-8 text-xs text-muted-foreground sm:flex-row sm:px-6">
          <p>© RailFlow · Railway operations, simplified.</p>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-brand" />
            <Link href="/login" className="transition-colors hover:text-foreground">
              Sign in
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
