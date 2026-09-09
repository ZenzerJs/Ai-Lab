import * as React from "react";
import { cn } from "../../lib/utils";

interface ToggleGroupContextValue {
  value: string;
  onValueChange: (val: string) => void;
}

const ToggleGroupContext = React.createContext<ToggleGroupContextValue | null>(null);

export interface ToggleGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
  onValueChange: (val: string) => void;
}

const ToggleGroup = React.forwardRef<HTMLDivElement, ToggleGroupProps>(
  ({ className, value, onValueChange, children, ...props }, ref) => {
    return (
      <ToggleGroupContext.Provider value={{ value, onValueChange }}>
        <div
          ref={ref}
          role="radiogroup"
          className={cn(
            "inline-flex items-center gap-1 rounded-lg border border-surface-border bg-background/80 p-1 select-none",
            className
          )}
          {...props}
        >
          {children}
        </div>
      </ToggleGroupContext.Provider>
    );
  }
);
ToggleGroup.displayName = "ToggleGroup";

export interface ToggleGroupItemProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
}

const ToggleGroupItem = React.forwardRef<HTMLButtonElement, ToggleGroupItemProps>(
  ({ className, value, children, ...props }, ref) => {
    const ctx = React.useContext(ToggleGroupContext);
    const isSelected = ctx?.value === value;

    return (
      <button
        ref={ref}
        type="button"
        role="radio"
        aria-checked={isSelected}
        onClick={() => ctx?.onValueChange(value)}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium font-mono transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary disabled:pointer-events-none disabled:opacity-50",
          isSelected
            ? "bg-primary text-white shadow-sm font-semibold"
            : "text-gray-400 hover:bg-surface-hover hover:text-white",
          className
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);
ToggleGroupItem.displayName = "ToggleGroupItem";

export { ToggleGroup, ToggleGroupItem };
