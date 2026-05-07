import { useMemo, useState } from "react";
import { Send, X } from "lucide-react";
import { Opportunity } from "../../types/opportunity";
import { OpportunityListItem } from "./OpportunityListItem";
import { SendTemplateModal } from "./SendTemplateModal";
import { Button } from "../../design/primitives";

interface Props {
  items: Opportunity[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading: boolean;
  /** When `embedded`, skip the outer width/border container so a parent
   * (like InboxPage with category tabs above the list) can lay it out. */
  embedded?: boolean;
}

export function OpportunityList({ items, selectedId, onSelect, loading, embedded }: Props) {
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [showBulkSend, setShowBulkSend] = useState(false);

  function toggle(id: string) {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function clearSelection() {
    setChecked(new Set());
  }

  function selectAll() {
    setChecked(new Set(items.map((o) => o.id)));
  }

  const selectedItems = useMemo(
    () => items.filter((o) => checked.has(o.id)),
    [items, checked],
  );
  // Bulk send only makes sense for cold prospects — direct (job) leads
  // expect an individual reply on-platform, not a templated email blast.
  const selectedCold = selectedItems.filter((o) => o.type === "cold");
  const selectedDirectCount = selectedItems.length - selectedCold.length;
  const coldWithEmail = selectedCold.filter(
    (o) => o.contact_email && o.contact_email.includes("@"),
  ).length;

  const containerClass = embedded
    ? "flex-1 bg-[var(--color-bg)] flex flex-col min-h-0"
    : "w-[380px] shrink-0 bg-[var(--color-bg)] border-r border-[var(--color-border)] flex flex-col";

  return (
    <div className={containerClass}>
      <div className="h-9 px-3 flex items-center justify-between border-b border-[var(--color-border)]">
        <span className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
          {loading ? "Loading…" : `${items.length} opportunities`}
        </span>
        {items.length > 0 && (
          <button
            type="button"
            onClick={checked.size === items.length ? clearSelection : selectAll}
            className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] font-medium"
          >
            {checked.size === items.length ? "Clear" : "Select all"}
          </button>
        )}
      </div>

      {/* Bulk action bar — cold prospects only */}
      {checked.size > 0 && (
        <div className="px-3 py-2 border-b border-[var(--color-border)] bg-[var(--color-surface-raised)] flex items-center gap-2">
          <span className="text-[12px] text-[var(--color-text-primary)] flex-1 leading-tight">
            {selectedCold.length > 0 ? (
              <>
                {selectedCold.length} cold selected
                <span className="text-[var(--color-text-tertiary)]"> · {coldWithEmail} with email</span>
              </>
            ) : (
              <span className="text-[var(--color-text-tertiary)]">
                Bulk send only applies to cold prospects.
              </span>
            )}
            {selectedDirectCount > 0 && (
              <span className="block text-[10px] text-[var(--color-text-tertiary)] mt-0.5">
                {selectedDirectCount} direct (job) lead{selectedDirectCount === 1 ? "" : "s"} ignored —
                reply individually from the detail panel.
              </span>
            )}
          </span>
          <Button
            variant="primary"
            onClick={() => setShowBulkSend(true)}
            disabled={coldWithEmail === 0}
          >
            <Send className="w-3 h-3 mr-1" />
            Send to {coldWithEmail}
          </Button>
          <button
            type="button"
            onClick={clearSelection}
            className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]"
            aria-label="Clear selection"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="flex-1 overflow-auto">
        {items.length === 0 && !loading && (
          <div className="p-6 text-center text-[12px] text-[var(--color-text-tertiary)]">
            No fresh prey. Run a scan from Sources to catch some.
          </div>
        )}
        {items.map((opp) => (
          <OpportunityListItem
            key={opp.id}
            opp={opp}
            active={opp.id === selectedId}
            selected={checked.has(opp.id)}
            onClick={() => onSelect(opp.id)}
            onToggleSelect={(e) => {
              e.stopPropagation();
              toggle(opp.id);
            }}
          />
        ))}
      </div>

      {showBulkSend && (
        <SendTemplateModal
          recipients={selectedCold}
          onClose={() => {
            setShowBulkSend(false);
            // Keep selection so user can adjust + retry if some failed.
          }}
        />
      )}
    </div>
  );
}
