import { HTMLAttributes } from "react";
import clsx from "clsx";

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        "bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)]",
        className,
      )}
      {...rest}
    />
  );
}
