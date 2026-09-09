import * as React from "react";
import { cn } from "../../lib/utils";

export interface ButtonVariantProps {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
}

export function buttonVariants({
  variant = "default",
  size = "default",
  className,
}: ButtonVariantProps & { className?: string } = {}) {
  const variantClasses = {
    default: "bg-primary text-white shadow hover:bg-primary/90",
    destructive:
      "bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 shadow-sm",
    outline:
      "border border-surface-border bg-surface-hover/50 text-gray-200 shadow-sm hover:bg-surface-hover hover:text-white",
    secondary:
      "bg-surface-border text-gray-100 shadow-sm hover:bg-surface-hover",
    ghost: "text-gray-400 hover:bg-surface-hover hover:text-white",
    link: "text-primary underline-offset-4 hover:underline",
  }[variant];

  const sizeClasses = {
    default: "h-9 px-4 py-2 text-sm",
    sm: "h-8 rounded-md px-3 text-xs",
    lg: "h-10 rounded-md px-6 text-sm font-semibold",
    icon: "size-8 p-0",
  }[size];

  return cn(
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary disabled:pointer-events-none disabled:opacity-50 select-none",
    variantClasses,
    sizeClasses,
    className
  );
}

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    ButtonVariantProps {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={buttonVariants({ variant, size, className })}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
