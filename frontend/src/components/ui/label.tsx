"use client";

import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";

import { cn } from "@/lib/utils";

/* Sentence case in product copy; uppercase only for these micro labels, which
   carry slightly looser tracking (docs §3, STD-visual-details-04/05). */
const Label = React.forwardRef<
  React.ComponentRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn("text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground", className)}
    {...props}
  />
));
Label.displayName = "Label";

export { Label };
