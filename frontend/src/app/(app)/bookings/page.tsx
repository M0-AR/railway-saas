"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, Download, Loader2, Plus, Search, Ticket, X } from "lucide-react";

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
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/ui/page-header";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "@/components/ui/toaster";
import { ApiError, api, downloadFile } from "@/lib/api";
import { formatDateTime, money, titleCase, todayISO } from "@/lib/format";
import type { Availability, Booking, BookingListItem, Page, Train } from "@/lib/types";
import { useDeepLinkFlag } from "@/lib/use-deep-link";

const BOOKING_STATUSES = ["confirmed", "pending", "completed", "cancelled"];
const CHANNELS = ["counter", "phone", "agent", "online"];

const STATUS_VARIANT: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = {
  confirmed: "success",
  pending: "warning",
  cancelled: "danger",
  completed: "muted",
};

function CreateBookingDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <NewBookingForm onCreated={onCreated} onClose={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  );
}

function NewBookingForm({ onCreated, onClose }: { onCreated: () => void; onClose: () => void }) {
  const [trainId, setTrainId] = React.useState("");
  const [travelDate, setTravelDate] = React.useState(todayISO());
  const [seats, setSeats] = React.useState("1");
  const [contactName, setContactName] = React.useState("");
  const [contactEmail, setContactEmail] = React.useState("");
  const [contactPhone, setContactPhone] = React.useState("");
  const [channel, setChannel] = React.useState("counter");
  const [notes, setNotes] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  const trains = useQuery({
    queryKey: ["trains", "picker"],
    queryFn: () => api.get<Page<Train>>("/trains", { query: { is_active: true, page_size: 100 } }),
  });

  const selectedTrain = trains.data?.items.find((train) => train.id === trainId) ?? null;

  const availability = useQuery({
    queryKey: ["availability", trainId, travelDate],
    queryFn: () =>
      api.get<Availability>(`/trains/${trainId}/availability`, {
        query: { date_from: travelDate, days: 1 },
      }),
    enabled: Boolean(trainId) && Boolean(travelDate),
  });

  const dayInfo = availability.data?.days[0] ?? null;
  const seatsLeft = dayInfo?.runs ? dayInfo.seats_left : null;
  const overCapacity = dayInfo?.runs ? Number(seats) > (dayInfo.seats_left ?? 0) : false;

  const create = useMutation({
    mutationFn: () =>
      api.post<Booking>("/bookings", {
        train_id: trainId,
        travel_date: travelDate,
        seats: Number(seats),
        contact_name: contactName.trim(),
        contact_email: contactEmail.trim(),
        contact_phone: contactPhone.trim(),
        passengers: [],
        channel,
        notes: notes.trim(),
      }),
    onSuccess: (booking) => {
      toast({
        title: `Booking ${booking.pnr} confirmed`,
        description: `${booking.seats} seat(s) · ${money(booking.total_fare_cents, booking.currency)}`,
        variant: "success",
      });
      onCreated();
      onClose();
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 409) {
        const left = err.details?.seats_left;
        setError(
          left !== undefined
            ? `Not enough seats left — only ${left} available on this date.`
            : err.message,
        );
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Could not create the booking.");
      }
    },
  });

  const valid =
    Boolean(trainId) && Number(seats) >= 1 && Number(seats) <= 10 && contactName.trim().length >= 2;

  return (
    <>
      <DialogHeader>
        <DialogTitle>New booking</DialogTitle>
        <DialogDescription>
          Seats are reserved atomically — the system prevents overbooking.
        </DialogDescription>
      </DialogHeader>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          create.mutate();
        }}
        className="space-y-4"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5 sm:col-span-2">
            <Label>Train</Label>
            <Select value={trainId} onValueChange={setTrainId}>
              <SelectTrigger aria-label="Train">
                <SelectValue placeholder={trains.isLoading ? "Loading trains…" : "Select a train"} />
              </SelectTrigger>
              <SelectContent>
                {(trains.data?.items ?? []).map((train) => (
                  <SelectItem key={train.id} value={train.id}>
                    {train.number} · {train.name} ({train.source} → {train.destination})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="booking-date">Travel date</Label>
            <Input
              id="booking-date"
              type="date"
              min={todayISO()}
              value={travelDate}
              onChange={(event) => setTravelDate(event.target.value)}
              className="tabular-nums"
              required
            />
            {selectedTrain && dayInfo ? (
              dayInfo.runs ? (
                <p className="text-[11px] text-success">
                  Runs on this day · {dayInfo.seats_left} of {selectedTrain.total_seats} seats left
                </p>
              ) : (
                <p className="text-[11px] text-warning">
                  This train does not operate on the selected weekday.
                </p>
              )
            ) : null}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="booking-seats">Seats</Label>
            <Input
              id="booking-seats"
              type="number"
              min={1}
              max={10}
              value={seats}
              onChange={(event) => setSeats(event.target.value)}
              className="tabular-nums"
              required
            />
            {overCapacity ? (
              <p className="text-[11px] text-warning">
                Only {seatsLeft} seat(s) available — booking may be rejected.
              </p>
            ) : null}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="booking-name">Passenger name</Label>
            <Input
              id="booking-name"
              value={contactName}
              onChange={(event) => setContactName(event.target.value)}
              placeholder="Jane Cooper"
              required
              minLength={2}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="booking-phone">Phone</Label>
            <Input
              id="booking-phone"
              value={contactPhone}
              onChange={(event) => setContactPhone(event.target.value)}
              placeholder="+1 555 010 2030"
              className="tabular-nums"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="booking-email">Email</Label>
            <Input
              id="booking-email"
              type="email"
              value={contactEmail}
              onChange={(event) => setContactEmail(event.target.value)}
              placeholder="jane@example.com"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Channel</Label>
            <Select value={channel} onValueChange={setChannel}>
              <SelectTrigger aria-label="Booking channel">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHANNELS.map((item) => (
                  <SelectItem key={item} value={item}>
                    {titleCase(item)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="booking-notes">Notes</Label>
            <Textarea
              id="booking-notes"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Wheelchair assistance, extra luggage…"
              maxLength={2000}
            />
          </div>
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
          <Button type="submit" disabled={!valid || create.isPending || overCapacity}>
            {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Confirm booking
          </Button>
        </DialogFooter>
      </form>
    </>
  );
}

function BookingDetailDialog({
  bookingId,
  onOpenChange,
  onChanged,
}: {
  bookingId: string | null;
  onOpenChange: (open: boolean) => void;
  onChanged: () => void;
}) {
  const [confirming, setConfirming] = React.useState(false);

  const booking = useQuery({
    queryKey: ["booking", bookingId],
    queryFn: () => api.get<Booking>(`/bookings/${bookingId}`),
    enabled: Boolean(bookingId),
  });

  const cancel = useMutation({
    mutationFn: () => api.post<Booking>(`/bookings/${bookingId}/cancel`),
    onSuccess: (result) => {
      toast({ title: `Booking ${result.pnr} cancelled`, variant: "success" });
      setConfirming(false);
      onChanged();
      onOpenChange(false);
    },
    onError: (err) =>
      toast({ title: err instanceof ApiError ? err.message : "Could not cancel", variant: "error" }),
  });

  const data = booking.data;

  return (
    <>
      <Dialog open={Boolean(bookingId)} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl">
          {booking.isLoading ? (
            <div className="space-y-3 py-6">
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
            </div>
          ) : data ? (
            <>
              <DialogHeader>
                <div className="flex flex-wrap items-center gap-3">
                  <DialogTitle className="font-mono">{data.pnr}</DialogTitle>
                  <Badge variant={STATUS_VARIANT[data.status] ?? "muted"} dot>
                    {titleCase(data.status)}
                  </Badge>
                  {data.refund_status !== "none" ? (
                    <Badge variant="warning" dot>
                      Refund {data.refund_status}
                    </Badge>
                  ) : null}
                </div>
                <DialogDescription>
                  {data.train.number} · {data.train.name} · {data.travel_date} ·{" "}
                  {money(data.total_fare_cents, data.currency)}
                </DialogDescription>
              </DialogHeader>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-lg border border-border p-4">
                  <p className="text-[11px] uppercase tracking-[0.08em] text-faint-foreground">Contact</p>
                  <p className="mt-2 text-[13px] font-medium">{data.contact_name}</p>
                  <p className="text-xs text-muted-foreground">{data.contact_email || "—"}</p>
                  <p className="text-xs tabular-nums text-muted-foreground">
                    {data.contact_phone || "—"}
                  </p>
                </div>
                <div className="rounded-lg border border-border p-4">
                  <p className="text-[11px] uppercase tracking-[0.08em] text-faint-foreground">Journey</p>
                  <p className="mt-2 text-[13px] font-medium">
                    {data.train.source} → {data.train.destination}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    <span className="tabular-nums">{data.seats}</span> seat(s) ·{" "}
                    {titleCase(data.channel)} channel
                  </p>
                  <p className="text-xs text-muted-foreground">Booked {formatDateTime(data.created_at)}</p>
                </div>
              </div>

              {data.passengers.length > 0 ? (
                <div className="rounded-lg border border-border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Passenger</TableHead>
                        <TableHead className="text-right">Age</TableHead>
                        <TableHead>Preference</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.passengers.map((passenger, index) => (
                        <TableRow key={passenger.id ?? index}>
                          <TableCell>{passenger.full_name}</TableCell>
                          <TableCell className="text-right tabular-nums text-muted-foreground">
                            {passenger.age ?? "—"}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {passenger.seat_preference || "—"}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : null}

              {data.notes ? (
                <p className="rounded-lg border border-border p-3 text-xs leading-relaxed text-muted-foreground">
                  {data.notes}
                </p>
              ) : null}

              <DialogFooter>
                <Button variant="ghost" onClick={() => onOpenChange(false)}>
                  Close
                </Button>
                {data.status !== "cancelled" ? (
                  <Button variant="danger" onClick={() => setConfirming(true)}>
                    <Ban className="h-4 w-4" /> Cancel booking
                  </Button>
                ) : null}
              </DialogFooter>
            </>
          ) : (
            <p className="py-6 text-center text-sm text-muted-foreground">
              Booking could not be loaded.
            </p>
          )}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title="Cancel this booking?"
        description="Reserved seats are released back to inventory. Refund will be marked pending."
        confirmLabel="Cancel booking"
        danger
        loading={cancel.isPending}
        onConfirm={() => cancel.mutate()}
      />
    </>
  );
}

export default function BookingsPage() {
  const { me } = useMe();
  const queryClient = useQueryClient();
  const canExport = ["owner", "admin", "manager"].includes(me.user.role);

  const [search, setSearch] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [status, setStatus] = React.useState("all");
  const [trainId, setTrainId] = React.useState("all");
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [createOpen, setCreateOpen] = React.useState(false);
  const [createKey, setCreateKey] = React.useState(0);
  const [detailId, setDetailId] = React.useState<string | null>(null);

  const openCreateDialog = () => {
    setCreateKey((key) => key + 1);
    setCreateOpen(true);
  };

  useDeepLinkFlag("new", openCreateDialog);

  React.useEffect(() => {
    const timer = window.setTimeout(() => {
      setQuery(search.trim());
      setPage(1);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [search]);

  const trains = useQuery({
    queryKey: ["trains", "picker"],
    queryFn: () => api.get<Page<Train>>("/trains", { query: { page_size: 100 } }),
  });

  const bookings = useQuery({
    queryKey: ["bookings", { query, status, trainId, dateFrom, dateTo, page }],
    queryFn: () =>
      api.get<Page<BookingListItem>>("/bookings", {
        query: {
          q: query || undefined,
          status: status === "all" ? undefined : status,
          train_id: trainId === "all" ? undefined : trainId,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          page,
          page_size: 20,
        },
      }),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["bookings"] });
    void queryClient.invalidateQueries({ queryKey: ["reports"] });
  };

  const totalPages = bookings.data
    ? Math.max(1, Math.ceil(bookings.data.total / bookings.data.page_size))
    : 1;

  const hasFilters =
    query.length > 0 || status !== "all" || trainId !== "all" || Boolean(dateFrom) || Boolean(dateTo);

  const clearFilters = () => {
    setSearch("");
    setQuery("");
    setStatus("all");
    setTrainId("all");
    setDateFrom("");
    setDateTo("");
    setPage(1);
  };

  const total = bookings.data?.total ?? 0;
  const pageSize = bookings.data?.page_size ?? 20;
  const rangeStart = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const rangeEnd = Math.min(total, page * pageSize);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Bookings"
        description="Reservations across the fleet, with live seat inventory."
        actions={
          <>
            {canExport ? (
              <Button
                variant="secondary"
                onClick={() =>
                  downloadFile("/bookings/export.csv", "bookings.csv").catch(() =>
                    toast({ title: "Export failed", variant: "error" }),
                  )
                }
              >
                <Download className="h-4 w-4" /> Export
              </Button>
            ) : null}
            <Button onClick={openCreateDialog}>
              <Plus className="h-4 w-4" /> New booking
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
            placeholder="Search PNR, name or phone…"
            className="pl-9"
          />
        </div>
        <Select
          value={status}
          onValueChange={(value) => {
            setStatus(value);
            setPage(1);
          }}
        >
          <SelectTrigger aria-label="Filter by status" className="w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {BOOKING_STATUSES.map((item) => (
              <SelectItem key={item} value={item}>
                {titleCase(item)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={trainId}
          onValueChange={(value) => {
            setTrainId(value);
            setPage(1);
          }}
        >
          <SelectTrigger aria-label="Filter by train" className="w-52">
            <SelectValue placeholder="Train" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All trains</SelectItem>
            {(trains.data?.items ?? []).map((train) => (
              <SelectItem key={train.id} value={train.id}>
                {train.number} · {train.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex items-center gap-2">
          <Input
            type="date"
            aria-label="Travel date from"
            value={dateFrom}
            onChange={(event) => {
              setDateFrom(event.target.value);
              setPage(1);
            }}
            className="w-40 tabular-nums"
          />
          <span aria-hidden className="text-xs text-faint-foreground">
            –
          </span>
          <Input
            type="date"
            aria-label="Travel date to"
            value={dateTo}
            onChange={(event) => {
              setDateTo(event.target.value);
              setPage(1);
            }}
            className="w-40 tabular-nums"
          />
        </div>
        {hasFilters ? (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            <X className="h-3.5 w-3.5" /> Clear
          </Button>
        ) : null}
      </div>

      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {bookings.isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-9 rounded-lg" />
              ))}
            </div>
          ) : bookings.data && bookings.data.items.length > 0 ? (
            <Table containerClassName="max-h-[65vh] overflow-y-auto" scrollable>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 z-10 bg-card">PNR</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Train</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Travel date</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Contact</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card text-right">Seats</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card text-right">Fare</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Status</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Channel</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {bookings.data.items.map((booking) => (
                  <TableRow
                    key={booking.id}
                    className="cursor-pointer"
                    onClick={() => setDetailId(booking.id)}
                  >
                    <TableCell>
                      <button
                        type="button"
                        aria-label={`Open booking ${booking.pnr}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          setDetailId(booking.id);
                        }}
                        className="rounded-md bg-white/[0.06] px-1.5 py-0.5 font-mono text-[12px] text-brand-soft hover:bg-white/[0.1]"
                      >
                        {booking.pnr}
                      </button>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      <span className="font-medium">{booking.train_number}</span>
                      <span className="text-muted-foreground"> · {booking.train_name}</span>
                    </TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums text-muted-foreground">
                      {booking.travel_date}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">{booking.contact_name}</TableCell>
                    <TableCell className="text-right tabular-nums">{booking.seats}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {money(booking.total_fare_cents, booking.currency)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANT[booking.status] ?? "muted"} dot>
                        {titleCase(booking.status)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{titleCase(booking.channel)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="p-4">
              <EmptyState
                icon={<Ticket />}
                title={hasFilters ? "No bookings match these filters" : "No bookings yet"}
                description={
                  hasFilters
                    ? "Try a different search, status or date range."
                    : "Create the first reservation to see it here."
                }
                action={
                  hasFilters ? (
                    <Button variant="secondary" onClick={clearFilters}>
                      Clear filters
                    </Button>
                  ) : (
                    <Button onClick={openCreateDialog}>
                      <Plus className="h-4 w-4" /> New booking
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

      <CreateBookingDialog
        key={createKey}
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={invalidate}
      />
      <BookingDetailDialog
        bookingId={detailId}
        onOpenChange={(open) => {
          if (!open) setDetailId(null);
        }}
        onChanged={invalidate}
      />
    </div>
  );
}
