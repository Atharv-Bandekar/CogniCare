// frontend/src/components/ui/Input.tsx
import { InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = "", ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-slate-300 mb-1">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`w-full px-4 py-3 bg-slate-800 border rounded-lg text-slate-100 placeholder-slate-500
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
            disabled:bg-slate-700 disabled:text-slate-500
            ${error ? "border-rose-500" : "border-slate-600 hover:border-slate-500"}
            ${className}`}
          {...props}
        />
        {error && <p className="mt-1 text-sm text-rose-400">{error}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";