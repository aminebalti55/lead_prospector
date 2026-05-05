import { HTMLAttributes } from "react";
import clsx from "clsx";

export function KbdHint({ className, children, ...rest }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <kbd
      className={clsx(
        "inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-mono",
        "bg-[var(--color-surface-raised)] text-[var(--color-text-tertiary)]",
        "border border-[var(--color-border)] rounded-[4px]",
        className,
      )}
      {...rest}
    >
      {children}
    </kbd>
  );
}
