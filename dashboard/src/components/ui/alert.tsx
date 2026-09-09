import * as React from "react";
import { cn } from "../../lib/utils";

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "destructive" | "info" | "success" | "warning";
}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = "default", ...props }, ref) => {
    const variantClasses = {
      default: "bg-surface border-surface-border text-gray-200",
      destructive:
        "bg-red-500/10 border-red-500/30 text-red-300 [&>svg]:text-red-400",
      info: "bg-primary/10 border-primary/30 text-primary-light [&>svg]:text-primary",
      success:
        "bg-emerald-500/10 border-emerald-500/30 text-emerald-300 [&>svg]:text-emerald-400",
      warning:
        "bg-amber-500/10 border-amber-500/30 text-amber-300 [&>svg]:text-amber-400",
    }[variant];

    return (
      <div
        ref={ref}
        role="alert"
        className={cn(
          "relative w-full rounded-xl border p-4 text-xs flex items-start gap-3",
          variantClasses,
          className
        )}
        {...props}
      />
    );
  }
);
Alert.displayName = "Alert";

const AlertTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h5
    ref={ref}
    className={cn("font-semibold leading-none tracking-tight text-white", className)}
    {...props}
  />
));
AlertTitle.displayName = "AlertTitle";

const AlertDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-xs text-gray-300 [&_p]:leading-relaxed", className)}
    {...props}
  />
));
AlertDescription.displayName = "AlertDescription";

export { Alert, AlertTitle, AlertDescription };
