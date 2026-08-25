// frontend/src/components/ui/Button.tsx
import { ButtonHTMLAttributes, ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "success" | "danger";
  children: ReactNode;
  className?: string;
}

export function Button({ 
  variant = "primary", 
  children, 
  className = "", 
  ...props 
}: ButtonProps) {
  
  // These styles apply to ALL buttons (padding, rounded corners, transitions)
  const baseStyles = "px-6 py-4 rounded-xl font-bold transition-all flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed";
  
  // These styles change based on the 'variant' prop you pass
  const variants = {
    primary: "bg-blue-600 hover:bg-blue-700 text-white shadow-sm",
    secondary: "bg-slate-800 hover:bg-slate-700 border border-slate-600 text-white",
    success: "bg-green-600 hover:bg-green-700 text-white shadow-sm",
    danger: "bg-red-600 hover:bg-red-700 text-white shadow-sm"
  };

  return (
    <button className={`${baseStyles} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}