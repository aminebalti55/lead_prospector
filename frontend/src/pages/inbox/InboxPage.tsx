import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useOpportunities } from "../../api/opportunities";
import type { OpportunityFilters, Priority, OpportunityType } from "../../types/opportunity";
import { FilterPanel } from "./FilterPanel";
import { OpportunityList } from "./OpportunityList";
import { OpportunityDetail } from "./OpportunityDetail";

export function InboxPage() {
  const [filters, setFilters] = useState<OpportunityFilters>({ sort: "score", limit: 200 });
  const [searchParams] = useSearchParams();
  const oppFromUrl = searchParams.get("opp");
  const [selectedId, setSelectedId] = useState<string | null>(oppFromUrl);

  // Server query — has_email and hide_contacted are filtered client-side so
  // the totals panel still reflects the unfiltered counts.
  const { data, isLoading } = useOpportunities({
    ...filters,
    has_email: undefined,
    hide_contacted: undefined,
  });
  const POST_NEW = new Set(["contacted", "replied", "meeting", "won", "lost"]);
  const items = useMemo(() => {
    let list = data?.opportunities ?? [];
    if (filters.has_email) {
      list = list.filter((o) => o.contact_email && o.contact_email.includes("@"));
    }
    if (filters.hide_contacted) {
      list = list.filter((o) => !POST_NEW.has(o.stage));
    }
    return list;
  }, [data?.opportunities, filters.has_email, filters.hide_contacted]);
  const selected = items.find((o) => o.id === selectedId) ?? items[0] ?? null;

  // If URL ?opp= param changes, prefer it over current selection
  useEffect(() => {
    if (oppFromUrl && oppFromUrl !== selectedId) setSelectedId(oppFromUrl);
  }, [oppFromUrl, selectedId]);

  // Auto-select first item when list changes and nothing is selected
  useEffect(() => {
    if (!selectedId && items.length > 0) setSelectedId(items[0].id);
  }, [items, selectedId]);

  // Compute counts for the filter panel against the current (post-filter) list.
  // For accurate global counts we'd need a separate query — keep it cheap for now.
  const totalsByPriority = useMemo(() => {
    const counts: Record<Priority | "all", number> = { all: items.length, hot: 0, warm: 0, cold: 0 };
    items.forEach((o) => { counts[o.priority] = (counts[o.priority] ?? 0) + 1; });
    return counts;
  }, [items]);

  const totalsByType = useMemo(() => {
    const counts: Record<OpportunityType | "all", number> = { all: items.length, direct: 0, cold: 0 };
    items.forEach((o) => { counts[o.type] = (counts[o.type] ?? 0) + 1; });
    return counts;
  }, [items]);

  return (
    <div className="flex h-full">
      <FilterPanel
        value={filters}
        onChange={setFilters}
        totalsByPriority={totalsByPriority}
        totalsByType={totalsByType}
      />
      <OpportunityList
        items={items}
        selectedId={selected?.id ?? null}
        onSelect={setSelectedId}
        loading={isLoading}
      />
      {selected ? (
        <OpportunityDetail opp={selected} />
      ) : (
        <div className="flex-1 flex items-center justify-center text-[12px] text-[var(--color-text-tertiary)]">
          {isLoading ? "Loading…" : "Select an opportunity to see details."}
        </div>
      )}
    </div>
  );
}
