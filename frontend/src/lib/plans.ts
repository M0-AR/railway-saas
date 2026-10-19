import type { PlanPublic } from "@/lib/types";

export const FEATURE_LABELS: Record<string, string> = {
  "reports.basic": "Core reports",
  "reports.advanced": "Advanced analytics",
  "csv.import": "CSV import & export",
  custom_domain: "Custom domain",
  "audit.view": "Audit log",
  "team.roles": "Team roles & permissions",
};

export const QUOTA_LABELS: Record<string, string> = {
  max_trains: "Trains",
  max_users: "Team members",
  max_bookings_per_month: "Bookings / month",
};

export function quotaLabel(value: number | undefined): string {
  if (value === undefined) return "—";
  return value === -1 ? "Unlimited" : String(value);
}

export const FALLBACK_PLANS: PlanPublic[] = [
  {
    code: "starter",
    name: "Starter",
    description: "For small operators getting online.",
    price_cents: 0,
    currency: "USD",
    interval: "month",
    features: {
      "reports.basic": true,
      "reports.advanced": false,
      "csv.import": false,
      custom_domain: false,
      "audit.view": false,
      "team.roles": true,
    },
    quotas: { max_trains: 10, max_users: 3, max_bookings_per_month: 500 },
    sort_order: 0,
  },
  {
    code: "growth",
    name: "Growth",
    description: "For growing railways that need insight and automation.",
    price_cents: 4900,
    currency: "USD",
    interval: "month",
    features: {
      "reports.basic": true,
      "reports.advanced": true,
      "csv.import": true,
      custom_domain: true,
      "audit.view": true,
      "team.roles": true,
    },
    quotas: { max_trains: 100, max_users: 15, max_bookings_per_month: 10000 },
    sort_order: 1,
  },
  {
    code: "enterprise",
    name: "Enterprise",
    description: "Unlimited scale with white-glove support.",
    price_cents: 24900,
    currency: "USD",
    interval: "month",
    features: {
      "reports.basic": true,
      "reports.advanced": true,
      "csv.import": true,
      custom_domain: true,
      "audit.view": true,
      "team.roles": true,
    },
    quotas: { max_trains: -1, max_users: -1, max_bookings_per_month: -1 },
    sort_order: 2,
  },
];

export function planPrice(plan: PlanPublic): string {
  if (plan.price_cents === 0) return "Free";
  const amount = (plan.price_cents / 100).toLocaleString("en-US", {
    style: "currency",
    currency: plan.currency,
    maximumFractionDigits: 0,
  });
  return `${amount}/mo`;
}
