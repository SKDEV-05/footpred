import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "success" | "warning" | "danger" | "info";
}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = "default", ...props }, ref) => {
    const variants = {
      default: "bg-zinc-800 text-zinc-300 border-zinc-700",
      success: "bg-green-500/20 text-green-400 border-green-500/30",
      warning: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
      danger: "bg-red-500/20 text-red-400 border-red-500/30",
      info: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    };

    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border",
          variants[variant],
          className
        )}
        {...props}
      />
    );
  }
);
Badge.displayName = "Badge";

export { Badge };