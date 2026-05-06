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
}

export function OpportunityList({ items, selectedId, onSelect, loading }: Props) {
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
  const selectedWithEmail = selectedItems.filter(
    (o) => o.contact_email && o.contact_email.includes("@"),
  ).length;

  return (
    <div className="w-[380px] shrink-0 bg-[var(--color-bg)] border-r border-[var(--color-border)] flex flex-col">
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

      {/* Bulk action bar */}
      {checked.size > 0 && (
        <div className="px-3 py-2 border-b border-[var(--color-border)] bg-[var(--color-surface-raised)] flex items-center gap-2">
          <span className="text-[12px] text-[var(--color-text-primary)] flex-1">
            {checked.size} selected
            {selectedWithEmail < checked.size && (
              <span className="text-[var(--color-text-tertiary)]">
                {" "}
                · {selectedWithEmail} with email
              </span>
            )}
          </span>
          <Button
            variant="primary"
            onClick={() => setShowBulkSend(true)}
            disabled={selectedWithEmail === 0}
          >
            <Send className="w-3 h-3 mr-1" />
            Send template
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
          recipients={selectedItems}
          onClose={() => {
            setShowBulkSend(false);
            // Keep selection so user can adjust + retry if some failed.
          }}
        />
      )}
    </div>
  );
}
