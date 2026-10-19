"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, CreditCard, Minus, Sparkles } from "lucide-react";

import { useMe } from "@/components/require-auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatDate, money, titleCase } from "@/lib/format";
import { FALLBACK_PLANS, FEATURE_LABELS, QUOTA_LABELS, planPrice } from "@/lib/plans";
import type { Page, PlanPublic, ReportOverview, Subscription } from "@/lib/types";
import { cn } from "@/lib/utils";

const ALL_FEATURES = Object.keys(FEATURE_LABELS);

function UsageBar({
  label,
  used,
  limit,
}: {
  label: string;
  used: number | undefined;
  limit: number | undefined;
}) {
  const unlimited = limit === -1;
  const pct =
    unlimited || !limit || used === undefined ? 0 : Math.min(100, Math.round((used / limit) * 100));
  const near = pct >= 80;
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className={cn("font-medium tabular-nums", near && "text-warning")}>
          {(used ?? 0).toLocaleString("en-US")} / {unlimited ? "∞" : ((limit ?? 0).toLocaleString("en-US") || "…")}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
        <div
          className={cn("h-full rounded-full transition-all", near ? "bg-warning" : "bg-brand")}
          style={{ width: unlimited ? "8%" : `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function BillingPage() {
  const { me } = useMe();

  const subscription = useQuery({
    queryKey: ["billing", "subscription"],
    queryFn: () => api.get<Subscription>("/billing/subscription"),
  });

  const plans = useQuery({
    queryKey: ["public", "plans"],
    queryFn: () => api.get<PlanPublic[]>("/public/plans"),
    retry: 1,
  });

  const overview = useQuery({
    queryKey: ["reports", "overview"],
    queryFn: () => api.get<ReportOverview>("/reports/overview"),
  });

  const teamCount = useQuery({
    queryKey: ["team", "count"],
    queryFn: () => api.get<Page<unknown>>("/team/users", { query: { page: 1, page_size: 1 } }),
  });

  const planList = plans.data?.length ? plans.data : FALLBACK_PLANS;
  const current = subscription.data;
  const quotas = current?.quotas ?? me.entitlements.quotas;
  const currency = overview.data?.currency ?? "USD";

  const supportEmail = me.tenant.branding?.support_email || "sales@railflow.app";
  const upgradeHref = (plan: PlanPublic) =>
    `mailto:${supportEmail}?subject=${encodeURIComponent(
      `Upgrade workspace "${me.tenant.name}" to ${plan.name}`,
    )}&body=${encodeURIComponent(
      `Hello,\n\nPlease upgrade workspace "${me.tenant.slug}" (${me.tenant.name}) to the ${plan.name} plan (${planPrice(plan)}).\n\nThanks,\n${me.user.full_name}`,
    )}`;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Billing"
        description="Your plan, usage against quotas, and upgrade options."
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-brand-soft" />
              <CardTitle>Current plan</CardTitle>
            </div>
            <CardDescription>Workspace subscription</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {subscription.isLoading ? (
              <Skeleton className="h-20 rounded-lg" />
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-xl font-semibold">{current?.plan_name ?? me.tenant.plan_code}</span>
                  <Badge variant={current?.status === "active" ? "success" : "warning"} dot>
                    {titleCase(current?.status ?? "active")}
                  </Badge>
                </div>
                {current?.trial_ends_at ? (
                  <p className="text-xs text-muted-foreground">Trial ends {formatDate(current.trial_ends_at)}</p>
                ) : null}
                <div className="flex items-center justify-between rounded-lg border border-border/70 px-3 py-2 text-xs">
                  <span className="text-muted-foreground">Monthly price</span>
                  <span className="font-medium tabular-nums">
                    {planList.find((plan) => plan.code === (current?.plan_code ?? me.tenant.plan_code))
                      ? planPrice(
                          planList.find(
                            (plan) => plan.code === (current?.plan_code ?? me.tenant.plan_code),
                          ) as PlanPublic,
                        )
                      : "—"}
                  </span>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Usage this cycle</CardTitle>
            <CardDescription>Quotas reset with your billing period.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-5 sm:grid-cols-3">
            {overview.isLoading && teamCount.isLoading ? (
              <>
                <Skeleton className="h-10 rounded-lg" />
                <Skeleton className="h-10 rounded-lg" />
                <Skeleton className="h-10 rounded-lg" />
              </>
            ) : (
              <>
                <UsageBar
                  label={QUOTA_LABELS.max_trains}
                  used={overview.data?.trains.total}
                  limit={quotas?.max_trains}
                />
                <UsageBar
                  label={QUOTA_LABELS.max_users}
                  used={teamCount.data?.total}
                  limit={quotas?.max_users}
                />
                <UsageBar
                  label={QUOTA_LABELS.max_bookings_per_month}
                  used={overview.data?.bookings.last_30d}
                  limit={quotas?.max_bookings_per_month}
                />
              </>
            )}
            {overview.data ? (
              <p className="text-xs text-muted-foreground tabular-nums sm:col-span-3">
                30-day revenue {money(overview.data.revenue.last_30d_cents, currency)} ·
                cancellation rate {(overview.data.cancellation_rate_30d * 100).toFixed(1)}%
              </p>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="mb-3 text-[11px] font-medium uppercase tracking-[0.08em] text-faint-foreground">
          Plans
        </h2>
        <div className="grid gap-4 lg:grid-cols-3">
          {planList.map((plan) => {
            const isCurrent = plan.code === (current?.plan_code ?? me.tenant.plan_code);
            const currentPrice = planList.find((p) => p.code === current?.plan_code)?.price_cents ?? 0;
            return (
              <Card
                key={plan.code}
                className={cn("relative", isCurrent && "border-brand/50")}
              >
                {isCurrent ? (
                  <span className="absolute -top-2.5 left-4 rounded-full bg-brand px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-white">
                    Current
                  </span>
                ) : null}
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>{plan.name}</CardTitle>
                    {plan.code === "enterprise" ? (
                      <Sparkles className="h-4 w-4 text-brand-soft" />
                    ) : null}
                  </div>
                  <CardDescription>{plan.description}</CardDescription>
                  <p className="pt-1 text-2xl font-semibold tabular-nums">{planPrice(plan)}</p>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-2 text-xs">
                    {ALL_FEATURES.map((feature) => {
                      const included = Boolean(plan.features[feature]);
                      return (
                        <li key={feature} className="flex items-center gap-2">
                          {included ? (
                            <Check className="h-3.5 w-3.5 text-brand" />
                          ) : (
                            <Minus className="h-3.5 w-3.5 text-faint-foreground" />
                          )}
                          <span className={cn(!included && "text-faint-foreground")}>
                            {FEATURE_LABELS[feature]}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                  <div className="space-y-1 rounded-lg border border-border/70 p-3 text-[11px] tabular-nums">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Trains</span>
                      <span>{quotasText(plan.quotas.max_trains)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Team</span>
                      <span>{quotasText(plan.quotas.max_users)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Bookings / mo</span>
                      <span>{quotasText(plan.quotas.max_bookings_per_month)}</span>
                    </div>
                  </div>
                  {isCurrent ? (
                    <Button variant="secondary" className="w-full" disabled>
                      Active plan
                    </Button>
                  ) : (
                    <Button asChild className="w-full" variant={plan.price_cents > 0 ? "default" : "secondary"}>
                      <a href={upgradeHref(plan)}>
                        {plan.code === "enterprise"
                          ? "Talk to sales"
                          : plan.price_cents > currentPrice
                            ? `Upgrade to ${plan.name}`
                            : `Switch to ${plan.name}`}
                      </a>
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        Plans are activated by our team — the upgrade button opens a pre-filled email to{" "}
        <span className="font-mono">{supportEmail}</span>. Billing changes apply immediately for
        your workspace.
      </p>
    </div>
  );
}

function quotasText(value: number | undefined): string {
  if (value === undefined) return "—";
  return value === -1 ? "Unlimited" : value.toLocaleString("en-US");
}
