"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Download,
  Loader2,
  Pencil,
  Plus,
  Search,
  TrainFront,
  Trash2,
  Upload,
  X,
} from "lucide-react";

import { useMe } from "@/components/require-auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/ui/page-header";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "@/components/ui/toaster";
import { ApiError, api, downloadFile } from "@/lib/api";
import { formatTime, money, titleCase } from "@/lib/format";
import type { Page, Train } from "@/lib/types";
import { useDeepLinkFlag } from "@/lib/use-deep-link";
import { cn } from "@/lib/utils";

const TRAIN_TYPES = ["express", "intercity", "regional", "high_speed", "sleeper", "commuter"];
const DAY_LETTERS = ["M", "T", "W", "T", "F", "S", "S"];

interface ImportResult {
  created: number;
  updated: number;
  errors: Array<Record<string, unknown>>;
}

interface TrainFormState {
  number: string;
  name: string;
  train_type: string;
  source: string;
  destination: string;
  departure_time: string;
  arrival_time: string;
  days_of_week: number[];
  total_seats: string;
  fare: string;
}

const EMPTY_FORM: TrainFormState = {
  number: "",
  name: "",
  train_type: "express",
  source: "",
  destination: "",
  departure_time: "08:00",
  arrival_time: "12:00",
  days_of_week: [1, 2, 3, 4, 5, 6, 7],
  total_seats: "120",
  fare: "25.00",
};

function toForm(train: Train): TrainFormState {
  return {
    number: train.number,
    name: train.name,
    train_type: train.train_type,
    source: train.source,
    destination: train.destination,
    departure_time: train.departure_time?.slice(0, 5) ?? "",
    arrival_time: train.arrival_time?.slice(0, 5) ?? "",
    days_of_week: [...train.days_of_week],
    total_seats: String(train.total_seats),
    fare: (train.fare_cents / 100).toFixed(2),
  };
}

function DayChips({
  value,
  onChange,
  compact = false,
}: {
  value: number[];
  onChange?: (next: number[]) => void;
  compact?: boolean;
}) {
  return (
    <div className="flex gap-1">
      {DAY_LETTERS.map((letter, index) => {
        const day = index + 1;
        const active = value.includes(day);
        return (
          <button
            key={day}
            type="button"
            disabled={!onChange}
            aria-label={`Day ${day}`}
            aria-pressed={active}
            onClick={() =>
              onChange?.(
                active ? value.filter((item) => item !== day) : [...value, day].sort((a, b) => a - b),
              )
            }
            className={cn(
              "rounded-md border text-xs font-medium transition-colors",
              compact ? "h-6 w-6 text-[11px]" : "h-8 w-8",
              active
                ? "border-brand/50 bg-brand/20 text-brand-soft"
                : "border-border text-faint-foreground",
              onChange && "hover:border-brand/40 hover:text-foreground",
              !onChange && "cursor-default",
            )}
          >
            {letter}
          </button>
        );
      })}
    </div>
  );
}

