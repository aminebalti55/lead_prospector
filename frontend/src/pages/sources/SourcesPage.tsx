import { useSources } from "../../api/sources";
import { Card } from "../../design/primitives";
import { SourceCard } from "./SourceCard";
import { SavedSearchesList } from "./SavedSearchesList";

export function SourcesPage() {
  const { data, isLoading } = useSources();
  const sources = data?.sources ?? [];

  return (
    <div className="p-6 flex flex-col gap-4 max-w-[1400px] mx-auto w-full">
      <Card className="p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
              Sources
            </div>
            <div className="text-[11px] text-[var(--color-text-tertiary)]">
              {sources.length} sources · click Run Now to scan with the last keywords used
            </div>
          </div>
        </div>

        {isLoading && (
          <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">Loading…</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {sources.map((s) => (
            <SourceCard key={s.source} src={s} />
          ))}
        </div>
      </Card>

      <SavedSearchesList />
    </div>
  );
}
