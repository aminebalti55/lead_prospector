import { useNavigate } from "react-router-dom";
import { MapPin } from "lucide-react";
import { MoneyValue, Pill, StatusDot } from "../../design/primitives";
import type { Opportunity } from "../../types/opportunity";

interface Props {
  opp: Opportunity;
  isDragging?: boolean;
}

export function PipelineCard({ opp, isDragging = false }: Props) {
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate(`/inbox?opp=${opp.id}`)}
      className={
        "p-2.5 rounded-[var(--radius-md)] border bg-[var(--color-surface)] cursor-grab active:cursor-grabbing flex flex-col gap-1.5 transition-shadow " +
        (isDragging
          ? "border-[var(--color-accent)] shadow-[0_4px_12px_rgba(0,0,0,0.4)]"
          : "border-[var(--color-border)] hover:border-[var(--color-border-strong)]")
      }
    >
      <div className="flex items-center gap-1.5 min-w-0">
        <MoneyValue usd={opp.estimated_value_usd} size="md" tone="accent" />
        <span className="ml-auto">
          <StatusDot
            status={
              opp.priority === "hot"
                ? "hot"
                : opp.priority === "warm"
                ? "warm"
                : "cold"
            }
          />
        </span>
      </div>
      <div className="text-[12px] text-[var(--color-text-primary)] leading-snug line-clamp-2">
        {opp.title || "(no title)"}
      </div>
      <div className="flex items-center gap-1.5 text-[10px] text-[var(--color-text-tertiary)]">
        <Pill tone="neutral">{opp.source}</Pill>
        {opp.location && (
          <span className="flex items-center gap-0.5 truncate">
            <MapPin className="w-2.5 h-2.5" /> {opp.location}
          </span>
        )}
      </div>
    </div>
  );
}
