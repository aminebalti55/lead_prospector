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
    "bg-[--color-accent] text-[#0A0A0B] hover:bg-[--color-accent-hover] font-medium",
  secondary:
    "bg-[--color-surface-raised] text-[--color-text-primary] hover:bg-[--color-surface-hover] border border-[--color-border]",
  ghost:
    "bg-transparent text-[--color-text-secondary] hover:bg-[--color-surface-raised] hover:text-[--color-text-primary]",
  danger:
    "bg-[--color-hot-soft] text-[--color-hot] hover:bg-[--color-hot] hover:text-white",
};

const sizeClass: Record<Size, string> = {
  sm: "h-7 px-2.5 text-xs rounded-[--radius-sm]",
  md: "h-9 px-3.5 text-sm rounded-[--radius-md]",
  lg: "h-11 px-5 text-sm rounded-[--radius-md]",
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
