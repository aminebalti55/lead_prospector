import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useOpportunities } from "../../api/opportunities";
import { Card, MoneyValue, Pill, StatusDot } from "../../design/primitives";

export function HottestOpps() {
  const navigate = useNavigate();
  const { data, isLoading } = useOpportunities({
    sort: "score",
    priority: "hot",
    limit: 5,
  });
  const items = data?.opportunities ?? [];

  return (
    <Card className="p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
          Today's hottest opps
        </span>
        <button
          type="button"
          onClick={() => navigate("/inbox")}
          className="text-[11px] text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] flex items-center gap-1 transition-colors"
        >
          View all <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      {isLoading && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">Loading…</div>
      )}

      {!isLoading && items.length === 0 && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">
          No hot opportunities yet. Run a scan to catch some.
        </div>
      )}

      <div className="flex flex-col">
        {items.map((opp) => (
          <button
            key={opp.id}
            type="button"
            onClick={() => navigate("/inbox")}
            className="flex items-center gap-2 py-1.5 text-left hover:bg-[var(--color-surface-raised)] rounded-[var(--radius-sm)] px-1 -mx-1 transition-colors"
          >
            <StatusDot status="hot" />
            <span className="text-[13px] text-[var(--color-text-primary)] truncate flex-1">
              {opp.title || "(no title)"}
            </span>
            <Pill tone="neutral">{opp.source}</Pill>
            <MoneyValue usd={opp.estimated_value_usd} size="sm" tone="accent" />
          </button>
        ))}
      </div>
    </Card>
  );
}
