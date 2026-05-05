import { HTMLAttributes } from "react";
import clsx from "clsx";

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        "bg-[--color-surface] border border-[--color-border] rounded-[--radius-lg]",
        className,
      )}
      {...rest}
    />
  );
}
