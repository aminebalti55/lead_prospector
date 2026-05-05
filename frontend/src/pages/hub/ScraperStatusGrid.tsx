import { Card } from "../../design/primitives";
import { usePulseStatus } from "../../api/hub";
import { ScraperStatusCard } from "./ScraperStatusCard";

export function ScraperStatusGrid() {
  const { data, isLoading } = usePulseStatus();
  const sources = data?.sources ?? [];

  return (
    <Card className="p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
          Scraper status
        </span>
        <span className="text-[11px] text-[var(--color-text-tertiary)]">
          {sources.length} sources
        </span>
      </div>

      {isLoading && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">Loading…</div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
        {sources.map((s) => (
          <ScraperStatusCard key={s.source} src={s} />
        ))}
      </div>
    </Card>
  );
}
