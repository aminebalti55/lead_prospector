import { ButtonHTMLAttributes, forwardRef } from "react";
import clsx from "clsx";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const variantClass: Record<Variant, string> = {
  primary:
    "bg-[var(--color-accent)] text-[#0A0A0B] hover:bg-[var(--color-accent-hover)] font-medium",
  secondary:
    "bg-[var(--color-surface-raised)] text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)]",
  ghost:
    "bg-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-raised)] hover:text-[var(--color-text-primary)]",
  danger:
    "bg-[var(--color-hot-soft)] text-[var(--color-hot)] hover:bg-[var(--color-hot)] hover:text-white",
};

const sizeClass: Record<Size, string> = {
  sm: "h-7 px-2.5 text-xs rounded-[var(--radius-sm)]",
  md: "h-9 px-3.5 text-sm rounded-[var(--radius-md)]",
  lg: "h-11 px-5 text-sm rounded-[var(--radius-md)]",
};

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ variant = "secondary", size = "md", className, ...rest }, ref) => (
    <button
      ref={ref}
      className={clsx(
        "inline-flex items-center justify-center gap-1.5 transition-colors duration-150 disabled:opacity-50 disabled:pointer-events-none",
        variantClass[variant],
        sizeClass[size],
        className,
      )}
      {...rest}
    />
  ),
);
Button.displayName = "Button";
