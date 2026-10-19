"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, BarChart3, Lock, TrendingUp } from "lucide-react";
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useMe } from "@/components/require-auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/ui/page-header";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatShortDate, money, percent, todayISO } from "@/lib/format";
import { accentOf, primaryOf } from "@/lib/tenant-branding";
import type { OccupancyRow, ReportOverview, RevenuePoint } from "@/lib/types";

interface RevenueOut {
  days: RevenuePoint[];
  currency?: string;
}

interface TopTrainsOut {
  days: number;
  currency: string;
  trains: Array<{
    train_id: string;
    number: string;
    name: string;
    bookings: number;
    seats: number;
    revenue_cents: number;
  }>;
}

interface OccupancyOut {
  date: string;
  trains: OccupancyRow[];
}

function UpgradeCard() {
  return (
    <Card className="border-brand/30">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Lock className="h-4 w-4 text-brand-soft" />
          <CardTitle>Advanced analytics is a Growth feature</CardTitle>
        </div>
        <CardDescription>
          Unlock revenue trends, top-performing trains and daily occupancy breakdowns.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button asChild>
          <Link href="/billing">
            Compare plans <ArrowUpRight className="h-4 w-4" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

export default function ReportsPage() {
  const { me } = useMe();
  const advanced = Boolean(me.entitlements.features["reports.advanced"]);
  const [days, setDays] = React.useState("30");
  const [occupancyDate, setOccupancyDate] = React.useState(todayISO());

  const overview = useQuery({
    queryKey: ["reports", "overview"],
    queryFn: () => api.get<ReportOverview>("/reports/overview"),
  });

  const revenue = useQuery({
    queryKey: ["reports", "revenue", days],
    queryFn: () => api.get<RevenueOut>("/reports/revenue", { query: { days } }),
    enabled: advanced,
  });

  const topTrains = useQuery({
    queryKey: ["reports", "top-trains", days],
    queryFn: () => api.get<TopTrainsOut>("/reports/top-trains", { query: { days } }),
    enabled: advanced,
  });

  const occupancy = useQuery({
    queryKey: ["reports", "occupancy", occupancyDate],
    queryFn: () => api.get<OccupancyOut>("/reports/occupancy", { query: { on: occupancyDate } }),
    enabled: advanced,
  });

  const currency = overview.data?.currency ?? "USD";
  const brandPrimary = primaryOf(me.tenant.branding);
  const brandAccent = accentOf(me.tenant.branding);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        description="Revenue, demand and fleet utilisation."
        actions={
          advanced ? (
            <Select value={days} onValueChange={setDays}>
              <SelectTrigger aria-label="Report period" className="w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
                <SelectItem value="180">Last 180 days</SelectItem>
              </SelectContent>
            </Select>
          ) : null
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
            value={money(overview.data.revenue.last_30d_cents, currency)}
            hint={`${money(overview.data.revenue.today_cents, currency)} today`}
            icon={<TrendingUp />}
          />
          <StatCard
            label="Bookings · 30 days"
            value={String(overview.data.bookings.last_30d)}
            hint={`${overview.data.bookings.today} today`}
          />
          <StatCard
            label="Occupancy today"
            value={percent(overview.data.occupancy_today.rate)}
            hint={`${overview.data.occupancy_today.booked}/${overview.data.occupancy_today.capacity} seats`}
          />
          <StatCard
            label="Cancellation rate · 30d"
            value={percent(overview.data.cancellation_rate_30d, 1)}
            hint={`${Math.round(overview.data.cancellation_rate_30d * overview.data.bookings.last_30d)} cancelled`}
          />
        </div>
      ) : null}

      {!advanced ? <UpgradeCard /> : null}

      {advanced ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Revenue & bookings</CardTitle>
              <CardDescription>Daily revenue with booking volume overlay</CardDescription>
            </CardHeader>
            <CardContent className="h-80">
              {revenue.isLoading ? (
                <Skeleton className="h-full rounded-lg" />
              ) : revenue.data && revenue.data.days.length > 0 ? (
                <>
                  <div className="h-full" role="img" aria-label="Daily revenue and bookings">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart
                        accessibilityLayer={false}
                        data={revenue.data.days.map((point) => ({
                          ...point,
                          label: formatShortDate(point.day),
                        }))}
                        margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
                      >
                        <CartesianGrid stroke="var(--color-border)" vertical={false} />
                        <XAxis
                          dataKey="label"
                          tick={{ fill: "var(--color-faint-foreground)", fontSize: 11 }}
                          tickLine={false}
                          axisLine={false}
                          minTickGap={24}
                        />
                        <YAxis
                          yAxisId="revenue"
                          tick={{ fill: "var(--color-faint-foreground)", fontSize: 11 }}
                          tickLine={false}
                          axisLine={false}
                          tickFormatter={(value: number) => money(value, currency)}
                          width={80}
                        />
                        <YAxis yAxisId="bookings" orientation="right" hide />
                        <Tooltip
                          contentStyle={{
                            background: "var(--color-surface-2)",
                            border: "1px solid var(--color-border)",
                            borderRadius: 8,
                            fontSize: 12,
                            fontVariantNumeric: "tabular-nums",
                          }}
                          labelStyle={{ color: "var(--color-foreground)" }}
                          formatter={(value, name) =>
                            name === "revenue_cents"
                              ? [money(Number(value ?? 0), currency), "Revenue"]
                              : [Number(value ?? 0), "Bookings"]
                          }
                        />
                        <Bar
                          yAxisId="bookings"
                          dataKey="bookings"
                          fill={brandAccent}
                          fillOpacity={0.35}
                          radius={[4, 4, 0, 0]}
                          maxBarSize={18}
                        />
                        <Area
                          yAxisId="revenue"
                          type="monotone"
                          dataKey="revenue_cents"
                          stroke={brandPrimary}
                          strokeWidth={2}
                          fill={brandPrimary}
                          fillOpacity={0.12}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                  <table className="sr-only">
                    <caption>Daily revenue and bookings</caption>
                    <thead>
                      <tr>
                        <th scope="col">Day</th>
                        <th scope="col">Revenue</th>
                        <th scope="col">Bookings</th>
                      </tr>
                    </thead>
                    <tbody>
                      {revenue.data.days.map((point) => (
                        <tr key={point.day}>
                          <th scope="row">{point.day}</th>
                          <td>{money(point.revenue_cents, currency)}</td>
                          <td>{point.bookings}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              ) : (
                <p className="flex h-full items-center justify-center text-sm text-muted-foreground">
                  No revenue recorded in this window yet.
                </p>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Top trains</CardTitle>
                <CardDescription>Best performers in the selected window</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                {topTrains.isLoading ? (
                  <div className="space-y-2 p-4">
                    {Array.from({ length: 4 }).map((_, index) => (
                      <Skeleton key={index} className="h-9 rounded-lg" />
                    ))}
                  </div>
                ) : topTrains.data && topTrains.data.trains.length > 0 ? (
                  <Table containerClassName="max-h-[40vh] overflow-y-auto" scrollable>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="sticky top-0 z-10 bg-card">Train</TableHead>
                        <TableHead className="sticky top-0 z-10 bg-card text-right">Bookings</TableHead>
                        <TableHead className="sticky top-0 z-10 bg-card text-right">Seats</TableHead>
                        <TableHead className="sticky top-0 z-10 bg-card text-right">Revenue</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {topTrains.data.trains.map((train) => (
                        <TableRow key={train.train_id}>
                          <TableCell>
                            <span className="font-medium">{train.number}</span>
                            <span className="text-muted-foreground"> · {train.name}</span>
                          </TableCell>
                          <TableCell className="text-right tabular-nums">{train.bookings}</TableCell>
                          <TableCell className="text-right tabular-nums">{train.seats}</TableCell>
                          <TableCell className="text-right tabular-nums">
                            {money(train.revenue_cents, topTrains.data.currency)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <p className="p-5 text-sm text-muted-foreground">No bookings in this window.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex-row items-end justify-between gap-3">
                <div>
                  <CardTitle>Occupancy by train</CardTitle>
                  <CardDescription>Seats booked vs capacity for a single date</CardDescription>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="occupancy-date">Date</Label>
                  <Input
                    id="occupancy-date"
                    type="date"
                    value={occupancyDate}
                    onChange={(event) => setOccupancyDate(event.target.value)}
                    className="w-40"
                  />
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {occupancy.isLoading ? (
                  Array.from({ length: 4 }).map((_, index) => (
                    <Skeleton key={index} className="h-12 rounded-lg" />
                  ))
                ) : occupancy.data && occupancy.data.trains.length > 0 ? (
                  occupancy.data.trains.map((train) => (
                    <div key={train.train_id} className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium">
                          {train.number} · {train.name}
                        </span>
                        <span className="text-muted-foreground tabular-nums">
                          {train.booked}/{train.capacity} · {percent(train.rate)}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-white/5">
                        <div
                          className="h-full rounded-full bg-brand"
                          style={{ width: `${Math.min(100, train.rate * 100)}%` }}
                        />
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="py-6 text-center text-sm text-muted-foreground">
                    No trains operate on this date.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
              <CardTitle>What you get on Growth</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3">
            {[
              ["Revenue trends", "Daily revenue and booking volume across any window."],
              ["Top trains", "Spot your best-performing routes instantly."],
              ["Occupancy breakdown", "See per-train utilisation for any date."],
            ].map(([title, description]) => (
              <div key={title} className="rounded-lg border border-border/70 p-4">
                <p className="text-sm font-medium">{title}</p>
                <p className="mt-1 text-xs text-muted-foreground">{description}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {advanced && topTrains.data ? (
        <div className="flex justify-end">
          <Badge variant="muted">
            Window: last {topTrains.data.days} days · currency {currency}
          </Badge>
        </div>
      ) : null}
    </div>
  );
}
