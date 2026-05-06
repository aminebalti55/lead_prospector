import clsx from "clsx";
import { Check, Mail, MailX, CheckCircle2 } from "lucide-react";
import { Opportunity } from "../../types/opportunity";
import { StatusDot, Pill, MoneyValue } from "../../design/primitives";

const POST_NEW_STAGES = new Set(["contacted", "replied", "meeting", "won", "lost"]);

interface Props {
  opp: Opportunity;
  active: boolean;
  selected: boolean;
  onClick: () => void;
  onToggleSelect: (e: React.MouseEvent) => void;
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

export function OpportunityListItem({ opp, active, selected, onClick, onToggleSelect }: Props) {
  const hasEmail = !!(opp.contact_email && opp.contact_email.includes("@"));
  const alreadyTouched = POST_NEW_STAGES.has(opp.stage);
  return (
    <div
      className={clsx(
        "w-full px-3 py-2.5 border-b border-[var(--color-border)]",
        "transition-colors flex items-start gap-2",
        active
          ? "bg-[var(--color-surface-raised)]"
          : "hover:bg-[var(--color-surface)]",
      )}
    >
      <button
        type="button"
        onClick={onToggleSelect}
        aria-label={selected ? "Deselect" : "Select"}
        className={clsx(
          "mt-1 w-4 h-4 rounded-[3px] border shrink-0 flex items-center justify-center transition-colors",
          selected
            ? "bg-[var(--color-accent)] border-[var(--color-accent)]"
            : "border-[var(--color-border)] hover:border-[var(--color-text-tertiary)]",
        )}
      >
        {selected && <Check className="w-3 h-3 text-[#0A0A0B]" />}
      </button>

      <button
        type="button"
        onClick={onClick}
        className={clsx(
          "flex-1 text-left flex flex-col gap-1.5 min-w-0",
          alreadyTouched && "opacity-60",
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          <StatusDot status={opp.priority === "hot" ? "hot" : opp.priority === "warm" ? "warm" : "cold"} />
          <span className="text-[13px] font-medium text-[var(--color-text-primary)] truncate flex-1">
            {opp.title || "(no title)"}
          </span>
          <MoneyValue usd={opp.estimated_value_usd} size="sm" tone="accent" />
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-[var(--color-text-tertiary)]">
          <Pill tone="neutral">{opp.source}</Pill>
          {opp.location && <span className="truncate">{opp.location}</span>}
          {hasEmail ? (
            <Mail className="w-3 h-3 text-[var(--color-accent)] shrink-0" aria-label="Has email" />
          ) : (
            <MailX className="w-3 h-3 text-[var(--color-text-tertiary)] shrink-0" aria-label="No email" />
          )}
          {alreadyTouched && (
            <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-[var(--radius-xs)] bg-[var(--color-accent)]/15 text-[var(--color-accent)] text-[10px] font-medium uppercase tracking-wider">
              <CheckCircle2 className="w-2.5 h-2.5" /> {opp.stage}
            </span>
          )}
          <span className="ml-auto tabular-nums">{formatAge(opp.posted_date)}</span>
        </div>
      </button>
    </div>
  );
}
