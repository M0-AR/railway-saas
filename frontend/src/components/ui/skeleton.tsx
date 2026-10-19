import { cn } from "@/lib/utils";

/* Skeleton geometry matches the content it stands in for; 1.5s pulse,
   static under reduced motion (docs §7). */
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-skeleton rounded-md bg-white/[0.06]", className)} {...props} />;
}

export { Skeleton };
