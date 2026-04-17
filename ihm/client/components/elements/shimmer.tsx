import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type ShimmerProps = HTMLAttributes<HTMLDivElement>;

export function Shimmer({ className, ...props }: ShimmerProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-full bg-muted/60",
        "before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_1.4s_ease-in-out_infinite]",
        "before:bg-gradient-to-r before:from-transparent before:via-foreground/30 before:to-transparent",
        className
      )}
      {...props}
    />
  );
}
