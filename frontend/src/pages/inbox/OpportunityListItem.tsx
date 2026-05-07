import clsx from "clsx";
import {
  Check, Mail, MailX,
  CheckCircle2, MessageSquare, CalendarCheck, Trophy,
  Eye, X as XIcon,
} from "lucide-react";
import { Opportunity, Stage } from "../../types/opportunity";
import { StatusDot, Pill, MoneyValue } from "../../design/primitives";

interface Props {
  opp: Opportunity;
  active: boolean;
  selected: boolean;
  onClick: () => void;
  onToggleSelect: (e: React.MouseEvent) => void;
}

/** Stage labels are different for direct (jobs) vs cold (prospects). For
 * direct, "contacted" reads as "Applied" — that's the verb the user actually
 * performed. */
function rowStageLabel(stage: Stage, type: "direct" | "cold"): string {
  if (type === "direct") {
    return {
      researching: "Viewing",
      contacted: "Applied",
      replied: "Heard back",
      meeting: "Interview",
      won: "Hired",
      lost: "Rejected",
      new: "",
    }[stage];
  }
  return {
    researching: "Researching",
    contacted: "Contacted",
    replied: "Replied",
    meeting: "Meeting",
    won: "Won",
    lost: "Passed",
    new: "",
  }[stage];
}

function rowStageIcon(stage: Stage) {
  switch (stage) {
    case "researching": return <Eye className="w-2.5 h-2.5" />;
    case "contacted": return <CheckCircle2 className="w-2.5 h-2.5" />;
    case "replied": return <MessageSquare className="w-2.5 h-2.5" />;
    case "meeting": return <CalendarCheck className="w-2.5 h-2.5" />;
    case "won": return <Trophy className="w-2.5 h-2.5" />;
    case "lost": return <XIcon className="w-2.5 h-2.5" />;
    default: return null;
  }
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
  // 'lost' is dimmed but with a visible red badge so the user knows they
  // already passed. Active progressing stages are highlighted in volt-green.
  const isLost = opp.stage === "lost";
  const isProgressing = ["contacted", "replied", "meeting", "won"].includes(opp.stage);
  const isResearching = opp.stage === "researching";

  const stageLabel = rowStageLabel(opp.stage as Stage, opp.type);

  return (
    <div
      className={clsx(
        "w-full px-3 py-2.5 border-b border-[var(--color-border)]",
        "transition-colors flex items-start gap-2",
        active
          ? "bg-[var(--color-surface-raised)]"
          : "hover:bg-[var(--color-surface)]",
        isLost && "opacity-50",
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
        className="flex-1 text-left flex flex-col gap-1.5 min-w-0"
      >
        <div className="flex items-center gap-2 min-w-0">
          <StatusDot status={opp.priority === "hot" ? "hot" : opp.priority === "warm" ? "warm" : "cold"} />
          <span className={clsx(
            "text-[13px] font-medium truncate flex-1",
            isLost ? "text-[var(--color-text-tertiary)] line-through" : "text-[var(--color-text-primary)]",
          )}>
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
          {stageLabel && (
            <span
              className={clsx(
                "flex items-center gap-1 px-1.5 py-0.5 rounded-[var(--radius-xs)] text-[10px] font-medium uppercase tracking-wider shrink-0",
                isProgressing && "bg-[var(--color-accent)]/15 text-[var(--color-accent)]",
                isResearching && "bg-[var(--color-warm)]/15 text-[var(--color-warm)]",
                isLost && "bg-[var(--color-hot)]/15 text-[var(--color-hot)]",
              )}
            >
              {rowStageIcon(opp.stage as Stage)} {stageLabel}
            </span>
          )}
          <span className="ml-auto tabular-nums">{formatAge(opp.posted_date)}</span>
        </div>
      </button>
    </div>
  );
}
