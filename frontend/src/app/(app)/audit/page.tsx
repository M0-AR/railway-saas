"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Lock, ScrollText, Search, ShieldAlert, X } from "lucide-react";

import { useMe } from "@/components/require-auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatDateTime, relativeTime, titleCase } from "@/lib/format";
import type { AuditEntry, Page } from "@/lib/types";

const ENTITY_TYPES = ["train", "booking", "member", "tenant", "user", "subscription"];

function actionVariant(action: string): "default" | "success" | "warning" | "danger" | "muted" {
  if (action.includes("delete") || action.includes("cancel") || action.includes("deleted")) return "danger";
  if (action.includes("create") || action.includes("register") || action.includes("login")) return "success";
  if (action.includes("update") || action.includes("import")) return "warning";
  return "muted";
}

export default function AuditPage() {
  const { me } = useMe();
  const canView = ["owner", "admin"].includes(me.user.role);
  const entitled = Boolean(me.entitlements.features["audit.view"]);

  const [search, setSearch] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [action, setAction] = React.useState("");
  const [entityType, setEntityType] = React.useState("all");
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");
  const [page, setPage] = React.useState(1);

  React.useEffect(() => {
    const timer = window.setTimeout(() => {
      setQuery(search.trim());
      setPage(1);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [search]);

  const entries = useQuery({
    queryKey: ["audit", { query, action, entityType, dateFrom, dateTo, page }],
    queryFn: () =>
      api.get<Page<AuditEntry>>("/audit", {
        query: {
          q: query || undefined,
          action: action.trim() || undefined,
          entity_type: entityType === "all" ? undefined : entityType,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          page,
          page_size: 25,
        },
      }),
    enabled: canView && entitled,
  });

  if (!canView) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-warning" />
            <CardTitle>Restricted area</CardTitle>
          </div>
          <CardDescription>
            The audit log is available to workspace owners and admins.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (!entitled) {
    return (
      <Card className="border-brand/30">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-brand-soft" />
            <CardTitle>Audit log is a Growth feature</CardTitle>
          </div>
          <CardDescription>
            Track every sensitive action — logins, bookings, team and billing changes.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link href="/billing">Compare plans</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  const totalPages = entries.data
    ? Math.max(1, Math.ceil(entries.data.total / entries.data.page_size))
    : 1;

  const hasFilters =
    query.length > 0 ||
    action.trim().length > 0 ||
    entityType !== "all" ||
    dateFrom.length > 0 ||
    dateTo.length > 0;

  const clearFilters = () => {
    setSearch("");
    setQuery("");
    setAction("");
    setEntityType("all");
    setDateFrom("");
    setDateTo("");
    setPage(1);
  };

  const total = entries.data?.total ?? 0;
  const pageSize = entries.data?.page_size ?? 25;
  const rangeStart = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const rangeEnd = Math.min(total, page * pageSize);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit log"
        description="Immutable trail of every sensitive action in this workspace."
      />

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search actor, entity or payload…"
            className="pl-9"
          />
        </div>
        <Input
          value={action}
          onChange={(event) => {
            setAction(event.target.value);
            setPage(1);
          }}
          placeholder="Action contains…"
          className="w-52"
        />
        <Select
          value={entityType}
          onValueChange={(value) => {
            setEntityType(value);
            setPage(1);
          }}
        >
          <SelectTrigger aria-label="Filter by entity" className="w-40">
            <SelectValue placeholder="Entity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All entities</SelectItem>
            {ENTITY_TYPES.map((entity) => (
              <SelectItem key={entity} value={entity}>
                {titleCase(entity)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          type="date"
          aria-label="From date"
          value={dateFrom}
          onChange={(event) => {
            setDateFrom(event.target.value);
            setPage(1);
          }}
          className="w-40 tabular-nums"
        />
        <Input
          type="date"
          aria-label="To date"
          value={dateTo}
          onChange={(event) => {
            setDateTo(event.target.value);
            setPage(1);
          }}
          className="w-40 tabular-nums"
        />
        {hasFilters ? (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            <X className="h-3.5 w-3.5" /> Clear
          </Button>
        ) : null}
      </div>

      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {entries.isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-9 rounded-lg" />
              ))}
            </div>
          ) : entries.data && entries.data.items.length > 0 ? (
            <Table containerClassName="max-h-[65vh] overflow-y-auto" scrollable>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 z-10 bg-card">When</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Actor</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Action</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Entity</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">IP</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card text-right">Payload</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.data.items.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="text-muted-foreground">
                      <span title={formatDateTime(entry.created_at)}>
                        {relativeTime(entry.created_at)}
                      </span>
                    </TableCell>
                    <TableCell>{entry.actor_email || "system"}</TableCell>
                    <TableCell>
                      <Badge variant={actionVariant(entry.action)} dot>
                        {entry.action}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {entry.entity_type ? titleCase(entry.entity_type) : "—"}
                      {entry.entity_id ? (
                        <span className="font-mono text-[11px] text-faint-foreground">
                          {" · "}
                          {entry.entity_id.slice(0, 8)}
                        </span>
                      ) : null}
                    </TableCell>
                    <TableCell className="font-mono text-[11px] text-muted-foreground">
                      {entry.ip || "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      {entry.payload && Object.keys(entry.payload).length > 0 ? (
                        <details className="group inline-block text-left">
                          <summary className="flex cursor-pointer list-none items-center justify-end gap-1 text-[11px] text-faint-foreground transition-colors hover:text-foreground">
                            View
                            <ChevronDown className="h-3 w-3 transition-transform group-open:rotate-180" />
                          </summary>
                          <pre className="mt-2 max-h-48 max-w-md overflow-auto rounded-lg border border-border/70 bg-background/70 p-2 text-left font-mono text-[10px] leading-relaxed text-muted-foreground">
                            {JSON.stringify(entry.payload, null, 2)}
                          </pre>
                        </details>
                      ) : (
                        <span className="text-[11px] text-faint-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="p-4">
              <EmptyState
                icon={<ScrollText />}
                title={hasFilters ? "No entries match these filters" : "No audit entries yet"}
                description={
                  hasFilters
                    ? "Try a wider date range or a different action."
                    : "Actions will appear here as your team works."
                }
                action={
                  hasFilters ? (
                    <Button variant="secondary" onClick={clearFilters}>
                      Clear filters
                    </Button>
                  ) : undefined
                }
              />
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between text-xs text-faint-foreground">
        <span className="tabular-nums">
          Showing {rangeStart}–{rangeEnd} of {total}
        </span>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Previous
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
