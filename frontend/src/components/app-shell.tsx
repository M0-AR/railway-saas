"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import {
  BarChart3,
  CreditCard,
  LayoutDashboard,
  LogOut,
  Menu,
  ScrollText,
  Search,
  Settings2,
  Ticket,
  TrainFront,
  Upload,
  UserPlus,
  Users,
  X,
} from "lucide-react";

import { CommandPalette, type CommandPaletteItem } from "@/components/command-palette";
import { useMe } from "@/components/require-auth";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { initials, titleCase } from "@/lib/format";
import { brandingStyle, logoTextOf } from "@/lib/tenant-branding";
import type { Role } from "@/lib/types";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  roles?: Role[];
}

const NAV: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: <LayoutDashboard /> },
  { href: "/bookings", label: "Bookings", icon: <Ticket /> },
  { href: "/trains", label: "Trains", icon: <TrainFront /> },
  { href: "/reports", label: "Reports", icon: <BarChart3 /> },
  { href: "/team", label: "Team", icon: <Users />, roles: ["owner", "admin"] },
  { href: "/audit", label: "Audit log", icon: <ScrollText />, roles: ["owner", "admin"] },
  { href: "/billing", label: "Billing", icon: <CreditCard />, roles: ["owner", "admin"] },
  { href: "/settings", label: "Settings", icon: <Settings2 />, roles: ["owner", "admin"] },
];

