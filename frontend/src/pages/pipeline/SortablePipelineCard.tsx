import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { PipelineCard } from "./PipelineCard";
import type { Opportunity } from "../../types/opportunity";

interface Props {
  opp: Opportunity;
}

export function SortablePipelineCard({ opp }: Props) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: opp.id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <PipelineCard opp={opp} isDragging={isDragging} />
    </div>
  );
}
