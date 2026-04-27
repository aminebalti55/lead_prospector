import { cn } from "../lib/cn";
import { type ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
}

export function Button({ variant = "primary", size = "md", className, children, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-semibold transition-all duration-150 cursor-pointer",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        size === "sm" ? "px-3 py-1.5 text-[13px]" : "px-4 py-2 text-sm",
        variant === "primary" && "bg-primary text-white hover:bg-primary-hover shadow-sm hover:shadow-md active:scale-[0.98]",
        variant === "secondary" && "bg-surface text-text-primary border border-border hover:bg-bg hover:border-border-strong shadow-sm",
        variant === "ghost" && "text-text-secondary hover:text-text-primary hover:bg-bg",
        variant === "danger" && "bg-hot text-white hover:bg-red-700 shadow-sm",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
