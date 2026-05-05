import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { MoneyValue } from "../../design/primitives";
import { SortablePipelineCard } from "./SortablePipelineCard";
import type { Opportunity, Stage } from "../../types/opportunity";

interface Props {
  stage: Stage;
  label: string;
  opps: Opportunity[];
}

export function PipelineLane({ stage, label, opps }: Props) {
  const total = opps.reduce((sum, o) => sum + (o.estimated_value_usd || 0), 0);
  const { setNodeRef, isOver } = useDroppable({ id: stage });

  return (
    <div className="w-[260px] shrink-0 flex flex-col bg-[var(--color-bg)] border border-[var(--color-border)] rounded-[var(--radius-lg)]">
      {/* Header */}
      <div className="px-3 py-2.5 border-b border-[var(--color-border)] flex items-center justify-between">
        <div className="flex flex-col gap-0.5 min-w-0">
          <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
            {label}
          </span>
          <MoneyValue usd={total} size="md" tone="default" />
        </div>
        <span className="text-[11px] tabular-nums text-[var(--color-text-tertiary)] shrink-0">
          {opps.length}
        </span>
      </div>

      {/* Drop zone */}
      <div
        ref={setNodeRef}
        className={
          "flex-1 p-2 flex flex-col gap-2 overflow-y-auto min-h-[120px] transition-colors " +
          (isOver ? "bg-[var(--color-accent-soft)]" : "")
        }
      >
        <SortableContext items={opps.map((o) => o.id)} strategy={verticalListSortingStrategy}>
          {opps.map((opp) => (
            <SortablePipelineCard key={opp.id} opp={opp} />
          ))}
        </SortableContext>
        {opps.length === 0 && !isOver && (
          <div className="text-[11px] text-[var(--color-text-tertiary)] text-center py-4">
            Drop here
          </div>
        )}
      </div>
    </div>
  );
}
