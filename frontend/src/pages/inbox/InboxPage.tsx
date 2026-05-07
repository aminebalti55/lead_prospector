import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useOpportunities } from "../../api/opportunities";
import type { OpportunityFilters, Priority, OpportunityType } from "../../types/opportunity";
import { CategoryTabs } from "./CategoryTabs";
import { FilterPanel } from "./FilterPanel";
import { OpportunityList } from "./OpportunityList";
import { OpportunityDetail } from "./OpportunityDetail";

const POST_NEW = new Set(["contacted", "replied", "meeting", "won", "lost"]);

export function InboxPage() {
  const [filters, setFilters] = useState<OpportunityFilters>({ sort: "score", limit: 200 });
  const [searchParams] = useSearchParams();
  const oppFromUrl = searchParams.get("opp");
  const [selectedId, setSelectedId] = useState<string | null>(oppFromUrl);

  // Server query — `source`, `has_email`, `hide_contacted` are filtered
  // client-side so the category-tab counts stay accurate against the full
  // (type + priority) filtered set, not the per-source narrowed set.
  const { data, isLoading } = useOpportunities({
    ...filters,
    source: undefined,
    has_email: undefined,
    hide_contacted: undefined,
  });

  // Items shown in the category tabs — filtered by Type + Priority only.
  // The category tabs themselves are the next filter layer.
  const itemsBeforeCategory = data?.opportunities ?? [];

  // Final visible list: category-tab + has-email + hide-contacted on top.
  const items = useMemo(() => {
    let list = itemsBeforeCategory;
    if (filters.source) {
      list = list.filter((o) => o.source === filters.source);
    }
    if (filters.has_email) {
      list = list.filter((o) => o.contact_email && o.contact_email.includes("@"));
    }
    if (filters.hide_contacted) {
      list = list.filter((o) => !POST_NEW.has(o.stage));
    }
    return list;
  }, [
    itemsBeforeCategory,
    filters.source,
    filters.has_email,
    filters.hide_contacted,
  ]);

  const selected = items.find((o) => o.id === selectedId) ?? items[0] ?? null;

  useEffect(() => {
    if (oppFromUrl && oppFromUrl !== selectedId) setSelectedId(oppFromUrl);
  }, [oppFromUrl, selectedId]);

  useEffect(() => {
    if (!selectedId && items.length > 0) setSelectedId(items[0].id);
  }, [items, selectedId]);

  // Counts for the left FilterPanel — based on the broadest possible set
  // (no type filter applied) so the user can always see the full pivot.
  const allItems = data?.opportunities ?? [];

  const totalsByPriority = useMemo(() => {
    const counts: Record<Priority | "all", number> = { all: allItems.length, hot: 0, warm: 0, cold: 0 };
    allItems.forEach((o) => { counts[o.priority] = (counts[o.priority] ?? 0) + 1; });
    return counts;
  }, [allItems]);

  const totalsByType = useMemo(() => {
    const counts: Record<OpportunityType | "all", number> = { all: allItems.length, direct: 0, cold: 0 };
    allItems.forEach((o) => { counts[o.type] = (counts[o.type] ?? 0) + 1; });
    return counts;
  }, [allItems]);

  return (
    <div className="flex h-full">
      <FilterPanel
        value={filters}
        onChange={setFilters}
        totalsByPriority={totalsByPriority}
        totalsByType={totalsByType}
      />
      <div className="flex-1 flex min-w-0">
        <div className="w-[380px] shrink-0 flex flex-col border-r border-[var(--color-border)]">
          <CategoryTabs
            items={itemsBeforeCategory}
            activeSource={filters.source}
            onSelect={(source) => setFilters({ ...filters, source })}
          />
          <OpportunityList
            items={items}
            selectedId={selected?.id ?? null}
            onSelect={setSelectedId}
            loading={isLoading}
            embedded
          />
        </div>
        {selected ? (
          <OpportunityDetail opp={selected} />
        ) : (
          <div className="flex-1 flex items-center justify-center text-[12px] text-[var(--color-text-tertiary)]">
            {isLoading ? "Loading…" : "Select an opportunity to see details."}
          </div>
        )}
      </div>
    </div>
  );
}