const MANAGE_ROLES: Role[] = ["owner", "admin"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { me, logout } = useMe();
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpenFor, setMobileOpenFor] = React.useState<string | null>(null);
  const [paletteOpen, setPaletteOpen] = React.useState(false);
  const mobileOpen = mobileOpenFor === pathname;

  const items = NAV.filter((item) => !item.roles || item.roles.includes(me.user.role));
  const logo = logoTextOf(me.tenant.name, me.tenant.branding);
  const canManage = MANAGE_ROLES.includes(me.user.role);
  const canImport = canManage && me.entitlements.features["csv.import"] === true;

  React.useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((value) => !value);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const paletteItems = React.useMemo<CommandPaletteItem[]>(() => {
    const navigate: CommandPaletteItem[] = items.map((item) => ({
      id: `nav:${item.href}`,
      label: item.label,
      group: "Navigate",
      icon: item.icon,
      keywords: item.href,
      onRun: () => router.push(item.href),
    }));
    const actions: CommandPaletteItem[] = [
      {
        id: "action:booking-create",
        label: "New booking",
        group: "Actions",
        icon: <Ticket />,
        keywords: "create sell ticket",
        onRun: () => router.push("/bookings?new=1"),
      },
      {
        id: "action:train-create",
        label: "New train",
        group: "Actions",
        icon: <TrainFront />,
        keywords: "create add service",
        onRun: () => router.push("/trains?new=1"),
      },
    ];
    if (canManage) {
      actions.push({
        id: "action:team-invite",
        label: "Invite teammate",
        group: "Actions",
        icon: <UserPlus />,
        keywords: "create user member",
        onRun: () => router.push("/team?new=1"),
      });
    }
    if (canImport) {
      actions.push({
        id: "action:trains-import",
        label: "Import trains from CSV",
        group: "Actions",
        icon: <Upload />,
        keywords: "upload csv bulk",
        onRun: () => router.push("/trains?import=1"),
      });
    }
    return [...navigate, ...actions];
  }, [items, router, canManage, canImport]);

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex h-16 shrink-0 items-center gap-2.5 px-5">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-sm font-bold text-white">
          R
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold leading-tight">{logo}</p>
          <p className="truncate text-[11px] text-faint-foreground">{me.tenant.slug}.railflow</p>
        </div>
      </div>

      <nav className="mt-2 flex-1 space-y-0.5 overflow-y-auto px-3">
        {items.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors [&_svg]:h-4 [&_svg]:w-4",
                active
                  ? "bg-surface-3 text-foreground"
                  : "text-muted-foreground hover:bg-white/[0.04] hover:text-foreground",
              )}
            >
              <span className={cn(active && "text-brand-soft")}>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-3">
        <Link
          href="/billing"
          className="flex items-center justify-between gap-2 rounded-lg border border-border bg-white/[0.02] px-3 py-2.5 transition-colors hover:bg-white/[0.06]"
        >
          <div className="min-w-0">
            <p className="text-[11px] uppercase tracking-[0.08em] text-faint-foreground">Current plan</p>
            <p className="truncate text-sm font-medium">
              {me.entitlements.plan_name ?? titleCase(me.tenant.plan_code)}
            </p>
          </div>
          <Badge variant="muted">{me.tenant.plan_code}</Badge>
        </Link>
      </div>
    </div>
  );

  return (
    <div style={brandingStyle(me.tenant.branding)} className="min-h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:border focus:border-border focus:bg-surface-2 focus:px-4 focus:py-2 focus:text-sm focus:text-foreground"
      >
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] border-r border-border bg-card lg:block">
        {sidebar}
      </aside>

      {/* Mobile drawer */}
      <DialogPrimitive.Root
        open={mobileOpen}
        onOpenChange={(open) => setMobileOpenFor(open ? pathname : null)}
      >
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="motion-overlay fixed inset-0 z-40 bg-black/60 lg:hidden" />
          <DialogPrimitive.Content className="motion-drawer fixed inset-y-0 left-0 z-50 w-[264px] border-r border-border bg-card outline-none lg:hidden">
            <DialogPrimitive.Title className="sr-only">Navigation</DialogPrimitive.Title>
            <DialogPrimitive.Close className="absolute right-3 top-4 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-foreground">
              <X className="h-4 w-4" />
              <span className="sr-only">Close navigation</span>
            </DialogPrimitive.Close>
            {sidebar}
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>

      <div className="lg:pl-[248px]">
        <header className="scroll-edge sticky top-0 z-20 flex h-16 items-center gap-3 bg-white/[0.06] px-4 backdrop-blur-[20px] backdrop-saturate-[1.8] sm:px-6">
          <button
            type="button"
            aria-label="Open navigation"
            onClick={() => setMobileOpenFor(pathname)}
            className="rounded-lg border border-border p-2 text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-foreground lg:hidden"
          >
            <Menu className="h-4 w-4" />
          </button>
          <span className="hidden text-xs text-faint-foreground sm:block">
            {new Intl.DateTimeFormat("en-US", {
              weekday: "long",
              month: "long",
              day: "numeric",
            }).format(new Date())}
          </span>

          <div className="ml-auto flex items-center gap-3">
            <button
              type="button"
              onClick={() => setPaletteOpen(true)}
              className="hidden h-9 w-64 items-center gap-2 rounded-lg border border-border bg-white/[0.03] px-3 text-sm text-faint-foreground transition-colors hover:bg-white/[0.06] md:flex"
            >
              <Search className="h-4 w-4 shrink-0" />
              <span className="flex-1 truncate text-left">Search or jump to…</span>
              <kbd className="rounded border border-border px-1.5 py-0.5 font-sans text-[10px] font-medium tabular-nums">
                ⌘K
              </kbd>
            </button>
            <button
              type="button"
              aria-label="Search"
              onClick={() => setPaletteOpen(true)}
              className="rounded-lg border border-border p-2 text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-foreground md:hidden"
            >
              <Search className="h-4 w-4" />
            </button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="flex items-center gap-2.5 rounded-lg border border-border bg-white/[0.03] py-1 pl-1 pr-2.5 transition-colors hover:bg-white/[0.06]"
                >
                  <span className="flex h-8 w-8 items-center justify-center rounded-md bg-brand/15 text-xs font-semibold text-brand-soft">
                    {initials(me.user.full_name)}
                  </span>
                  <span className="hidden text-left sm:block">
                    <span className="block text-xs font-medium leading-tight">{me.user.full_name}</span>
                    <span className="block text-[11px] leading-tight text-faint-foreground">
                      {titleCase(me.user.role)}
                    </span>
                  </span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <span className="block truncate text-xs text-foreground">{me.user.email}</span>
                  <span className="block truncate text-[11px]">{me.tenant.name}</span>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/settings">
                    <Settings2 className="h-4 w-4" /> Workspace settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={logout} className="text-danger focus:text-danger">
                  <LogOut className="h-4 w-4" /> Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-6xl px-4 py-6 outline-none sm:px-6">{children}</main>
      </div>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} items={paletteItems} />
    </div>
  );
}
