// frontend/src/components/ui/Badge.tsx
import { HTMLAttributes, forwardRef } from "react";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "outline" | "success" | "warning" | "danger";
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ variant = "default", className = "", children, ...props }, ref) => {
    const variants = {
      default: "bg-blue-500/20 text-blue-400 border-blue-500/30",
      outline: "bg-slate-500/20 text-slate-400 border-slate-500/30",
      success: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
      warning: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
      danger: "bg-rose-500/20 text-rose-400 border-rose-500/30",
    };

    return (
      <span
        ref={ref}
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${variants[variant]} ${className}`}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = "Badge";