function TrainDialog({
  open,
  onOpenChange,
  editing,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editing: Train | null;
  onSaved: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <TrainForm editing={editing} onSaved={onSaved} onClose={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  );
}

function TrainForm({
  editing,
  onSaved,
  onClose,
}: {
  editing: Train | null;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [form, setForm] = React.useState<TrainFormState>(() =>
    editing ? toForm(editing) : EMPTY_FORM,
  );
  const [error, setError] = React.useState<string | null>(null);

  const save = useMutation({
    mutationFn: async () => {
      const payload = {
        number: form.number.trim(),
        name: form.name.trim(),
        train_type: form.train_type,
        source: form.source.trim(),
        destination: form.destination.trim(),
        departure_time: form.departure_time ? `${form.departure_time}:00` : null,
        arrival_time: form.arrival_time ? `${form.arrival_time}:00` : null,
        days_of_week: form.days_of_week,
        total_seats: Number(form.total_seats),
        fare_cents: Math.round(Number(form.fare) * 100),
      };
      if (editing) return api.patch<Train>(`/trains/${editing.id}`, payload);
      return api.post<Train>("/trains", payload);
    },
    onSuccess: (train) => {
      toast({
        title: editing ? "Train updated" : "Train created",
        description: `${train.number} · ${train.name}`,
        variant: "success",
      });
      onSaved();
      onClose();
    },
    onError: (err) => {
      if (err instanceof ApiError && err.isPlanGate) {
        setError(`${err.message} — upgrade your plan to add more trains.`);
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Could not save the train.");
      }
    },
  });

  const valid =
    form.number.trim().length > 0 &&
    form.name.trim().length >= 2 &&
    form.source.trim().length >= 2 &&
    form.destination.trim().length >= 2 &&
    form.days_of_week.length > 0 &&
    Number(form.total_seats) >= 1 &&
    Number(form.total_seats) <= 2000 &&
    Number(form.fare) >= 0;

  return (
    <>
      <DialogHeader>
        <DialogTitle>{editing ? `Edit ${editing.number}` : "New train"}</DialogTitle>
        <DialogDescription>
          Schedules repeat weekly on the days you select.
        </DialogDescription>
      </DialogHeader>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          save.mutate();
        }}
        className="space-y-4"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="train-number">Number</Label>
            <Input
              id="train-number"
              value={form.number}
              onChange={(event) => setForm({ ...form, number: event.target.value })}
              placeholder="RC-101"
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="train-name">Name</Label>
            <Input
              id="train-name"
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              placeholder="Capital Express"
              required
              minLength={2}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Type</Label>
            <Select
              value={form.train_type}
              onValueChange={(value) => setForm({ ...form, train_type: value })}
            >
              <SelectTrigger aria-label="Train type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TRAIN_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {titleCase(type)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="train-departure">Departure</Label>
              <Input
                id="train-departure"
                type="time"
                value={form.departure_time}
                onChange={(event) => setForm({ ...form, departure_time: event.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="train-arrival">Arrival</Label>
              <Input
                id="train-arrival"
                type="time"
                value={form.arrival_time}
                onChange={(event) => setForm({ ...form, arrival_time: event.target.value })}
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="train-source">From</Label>
            <Input
              id="train-source"
              value={form.source}
              onChange={(event) => setForm({ ...form, source: event.target.value })}
              placeholder="Central Station"
              required
              minLength={2}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="train-destination">To</Label>
            <Input
              id="train-destination"
              value={form.destination}
              onChange={(event) => setForm({ ...form, destination: event.target.value })}
              placeholder="Harbor City"
              required
              minLength={2}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="train-seats">Total seats</Label>
            <Input
              id="train-seats"
              type="number"
              min={1}
              max={2000}
              value={form.total_seats}
              onChange={(event) => setForm({ ...form, total_seats: event.target.value })}
              className="tabular-nums"
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="train-fare">Fare (per seat)</Label>
            <Input
              id="train-fare"
              type="number"
              min={0}
              step="0.01"
              value={form.fare}
              onChange={(event) => setForm({ ...form, fare: event.target.value })}
              className="tabular-nums"
              required
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <Label>Operating days</Label>
          <DayChips
            value={form.days_of_week}
            onChange={(days) => setForm({ ...form, days_of_week: days })}
          />
          {form.days_of_week.length === 0 ? (
            <p className="text-[11px] text-danger">Select at least one operating day.</p>
          ) : null}
        </div>

        {error ? (
          <p className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">
            {error}
          </p>
        ) : null}

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!valid || save.isPending}>
            {save.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {editing ? "Save changes" : "Create train"}
          </Button>
        </DialogFooter>
      </form>
    </>
  );
}

export default function TrainsPage() {
  const { me } = useMe();
  const queryClient = useQueryClient();
  const canImport = Boolean(me.entitlements.features["csv.import"]);
  const canDelete = me.user.role === "owner" || me.user.role === "admin";

  const [search, setSearch] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [typeFilter, setTypeFilter] = React.useState("all");
  const [activeFilter, setActiveFilter] = React.useState("all");
  const [page, setPage] = React.useState(1);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [dialogKey, setDialogKey] = React.useState(0);
  const [editing, setEditing] = React.useState<Train | null>(null);
  const [deleting, setDeleting] = React.useState<Train | null>(null);
  const fileRef = React.useRef<HTMLInputElement>(null);

  const openTrainDialog = (train: Train | null) => {
    setEditing(train);
    setDialogKey((key) => key + 1);
    setDialogOpen(true);
  };

  useDeepLinkFlag("new", () => openTrainDialog(null));
  useDeepLinkFlag("import", () => fileRef.current?.click(), canImport);

  React.useEffect(() => {
    const timer = window.setTimeout(() => {
      setQuery(search.trim());
      setPage(1);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [search]);

  const trains = useQuery({
    queryKey: ["trains", { query, typeFilter, activeFilter, page }],
    queryFn: () =>
      api.get<Page<Train>>("/trains", {
        query: {
          q: query || undefined,
          train_type: typeFilter === "all" ? undefined : typeFilter,
          is_active: activeFilter === "all" ? undefined : activeFilter === "active",
          page,
          page_size: 20,
        },
      }),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["trains"] });
    void queryClient.invalidateQueries({ queryKey: ["reports"] });
  };

  const toggleActive = useMutation({
    mutationFn: (train: Train) => api.patch<Train>(`/trains/${train.id}`, { is_active: !train.is_active }),
    onSuccess: (train) => {
      toast({
        title: train.is_active ? "Train activated" : "Train deactivated",
        description: `${train.number} · ${train.name}`,
      });
      invalidate();
    },
    onError: (err) => toast({ title: err instanceof ApiError ? err.message : "Update failed", variant: "error" }),
  });

  const remove = useMutation({
    mutationFn: (train: Train) => api.delete(`/trains/${train.id}`),
    onSuccess: () => {
      toast({ title: "Train deleted", variant: "success" });
      setDeleting(null);
      invalidate();
    },
    onError: (err) =>
      toast({ title: err instanceof ApiError ? err.message : "Could not delete", variant: "error" }),
  });

  const importCsv = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.post<ImportResult>("/trains/import", undefined, { form });
    },
    onSuccess: (result) => {
      toast({
        title: `Import finished: ${result.created} created, ${result.updated} updated`,
        description:
          result.errors.length > 0
            ? `${result.errors.length} row(s) skipped — check the file and retry.`
            : undefined,
        variant: result.errors.length > 0 ? "default" : "success",
      });
      invalidate();
    },
    onError: (err) =>
      toast({
        title:
          err instanceof ApiError && err.isPlanGate
            ? "CSV import requires the Growth plan"
            : err instanceof ApiError
              ? err.message
              : "Import failed",
        variant: "error",
      }),
  });

  const totalPages = trains.data ? Math.max(1, Math.ceil(trains.data.total / trains.data.page_size)) : 1;

  const hasFilters = query.length > 0 || typeFilter !== "all" || activeFilter !== "all";

  const clearFilters = () => {
    setSearch("");
    setQuery("");
    setTypeFilter("all");
    setActiveFilter("all");
    setPage(1);
  };

  const total = trains.data?.total ?? 0;
  const pageSize = trains.data?.page_size ?? 20;
  const rangeStart = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const rangeEnd = Math.min(total, page * pageSize);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Trains"
        description="Manage your fleet, schedules and weekly operating days."
        actions={
          <>
            {canImport ? (
              <>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) importCsv.mutate(file);
                    event.target.value = "";
                  }}
                />
                <Button
                  variant="secondary"
                  onClick={() => fileRef.current?.click()}
                  disabled={importCsv.isPending}
                >
                  {importCsv.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                  Import CSV
                </Button>
                <Button
                  variant="secondary"
                  onClick={() =>
                    downloadFile("/trains/export.csv", "trains.csv").catch(() =>
                      toast({ title: "Export failed", variant: "error" }),
                    )
                  }
                >
                  <Download className="h-4 w-4" /> Export
                </Button>
              </>
            ) : null}
            <Button onClick={() => openTrainDialog(null)}>
              <Plus className="h-4 w-4" /> New train
            </Button>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search number, name or route…"
            className="pl-9"
          />
        </div>
        <Select
          value={typeFilter}
          onValueChange={(value) => {
            setTypeFilter(value);
            setPage(1);
          }}
        >
          <SelectTrigger aria-label="Filter by type" className="w-40">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {TRAIN_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {titleCase(type)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={activeFilter}
          onValueChange={(value) => {
            setActiveFilter(value);
            setPage(1);
          }}
        >
          <SelectTrigger aria-label="Filter by status" className="w-36">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
          </SelectContent>
        </Select>
        {hasFilters ? (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            <X className="h-3.5 w-3.5" /> Clear
          </Button>
        ) : null}
      </div>

      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {trains.isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-9 rounded-lg" />
              ))}
            </div>
          ) : trains.data && trains.data.items.length > 0 ? (
            <Table containerClassName="max-h-[65vh] overflow-y-auto" scrollable>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 z-10 bg-card">Train</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Route</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Type</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Days</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card text-right">Seats</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card text-right">Fare</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Active</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {trains.data.items.map((train) => (
                  <TableRow key={train.id}>
                    <TableCell>
                      <span className="font-medium">{train.number}</span>
                      <span className="text-muted-foreground"> · {train.name}</span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {train.source} → {train.destination}
                      <span className="text-faint-foreground">
                        {" · "}
                        <span className="tabular-nums">
                          {formatTime(train.departure_time)}–{formatTime(train.arrival_time)}
                        </span>
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge variant="muted">{titleCase(train.train_type)}</Badge>
                    </TableCell>
                    <TableCell>
                      <DayChips value={train.days_of_week} compact />
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{train.total_seats}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {money(train.fare_cents, train.currency || "USD")}
                    </TableCell>
                    <TableCell>
                      <Switch
                        checked={train.is_active}
                        aria-label={`${train.number} active`}
                        disabled={toggleActive.isPending}
                        onCheckedChange={() => toggleActive.mutate(train)}
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Edit ${train.number}`}
                          onClick={() => openTrainDialog(train)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        {canDelete ? (
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Delete ${train.number}`}
                            className="text-danger hover:text-danger"
                            onClick={() => setDeleting(train)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="p-4">
              <EmptyState
                icon={<TrainFront />}
                title={hasFilters ? "No trains match these filters" : "No trains yet"}
                description={
                  hasFilters
                    ? "Try a different search, type or status."
                    : "Create your first train or import a CSV to populate the fleet."
                }
                action={
                  hasFilters ? (
                    <Button variant="secondary" onClick={clearFilters}>
                      Clear filters
                    </Button>
                  ) : (
                    <Button onClick={() => openTrainDialog(null)}>
                      <Plus className="h-4 w-4" /> New train
                    </Button>
                  )
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

      <TrainDialog
        key={dialogKey}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editing={editing}
        onSaved={invalidate}
      />

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        title={deleting ? `Delete ${deleting.number}?` : "Delete train?"}
        description="Trains with existing bookings cannot be deleted. Deactivate them instead to hide from booking."
        confirmLabel="Delete"
        danger
        loading={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </div>
  );
}
