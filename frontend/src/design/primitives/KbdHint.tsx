import { HTMLAttributes } from "react";
import clsx from "clsx";

export function KbdHint({ className, children, ...rest }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <kbd
      className={clsx(
        "inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-mono",
        "bg-[--color-surface-raised] text-[--color-text-tertiary]",
        "border border-[--color-border] rounded-[4px]",
        className,
      )}
      {...rest}
    >
      {children}
    </kbd>
  );
}
