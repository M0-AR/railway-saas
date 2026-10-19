"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, Loader2, Plus, Search, ShieldCheck, UserPlus, Users, X } from "lucide-react";

import { useMe } from "@/components/require-auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import { ApiError, api } from "@/lib/api";
import { formatDateTime, initials, relativeTime, titleCase } from "@/lib/format";
import type { Member, Page, Role } from "@/lib/types";
import { useDeepLinkFlag } from "@/lib/use-deep-link";
import { cn } from "@/lib/utils";

const ROLE_VARIANT: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = {
  owner: "default",
  admin: "success",
  manager: "warning",
  agent: "muted",
  viewer: "muted",
};

interface InviteResponse {
  member: Member;
  temporary_password: string | null;
}

function InviteDialog({
  open,
  onOpenChange,
  onInvited,
  actorRole,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onInvited: () => void;
  actorRole: Role;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <InviteForm actorRole={actorRole} onInvited={onInvited} onClose={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  );
}

function InviteForm({
  actorRole,
  onInvited,
  onClose,
}: {
  actorRole: Role;
  onInvited: () => void;
  onClose: () => void;
}) {
  const [fullName, setFullName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [role, setRole] = React.useState<Role>("agent");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [invited, setInvited] = React.useState<InviteResponse | null>(null);
  const [copied, setCopied] = React.useState(false);

  const assignable: Role[] =
    actorRole === "owner"
      ? ["admin", "manager", "agent", "viewer"]
      : ["manager", "agent", "viewer"];

  const invite = useMutation({
    mutationFn: () =>
      api.post<InviteResponse>("/team/users", {
        full_name: fullName.trim(),
        email: email.trim(),
        role,
        password: password ? password : undefined,
      }),
    onSuccess: (result) => {
      setInvited(result);
      onInvited();
    },
    onError: (err) => {
      if (err instanceof ApiError && err.isPlanGate) {
        setError(`${err.message} — upgrade your plan to invite more teammates.`);
      } else {
        setError(err instanceof ApiError ? err.message : "Could not invite the member.");
      }
    },
  });

  return (
    <>
      {invited ? (
        <>
          <DialogHeader>
            <DialogTitle>Invitation ready</DialogTitle>
            <DialogDescription>
              {invited.member.full_name} can sign in with the credentials below.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 rounded-lg border border-border/70 p-4 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-[11px] uppercase tracking-[0.08em] text-faint-foreground">Email</span>
              <span className="font-mono text-xs">{invited.member.email}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] uppercase tracking-[0.08em] text-faint-foreground">Password</span>
              <span className="font-mono text-xs">
                {invited.temporary_password ?? "(set by you)"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] uppercase tracking-[0.08em] text-faint-foreground">Role</span>
              <Badge variant={ROLE_VARIANT[invited.member.role] ?? "muted"}>
                {titleCase(invited.member.role)}
              </Badge>
            </div>
            {invited.temporary_password ? (
              <Button
                variant="secondary"
                size="sm"
                className="w-full"
                onClick={() => {
                  void navigator.clipboard.writeText(invited.temporary_password ?? "");
                  setCopied(true);
                }}
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? "Copied" : "Copy password"}
              </Button>
            ) : null}
          </div>
          <DialogFooter>
            <Button onClick={onClose}>Done</Button>
          </DialogFooter>
        </>
      ) : (
        <>
          <DialogHeader>
            <DialogTitle>Invite a teammate</DialogTitle>
            <DialogDescription>
              They join this workspace immediately with the role you choose.
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              invite.mutate();
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <Label htmlFor="member-name">Full name</Label>
              <Input
                id="member-name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Sam Rivera"
                autoComplete="name"
                required
                minLength={2}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="member-email">Email</Label>
              <Input
                id="member-email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="sam@company.com"
                autoComplete="email"
                required
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Role</Label>
                <Select value={role} onValueChange={(value) => setRole(value as Role)}>
                  <SelectTrigger aria-label="Role">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {assignable.map((item) => (
                      <SelectItem key={item} value={item}>
                        {titleCase(item)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="member-password">Password (optional)</Label>
                <Input
                  id="member-password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Leave empty to generate"
                  autoComplete="new-password"
                  minLength={8}
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
              <Button type="submit" disabled={invite.isPending}>
                {invite.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Send invite
              </Button>
            </DialogFooter>
          </form>
        </>
      )}
    </>
  );
}

export default function TeamPage() {
  const { me } = useMe();
  const queryClient = useQueryClient();
  const [search, setSearch] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [inviteOpen, setInviteOpen] = React.useState(false);
  const [inviteKey, setInviteKey] = React.useState(0);

  const openInviteDialog = () => {
    setInviteKey((key) => key + 1);
    setInviteOpen(true);
  };

  useDeepLinkFlag("new", openInviteDialog);

  React.useEffect(() => {
    const timer = window.setTimeout(() => {
      setQuery(search.trim());
      setPage(1);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [search]);

  const members = useQuery({
    queryKey: ["team", { query, page }],
    queryFn: () =>
      api.get<Page<Member>>("/team/users", {
        query: { q: query || undefined, page, page_size: 20 },
      }),
  });

  const invalidate = () => void queryClient.invalidateQueries({ queryKey: ["team"] });

  const update = useMutation({
    mutationFn: (input: { member: Member; payload: { role?: Role; is_active?: boolean } }) =>
      api.patch<Member>(`/team/users/${input.member.id}`, input.payload),
    onSuccess: (member) => {
      toast({ title: `${member.full_name} updated`, variant: "success" });
      invalidate();
    },
    onError: (err) =>
      toast({
        title: err instanceof ApiError ? err.message : "Update failed",
        variant: "error",
      }),
  });

  function canManage(target: Member): boolean {
    if (target.id === me.user.id) return false;
    if (me.user.role === "owner") return true;
    if (me.user.role === "admin") return !["owner", "admin"].includes(target.role);
    return false;
  }

  function assignableRoles(target: Member): Role[] {
    if (target.role === "owner") return ["owner"];
    if (me.user.role === "owner") {
      return ["admin", "manager", "agent", "viewer"];
    }
    return ["manager", "agent", "viewer"];
  }

  const quota = me.entitlements.quotas.max_users;
  const totalPages = members.data ? Math.max(1, Math.ceil(members.data.total / members.data.page_size)) : 1;

  const hasFilters = query.length > 0;
  const total = members.data?.total ?? 0;
  const pageSize = members.data?.page_size ?? 20;
  const rangeStart = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const rangeEnd = Math.min(total, page * pageSize);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Team"
        description={
          quota === -1
            ? "Unlimited seats on your plan."
            : `${members.data?.total ?? "…"} of ${quota} seats used on the ${me.tenant.plan_code} plan.`
        }
        actions={
          <Button onClick={openInviteDialog}>
            <UserPlus className="h-4 w-4" /> Invite member
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search name or email…"
            className="pl-9"
          />
        </div>
        {hasFilters ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSearch("");
              setQuery("");
              setPage(1);
            }}
          >
            <X className="h-3.5 w-3.5" /> Clear
          </Button>
        ) : null}
      </div>

      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {members.isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-9 rounded-lg" />
              ))}
            </div>
          ) : members.data && members.data.items.length > 0 ? (
            <Table containerClassName="max-h-[65vh] overflow-y-auto" scrollable>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 z-10 bg-card">Member</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Role</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Last login</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Active</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Joined</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.data.items.map((member) => {
                  const manageable = canManage(member);
                  const isSelf = member.id === me.user.id;
                  return (
                    <TableRow key={member.id}>
                      <TableCell>
                        <div className="flex items-center gap-2.5">
                          <span
                            className={cn(
                              "flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[11px] font-semibold",
                              member.is_active
                                ? "bg-brand/20 text-brand-soft"
                                : "bg-white/5 text-muted-foreground",
                            )}
                          >
                            {initials(member.full_name)}
                          </span>
                          <span className="font-medium">{member.full_name}</span>
                          {isSelf ? (
                            <span className="text-[11px] text-faint-foreground">(you)</span>
                          ) : null}
                          <span className="text-muted-foreground"> · {member.email}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        {manageable && member.role !== "owner" ? (
                          <Select
                            value={member.role}
                            onValueChange={(value) =>
                              update.mutate({ member, payload: { role: value as Role } })
                            }
                          >
                            <SelectTrigger aria-label="Member role" className="h-8 w-32">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {assignableRoles(member).map((role) => (
                                <SelectItem key={role} value={role}>
                                  {titleCase(role)}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        ) : (
                          <Badge variant={ROLE_VARIANT[member.role] ?? "muted"} dot>
                            {member.role === "owner" ? (
                              <>
                                <ShieldCheck className="h-3 w-3" /> Owner
                              </>
                            ) : (
                              titleCase(member.role)
                            )}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {member.last_login_at ? (
                          <span title={formatDateTime(member.last_login_at)}>
                            {relativeTime(member.last_login_at)}
                          </span>
                        ) : (
                          "Never"
                        )}
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={member.is_active}
                          disabled={!manageable || update.isPending}
                          onCheckedChange={(checked) =>
                            update.mutate({ member, payload: { is_active: checked } })
                          }
                        />
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDateTime(member.created_at)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <div className="p-4">
              <EmptyState
                icon={<Users />}
                title={hasFilters ? "No members match this search" : "No team members yet"}
                description={
                  hasFilters
                    ? "Try a different name or email."
                    : "Invite colleagues to share the workspace."
                }
                action={
                  hasFilters ? (
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setSearch("");
                        setQuery("");
                        setPage(1);
                      }}
                    >
                      Clear search
                    </Button>
                  ) : (
                    <Button onClick={openInviteDialog}>
                      <Plus className="h-4 w-4" /> Invite member
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

      <InviteDialog
        key={inviteKey}
        open={inviteOpen}
        onOpenChange={setInviteOpen}
        onInvited={invalidate}
        actorRole={me.user.role}
      />
    </div>
  );
}
