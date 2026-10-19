"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, DollarSign, Plus, Ticket, TrainFront, TrendingUp } from "lucide-react";

import { useMe } from "@/components/require-auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { api } from "@/lib/api";
import { formatDateTime, money, percent, titleCase } from "@/lib/format";
import type { BookingListItem, Page, ReportOverview } from "@/lib/types";

const STATUS_VARIANT: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = {
  confirmed: "success",
  pending: "warning",
  cancelled: "danger",
  completed: "muted",
};

export default function DashboardPage() {
  const { me } = useMe();

  const overview = useQuery({
    queryKey: ["reports", "overview"],
    queryFn: () => api.get<ReportOverview>("/reports/overview"),
  });

  const recent = useQuery({
    queryKey: ["bookings", "recent"],
    queryFn: () => api.get<Page<BookingListItem>>("/bookings", { query: { page_size: 6 } }),
  });

  const advanced = Boolean(me.entitlements.features["reports.advanced"]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description={`Here's how ${me.tenant.name} is performing today.`}
        actions={
          <Button asChild>
            <Link href="/bookings?new=1">
              <Plus className="h-4 w-4" /> New booking
            </Link>
          </Button>
        }
      />

      {overview.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-28 rounded-lg" />
          ))}
        </div>
      ) : overview.data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Revenue · 30 days"
            value={money(overview.data.revenue.last_30d_cents, overview.data.currency)}
            hint={`${money(overview.data.revenue.today_cents, overview.data.currency)} today`}
            icon={<DollarSign />}
          />
          <StatCard
            label="Bookings · 30 days"
            value={String(overview.data.bookings.last_30d)}
            hint={`${overview.data.bookings.today} today`}
            icon={<Ticket />}
          />
          <StatCard
            label="Occupancy today"
            value={percent(overview.data.occupancy_today.rate)}
            hint={`${overview.data.occupancy_today.booked}/${overview.data.occupancy_today.capacity} seats`}
            icon={<TrendingUp />}
          />
          <StatCard
            label="Active trains"
            value={`${overview.data.trains.active}`}
            hint={`of ${overview.data.trains.total} fleet`}
            icon={<TrainFront />}
          />
        </div>
      ) : (
        <Card>
          <CardContent className="pt-4 text-sm text-muted-foreground">
            Reports are unavailable right now.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle>Latest bookings</CardTitle>
              <CardDescription>Most recent reservations across your fleet</CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm">
              <Link href="/bookings">
                View all <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {recent.isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-12 rounded-lg" />
                ))}
              </div>
            ) : recent.data && recent.data.items.length > 0 ? (
              <div className="divide-y divide-border">
                {recent.data.items.map((booking) => (
                  <div
                    key={booking.id}
                    className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="shrink-0 rounded-md bg-white/[0.06] px-1.5 py-0.5 font-mono text-[12px] text-brand-soft">
                        {booking.pnr}
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-[13px] font-medium">
                          {booking.train_number} · {booking.train_name}
                        </p>
                        <p className="truncate text-[11px] text-faint-foreground">
                          {booking.travel_date} · {booking.contact_name}
                        </p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <span className="text-[13px] tabular-nums text-muted-foreground">
                        {money(booking.total_fare_cents, booking.currency)}
                      </span>
                      <Badge variant={STATUS_VARIANT[booking.status] ?? "muted"} dot>
                        {titleCase(booking.status)}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No bookings yet — create the first one.
              </p>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Today at a glance</CardTitle>
              <CardDescription>Live operational snapshot</CardDescription>
            </CardHeader>
            <CardContent>
              <div>
                <div className="flex items-center justify-between text-[13px]">
                  <span className="text-muted-foreground">Seat occupancy</span>
                  <span className="font-medium tabular-nums">
                    {overview.data ? percent(overview.data.occupancy_today.rate) : "—"}
                  </span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
                  <div
                    className="h-full rounded-full bg-brand transition-[width] duration-200"
                    style={{
                      width: `${Math.min(100, (overview.data?.occupancy_today.rate ?? 0) * 100)}%`,
                    }}
                  />
                </div>
              </div>
              <dl className="mt-4 space-y-3 border-t border-border pt-4 text-[13px]">
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Bookings today</dt>
                  <dd className="font-medium tabular-nums">{overview.data?.bookings.today ?? "—"}</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Cancellation rate · 30d</dt>
                  <dd className="font-medium tabular-nums">
                    {overview.data ? percent(overview.data.cancellation_rate_30d, 1) : "—"}
                  </dd>
                </div>
              </dl>
              <p className="pt-4 text-[11px] text-faint-foreground">
                Last refreshed {formatDateTime(new Date())}
              </p>
            </CardContent>
          </Card>

          {!advanced ? (
            <Card>
              <CardHeader>
                <CardTitle>Unlock advanced analytics</CardTitle>
                <CardDescription>
                  Revenue trends, top trains and occupancy breakdowns on the Growth plan.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button asChild className="w-full">
                  <Link href="/billing">Compare plans</Link>
                </Button>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
