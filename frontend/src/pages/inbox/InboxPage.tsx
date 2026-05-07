import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useHotkeys } from "react-hotkeys-hook";
import { Keyboard } from "lucide-react";
import { useOpportunities } from "../../api/opportunities";
import type { OpportunityFilters, Priority, OpportunityType } from "../../types/opportunity";
import { useInboxHotkeys } from "../../hooks/useInboxHotkeys";
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

  // Hotkeys: J/K nav, A apply, R reject, V viewing, O / Enter open, ? help.
  useInboxHotkeys({ items, selectedId, setSelectedId });
  const [showHelp, setShowHelp] = useState(false);
  useHotkeys("shift+slash", () => setShowHelp((v) => !v), { preventDefault: true }, []);
  useHotkeys("escape", () => setShowHelp(false), { enabled: showHelp }, []);

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
    <div className="flex h-full relative">
      {/* Floating shortcut-help button — opens via ? or click. */}
      <button
        type="button"
        onClick={() => setShowHelp(true)}
        className="absolute bottom-4 left-[210px] z-10 h-7 w-7 rounded-full bg-[var(--color-surface-raised)] border border-[var(--color-border)] flex items-center justify-center text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)] transition-colors"
        aria-label="Keyboard shortcuts"
        title="Keyboard shortcuts (?)"
      >
        <Keyboard className="w-3.5 h-3.5" />
      </button>
      {showHelp && <ShortcutHelp onClose={() => setShowHelp(false)} />}
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

/** Keyboard-shortcut cheat sheet, toggled by `?`. */
function ShortcutHelp({ onClose }: { onClose: () => void }) {
  const rows: Array<[string, string]> = [
    ["J / ↓", "Next lead"],
    ["K / ↑", "Previous lead"],
    ["A", "Mark as Applied (direct) / Contacted (cold)"],
    ["R", "Reject this lead"],
    ["V", "Mark as Viewing"],
    ["O / Enter", "Open original (auto-flips to Viewing)"],
    ["⌘ K", "Open command palette"],
    ["?", "Toggle this overlay"],
  ];
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="w-[420px] bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-md)] p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="text-[14px] font-semibold text-[var(--color-text-primary)] mb-3">
          Keyboard shortcuts
        </div>
        <table className="w-full text-[12px]">
          <tbody>
            {rows.map(([key, label]) => (
              <tr key={key}>
                <td className="py-1.5 pr-3">
                  <kbd className="text-[11px] text-[var(--color-text-secondary)] border border-[var(--color-border)] rounded px-1.5 py-0.5 bg-[var(--color-surface-raised)] font-mono">
                    {key}
                  </kbd>
                </td>
                <td className="py-1.5 text-[var(--color-text-primary)]">{label}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
