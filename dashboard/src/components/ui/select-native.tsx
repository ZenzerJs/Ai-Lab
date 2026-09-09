import * as React from "react";
import { cn } from "../../lib/utils";

export interface SelectNativeProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {}

const SelectNative = React.forwardRef<HTMLSelectElement, SelectNativeProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={cn(
          "h-8 rounded-md border border-surface-border bg-background px-2.5 py-1 text-xs text-gray-200 transition-colors focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50 font-mono select-none",
          className
        )}
        {...props}
      >
        {children}
      </select>
    );
  }
);
SelectNative.displayName = "SelectNative";

export { SelectNative };
