import * as React from "react";

import { cn } from "@/lib/utils";

interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

/* Empty states teach: icon, one-line explanation, one action (docs §7). */
export function EmptyState({ icon, title, description, action, className, ...props }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-lg border border-border bg-white/[0.015] px-6 py-12 text-center",
        className,
      )}
      {...props}
    >
      {icon ? (
        <div className="mb-1 flex h-10 w-10 items-center justify-center rounded-lg bg-white/[0.05] text-muted-foreground [&_svg]:h-5 [&_svg]:w-5">
          {icon}
        </div>
      ) : null}
      <p className="text-sm font-medium">{title}</p>
      {description ? <p className="max-w-sm text-xs leading-relaxed text-muted-foreground">{description}</p> : null}
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}
