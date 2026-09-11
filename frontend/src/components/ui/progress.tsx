"use client";

import * as Progress from "@radix-ui/react-progress";
import * as React from "react";

import { cn } from "@/lib/utils";

export function ProgressRoot({
  className,
  value,
  max = 100,
  ...props
}: React.ComponentPropsWithoutRef<typeof Progress.Root>) {
  return (
    <Progress.Root
      value={value}
      max={max}
      className={cn(
        "relative h-2 w-full overflow-hidden rounded-full bg-primary/20",
        className,
      )}
      {...props}
    />
  );
}

export function ProgressIndicator({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof Progress.Indicator>) {
  return (
    <Progress.Indicator
      className={cn(
        "h-full w-full flex-1 rounded-full bg-primary transition-all",
        className,
      )}
      {...props}
    />
  );
}

export { Progress as ProgressPrimitive };