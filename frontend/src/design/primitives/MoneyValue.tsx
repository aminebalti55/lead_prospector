import clsx from "clsx";

interface Props {
  usd: number;
  size?: "sm" | "md" | "lg" | "xl";
  tone?: "default" | "accent" | "muted";
  abbreviate?: boolean;
  className?: string;
}

const sizeClass: Record<NonNullable<Props["size"]>, string> = {
  sm: "text-xs",
  md: "text-sm",
  lg: "text-lg",
  xl: "text-3xl",
};

const toneClass: Record<NonNullable<Props["tone"]>, string> = {
  default: "text-[--color-text-primary]",
  accent: "text-[--color-accent]",
  muted: "text-[--color-text-secondary]",
};

function format(usd: number, abbreviate: boolean): string {
  if (abbreviate && usd >= 10_000) {
    return `$${(usd / 1000).toFixed(usd >= 100_000 ? 0 : 1)}K`;
  }
  return `$${usd.toLocaleString("en-US")}`;
}

export function MoneyValue({
  usd,
  size = "md",
  tone = "default",
  abbreviate = false,
  className,
}: Props) {
  return (
    <span
      className={clsx(
        "font-mono tabular-nums font-medium",
        sizeClass[size],
        toneClass[tone],
        className,
      )}
    >
      {format(usd, abbreviate)}
    </span>
  );
}
