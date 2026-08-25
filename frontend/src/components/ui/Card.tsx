// frontend/src/components/ui/Card.tsx
import { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string; // Allows us to pass extra classes if needed
}

export function Card({ children, className = "" }: CardProps) {
  return (
    <div className={`bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg transition-all ${className}`}>
      {children}
    </div>
  );
}