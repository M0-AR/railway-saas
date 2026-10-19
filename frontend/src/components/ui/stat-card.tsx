import * as React from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  hint?: string;
  delta?: number | null;
  icon?: React.ReactNode;
  className?: string;
}

/* KPI surface: numbers are tabular so columns align and values don't jitter
   (docs §3, STD-visual-details-02). No entrance animation (docs §6 rule 12). */
export function StatCard({ label, value, hint, delta, icon, className }: StatCardProps) {
  const hasDelta = typeof delta === "number" && Number.isFinite(delta);
  const positive = hasDelta && (delta as number) >= 0;
  return (
    <div className={cn("rounded-lg border border-border bg-card p-4", className)}>
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-faint-foreground">{label}</p>
        {icon ? <span className="text-faint-foreground [&_svg]:h-4 [&_svg]:w-4">{icon}</span> : null}
      </div>
      <p className="mt-2 text-2xl font-semibold leading-none tracking-[-0.02em] tabular-nums">{value}</p>
      <div className="mt-2 flex items-center gap-2">
        {hasDelta ? (
          <span
            className={cn(
              "inline-flex items-center gap-0.5 text-[11px] font-medium tabular-nums",
              positive ? "text-success" : "text-danger",
            )}
          >
            {positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            {Math.abs(delta as number).toFixed(1)}%
          </span>
        ) : null}
        {hint ? <span className="text-xs text-muted-foreground">{hint}</span> : null}
      </div>
    </div>
  );
}
