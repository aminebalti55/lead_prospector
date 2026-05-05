import clsx from "clsx";
import { Opportunity } from "../../types/opportunity";
import { StatusDot, Pill, MoneyValue } from "../../design/primitives";

interface Props {
  opp: Opportunity;
  active: boolean;
  onClick: () => void;
}

function formatAge(iso: string | null): string {
  if (!iso) return "";
  const ms = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

export function OpportunityListItem({ opp, active, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "w-full text-left px-3 py-2.5 border-b border-[var(--color-border)]",
        "transition-colors flex flex-col gap-1.5",
        active
          ? "bg-[var(--color-surface-raised)]"
          : "hover:bg-[var(--color-surface)]",
      )}
    >
      <div className="flex items-center gap-2 min-w-0">
        <StatusDot status={opp.priority === "hot" ? "hot" : opp.priority === "warm" ? "warm" : "cold"} />
        <span className="text-[13px] font-medium text-[var(--color-text-primary)] truncate flex-1">
          {opp.title || "(no title)"}
        </span>
        <MoneyValue
          usd={opp.estimated_value_usd}
          size="sm"
          tone="accent"
        />
      </div>
      <div className="flex items-center gap-1.5 text-[11px] text-[var(--color-text-tertiary)]">
        <Pill tone="neutral">{opp.source}</Pill>
        {opp.location && <span className="truncate">{opp.location}</span>}
        <span className="ml-auto tabular-nums">{formatAge(opp.posted_date)}</span>
      </div>
    </button>
  );
}
