import clsx from "clsx";

type Status = "live" | "idle" | "error" | "hot" | "warm" | "cold";

interface Props {
  status: Status;
  className?: string;
}

const colorClass: Record<Status, string> = {
  live: "bg-[var(--color-accent)]",
  idle: "bg-[var(--color-text-tertiary)]",
  error: "bg-[var(--color-hot)]",
  hot: "bg-[var(--color-hot)]",
  warm: "bg-[var(--color-warm)]",
  cold: "bg-[var(--color-cool)]",
};

export function StatusDot({ status, className }: Props) {
  const animate = status === "live" || status === "hot";
  return (
    <span
      className={clsx(
        "inline-block w-1.5 h-1.5 rounded-full",
        colorClass[status],
        animate && "animate-pulse-dot",
        className,
      )}
    />
  );
}
