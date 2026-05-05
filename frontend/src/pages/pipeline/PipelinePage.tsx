import { useState } from "react";
import { useOpportunities } from "../../api/opportunities";
import type { OpportunityFilters } from "../../types/opportunity";
import { PipelineToolbar } from "./PipelineToolbar";
import { PipelineBoard } from "./PipelineBoard";

export function PipelinePage() {
  const [filters, setFilters] = useState<OpportunityFilters>({ sort: "score", limit: 500 });
  const { data, isLoading } = useOpportunities(filters);
  const opps = data?.opportunities ?? [];

  return (
    <div className="p-6 flex flex-col h-full max-w-full overflow-hidden">
      <PipelineToolbar value={filters} onChange={setFilters} totalCount={data?.total ?? 0} />

      {isLoading && (
        <div className="flex-1 flex items-center justify-center text-[12px] text-[var(--color-text-tertiary)]">
          Loading…
        </div>
      )}

      {!isLoading && opps.length === 0 && (
        <div className="flex-1 flex items-center justify-center text-[12px] text-[var(--color-text-tertiary)]">
          No opportunities match. Run a scan or clear your filters.
        </div>
      )}

      {!isLoading && opps.length > 0 && (
        <div className="flex-1 overflow-x-auto">
          <PipelineBoard opps={opps} />
        </div>
      )}
    </div>
  );
}
