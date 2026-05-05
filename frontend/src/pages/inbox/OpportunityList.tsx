import { Opportunity } from "../../types/opportunity";
import { OpportunityListItem } from "./OpportunityListItem";

interface Props {
  items: Opportunity[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading: boolean;
}

export function OpportunityList({ items, selectedId, onSelect, loading }: Props) {
  return (
    <div className="w-[380px] shrink-0 bg-[--color-bg] border-r border-[--color-border] flex flex-col">
      <div className="h-9 px-3 flex items-center justify-between border-b border-[--color-border]">
        <span className="text-[11px] uppercase tracking-wider text-[--color-text-tertiary] font-medium">
          {loading ? "Loading…" : `${items.length} opportunities`}
        </span>
      </div>
      <div className="flex-1 overflow-auto">
        {items.length === 0 && !loading && (
          <div className="p-6 text-center text-[12px] text-[--color-text-tertiary]">
            No fresh prey. Run a scan from Sources to catch some.
          </div>
        )}
        {items.map((opp) => (
          <OpportunityListItem
            key={opp.id}
            opp={opp}
            active={opp.id === selectedId}
            onClick={() => onSelect(opp.id)}
          />
        ))}
      </div>
    </div>
  );
}
