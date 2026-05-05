import clsx from "clsx";
import type { OpportunityFilters, Priority, OpportunityType } from "../../types/opportunity";

interface Props {
  value: OpportunityFilters;
  onChange: (next: OpportunityFilters) => void;
  totalsByPriority: Record<Priority | "all", number>;
  totalsByType: Record<OpportunityType | "all", number>;
}

function FilterRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[10px] uppercase tracking-wider text-[--color-text-tertiary] font-medium">
        {label}
      </span>
      {children}
    </div>
  );
}

function FilterPill({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count?: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "w-full flex items-center justify-between px-2.5 h-7 rounded-[--radius-sm] text-[12px] transition-colors",
        active
          ? "bg-[--color-accent-soft] text-[--color-accent]"
          : "text-[--color-text-secondary] hover:bg-[--color-surface-raised]",
      )}
    >
      <span>{label}</span>
      {count !== undefined && (
        <span className="text-[11px] tabular-nums opacity-70">{count}</span>
      )}
    </button>
  );
}

export function FilterPanel({ value, onChange, totalsByPriority, totalsByType }: Props) {
  return (
    <div className="w-[200px] shrink-0 bg-[--color-surface] border-r border-[--color-border] p-3 flex flex-col gap-4 overflow-auto">
      <FilterRow label="Type">
        <FilterPill
          label="All"
          count={totalsByType.all}
          active={!value.type}
          onClick={() => onChange({ ...value, type: undefined })}
        />
        <FilterPill
          label="Direct (jobs)"
          count={totalsByType.direct}
          active={value.type === "direct"}
          onClick={() => onChange({ ...value, type: "direct" })}
        />
        <FilterPill
          label="Cold (prospects)"
          count={totalsByType.cold}
          active={value.type === "cold"}
          onClick={() => onChange({ ...value, type: "cold" })}
        />
      </FilterRow>

      <FilterRow label="Priority">
        <FilterPill
          label="All"
          count={totalsByPriority.all}
          active={!value.priority}
          onClick={() => onChange({ ...value, priority: undefined })}
        />
        <FilterPill
          label="Hot"
          count={totalsByPriority.hot}
          active={value.priority === "hot"}
          onClick={() => onChange({ ...value, priority: "hot" })}
        />
        <FilterPill
          label="Warm"
          count={totalsByPriority.warm}
          active={value.priority === "warm"}
          onClick={() => onChange({ ...value, priority: "warm" })}
        />
        <FilterPill
          label="Cold"
          count={totalsByPriority.cold}
          active={value.priority === "cold"}
          onClick={() => onChange({ ...value, priority: "cold" })}
        />
      </FilterRow>

      <FilterRow label="Sort by">
        <FilterPill
          label="Score"
          active={!value.sort || value.sort === "score"}
          onClick={() => onChange({ ...value, sort: "score" })}
        />
        <FilterPill
          label="Value"
          active={value.sort === "value"}
          onClick={() => onChange({ ...value, sort: "value" })}
        />
        <FilterPill
          label="Recent"
          active={value.sort === "recent"}
          onClick={() => onChange({ ...value, sort: "recent" })}
        />
      </FilterRow>
    </div>
  );
}
