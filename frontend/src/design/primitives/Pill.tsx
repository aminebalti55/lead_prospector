import { HTMLAttributes } from "react";
import clsx from "clsx";

type Tone = "neutral" | "hot" | "warm" | "cool" | "accent";

interface Props extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

const toneClass: Record<Tone, string> = {
  neutral:
    "bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] border border-[var(--color-border)]",
  hot: "bg-[var(--color-hot-soft)] text-[var(--color-hot)]",
  warm: "bg-[var(--color-warm-soft)] text-[var(--color-warm)]",
  cool: "bg-[var(--color-cool-soft)] text-[var(--color-cool)]",
  accent: "bg-[var(--color-accent-soft)] text-[var(--color-accent)]",
};

export function Pill({ tone = "neutral", className, ...rest }: Props) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 text-[11px] font-medium rounded-[var(--radius-sm)] tabular-nums",
        toneClass[tone],
        className,
      )}
      {...rest}
    />
  );
}
