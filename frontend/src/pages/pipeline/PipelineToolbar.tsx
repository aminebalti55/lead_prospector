import { Search } from "lucide-react";
import clsx from "clsx";
import type { OpportunityFilters, OpportunityType } from "../../types/opportunity";

interface Props {
  value: OpportunityFilters;
  onChange: (next: OpportunityFilters) => void;
  totalCount: number;
}

function TypePill({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "h-7 px-2.5 text-[12px] rounded-[var(--radius-sm)] transition-colors",
        active
          ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
          : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-raised)]",
      )}
    >
      {label}
    </button>
  );
}

export function PipelineToolbar({ value, onChange, totalCount }: Props) {
  return (
    <div className="flex items-center gap-3 mb-3">
      <div className="flex items-center gap-1">
        <TypePill
          label="All opportunities"
          active={!value.type}
          onClick={() => onChange({ ...value, type: undefined })}
        />
        <TypePill
          label="Direct (jobs)"
          active={value.type === "direct"}
          onClick={() => onChange({ ...value, type: "direct" as OpportunityType })}
        />
        <TypePill
          label="Cold (prospects)"
          active={value.type === "cold"}
          onClick={() => onChange({ ...value, type: "cold" as OpportunityType })}
        />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <div className="h-7 flex items-center gap-2 px-2.5 rounded-[var(--radius-sm)] bg-[var(--color-surface-raised)] border border-[var(--color-border)] w-[260px]">
          <Search className="w-3.5 h-3.5 text-[var(--color-text-tertiary)]" strokeWidth={1.75} />
          <input
            type="search"
            value={value.q ?? ""}
            onChange={(e) => onChange({ ...value, q: e.target.value })}
            placeholder="Search title, company, source…"
            className="bg-transparent border-0 outline-none text-[12px] flex-1 text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)]"
          />
        </div>
        <span className="text-[11px] text-[var(--color-text-tertiary)] tabular-nums">
          {totalCount} opportunities
        </span>
      </div>
    </div>
  );
}
