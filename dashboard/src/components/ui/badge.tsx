import * as React from "react";
import { cn } from "../../lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variantClasses = {
    default: "border-transparent bg-primary text-white shadow hover:bg-primary/80",
    secondary: "border-transparent bg-surface-border text-gray-200 hover:bg-surface-hover",
    destructive: "border-transparent bg-red-500/15 text-red-400 border border-red-500/30 hover:bg-red-500/25",
    outline: "border-surface-border text-gray-300",
    success: "border-emerald-500/30 bg-emerald-500/15 text-emerald-400 border hover:bg-emerald-500/25",
    warning: "border-amber-500/30 bg-amber-500/15 text-amber-300 border hover:bg-amber-500/25",
  }[variant];

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold font-mono transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
        variantClasses,
        className
      )}
      {...props}
    />
  );
}

export { Badge };
