import { HTMLAttributes } from "react";
import clsx from "clsx";

type Tone = "neutral" | "hot" | "warm" | "cool" | "accent";

interface Props extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

const toneClass: Record<Tone, string> = {
  neutral:
    "bg-[--color-surface-raised] text-[--color-text-secondary] border border-[--color-border]",
  hot: "bg-[--color-hot-soft] text-[--color-hot]",
  warm: "bg-[--color-warm-soft] text-[--color-warm]",
  cool: "bg-[--color-cool-soft] text-[--color-cool]",
  accent: "bg-[--color-accent-soft] text-[--color-accent]",
};

export function Pill({ tone = "neutral", className, ...rest }: Props) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 text-[11px] font-medium rounded-[--radius-sm] tabular-nums",
        toneClass[tone],
        className,
      )}
      {...rest}
    />
  );
}
