"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { Check, Cog, Loader2, Lock, Palette, UserRound } from "lucide-react";

import { useMe } from "@/components/require-auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/ui/page-header";
import { toast } from "@/components/ui/toaster";
import { ApiError, api } from "@/lib/api";
import type { Member, Tenant } from "@/lib/types";
import { cn } from "@/lib/utils";

const PRESETS: Array<{ primary: string; accent: string }> = [
  { primary: "#6d5efc", accent: "#22d3ee" },
  { primary: "#2563eb", accent: "#38bdf8" },
  { primary: "#059669", accent: "#a3e635" },
  { primary: "#e11d48", accent: "#fb923c" },
  { primary: "#b45309", accent: "#facc15" },
];

const HEX_RE = /^#[0-9a-f]{6}$/i;

function ColorField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={HEX_RE.test(value) ? value : "#000000"}
          onChange={(event) => onChange(event.target.value)}
          className="h-9 w-12 cursor-pointer rounded-md border border-border bg-transparent p-1"
        />
        <Input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="#6d5efc"
          className={cn("font-mono text-xs", !HEX_RE.test(value) && "border-danger/50")}
        />
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const { me, refresh } = useMe();
  const tenant = me.tenant;
  const canEditWorkspace = ["owner", "admin"].includes(me.user.role);
  const canCustomDomain = Boolean(me.entitlements.features.custom_domain);

  const [logoText, setLogoText] = React.useState(tenant.branding?.logo_text ?? "");
  const [supportEmail, setSupportEmail] = React.useState(tenant.branding?.support_email ?? "");
  const [primary, setPrimary] = React.useState(tenant.branding?.primary_color ?? "#6d5efc");
  const [accent, setAccent] = React.useState(tenant.branding?.accent_color ?? "#22d3ee");

  const [name, setName] = React.useState(tenant.name);
  const [domain, setDomain] = React.useState(tenant.custom_domain ?? "");

  const [fullName, setFullName] = React.useState(me.user.full_name);
  const [password, setPassword] = React.useState("");

  const saveBranding = useMutation({
    mutationFn: () =>
      api.patch<Tenant>("/settings", {
        branding: {
          ...tenant.branding,
          logo_text: logoText.trim(),
          support_email: supportEmail.trim(),
          primary_color: primary,
          accent_color: accent,
        },
      }),
    onSuccess: async () => {
      toast({ title: "Branding updated", variant: "success" });
      await refresh();
    },
    onError: (err) =>
      toast({ title: err instanceof ApiError ? err.message : "Could not save", variant: "error" }),
  });

  const saveWorkspace = useMutation({
    mutationFn: () =>
      api.patch<Tenant>("/settings", {
        name: name.trim(),
        custom_domain: canCustomDomain ? domain.trim() || null : undefined,
      }),
    onSuccess: async () => {
      toast({ title: "Workspace updated", variant: "success" });
      await refresh();
    },
    onError: (err) =>
      toast({
        title:
          err instanceof ApiError && err.isPlanGate
            ? "Custom domains require the Growth plan"
            : err instanceof ApiError
              ? err.message
              : "Could not save",
        variant: "error",
      }),
  });

  const saveProfile = useMutation({
    mutationFn: () =>
      api.patch<Member>(`/team/users/${me.user.id}`, {
        full_name: fullName.trim(),
        password: password ? password : undefined,
      }),
    onSuccess: async () => {
      toast({ title: "Profile updated", variant: "success" });
      setPassword("");
      await refresh();
    },
    onError: (err) =>
      toast({ title: err instanceof ApiError ? err.message : "Could not save", variant: "error" }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Branding, workspace details and your profile."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Palette className="h-4 w-4 text-brand-soft" />
              <CardTitle>Branding</CardTitle>
            </div>
            <CardDescription>
              Applied instantly across the console and on your login page.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="logo-text">Logo text</Label>
              <Input
                id="logo-text"
                value={logoText}
                onChange={(event) => setLogoText(event.target.value)}
                placeholder={tenant.name}
                maxLength={60}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="support-email">Support email</Label>
              <Input
                id="support-email"
                type="email"
                value={supportEmail}
                onChange={(event) => setSupportEmail(event.target.value)}
                placeholder="support@company.com"
                maxLength={255}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <ColorField label="Primary color" value={primary} onChange={setPrimary} />
              <ColorField label="Accent color" value={accent} onChange={setAccent} />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {PRESETS.map((preset) => {
                const active = preset.primary === primary && preset.accent === accent;
                return (
                  <button
                    key={preset.primary}
                    type="button"
                    aria-label={`Use palette ${preset.primary} and ${preset.accent}`}
                    aria-pressed={active}
                    onClick={() => {
                      setPrimary(preset.primary);
                      setAccent(preset.accent);
                    }}
                    className={cn(
                      "flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] transition-colors",
                      active ? "border-brand/60 bg-brand/10" : "border-border hover:bg-white/5",
                    )}
                  >
                    <span className="flex h-3 w-3 overflow-hidden rounded-full border border-white/20">
                      <span className="h-full w-1/2" style={{ background: preset.primary }} />
                      <span className="h-full w-1/2" style={{ background: preset.accent }} />
                    </span>
                    {active ? <Check className="h-3 w-3" /> : null}
                  </button>
                );
              })}
            </div>

            <div className="rounded-lg border border-border bg-white/[0.015] p-4">
              <p className="text-[11px] uppercase tracking-[0.08em] text-faint-foreground">Preview</p>
              <div className="mt-3 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-sm font-bold text-white"
                    style={{ background: HEX_RE.test(primary) ? primary : "#6d5efc" }}
                  >
                    {(logoText || tenant.name).charAt(0).toUpperCase()}
                  </span>
                  <span className="text-sm font-medium">{logoText || tenant.name}</span>
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: HEX_RE.test(accent) ? accent : "#22d3ee" }}
                  />
                </div>
                <span
                  className="rounded-lg px-3 py-1.5 text-xs font-medium text-white"
                  style={{ background: HEX_RE.test(primary) ? primary : "#6d5efc" }}
                >
                  Book now
                </span>
              </div>
            </div>

            <Button
              onClick={() => saveBranding.mutate()}
              disabled={saveBranding.isPending || !HEX_RE.test(primary) || !HEX_RE.test(accent)}
            >
              {saveBranding.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Save branding
            </Button>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Cog className="h-4 w-4 text-brand-soft" />
                <CardTitle>Workspace</CardTitle>
              </div>
              <CardDescription>
                {canEditWorkspace
                  ? "Name and domain for this workspace."
                  : "Only owners and admins can change workspace settings."}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="workspace-name">Workspace name</Label>
                <Input
                  id="workspace-name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  disabled={!canEditWorkspace}
                  minLength={2}
                  maxLength={120}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="workspace-domain">Custom domain</Label>
                <Input
                  id="workspace-domain"
                  value={canCustomDomain ? domain : ""}
                  onChange={(event) => setDomain(event.target.value)}
                  disabled={!canCustomDomain || !canEditWorkspace}
                  placeholder={canCustomDomain ? "bookings.yourrailway.com" : "Growth plan required"}
                />
                {!canCustomDomain ? (
                  <p className="flex items-center gap-1 text-[11px] text-muted-foreground">
                    <Lock className="h-3 w-3" /> Custom domains are available on the Growth plan.
                  </p>
                ) : null}
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border/70 px-3 py-2.5 text-xs">
                <span className="text-muted-foreground">Workspace slug</span>
                <span className="font-mono">{tenant.slug}</span>
              </div>
              <Button
                onClick={() => saveWorkspace.mutate()}
                disabled={!canEditWorkspace || saveWorkspace.isPending || name.trim().length < 2}
              >
                {saveWorkspace.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Save workspace
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <UserRound className="h-4 w-4 text-brand-soft" />
                <CardTitle>Your profile</CardTitle>
              </div>
              <CardDescription>Update your name or set a new password.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="profile-name">Full name</Label>
                <Input
                  id="profile-name"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  minLength={2}
                  maxLength={120}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="profile-password">New password</Label>
                <Input
                  id="profile-password"
                  type="password"
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Leave empty to keep current"
                  minLength={8}
                />
              </div>
              <Button
                onClick={() => saveProfile.mutate()}
                disabled={
                  !canEditWorkspace ||
                  saveProfile.isPending ||
                  fullName.trim().length < 2 ||
                  (password.length > 0 && password.length < 8)
                }
              >
                {saveProfile.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Save profile
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
