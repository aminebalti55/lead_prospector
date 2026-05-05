import { useMemo } from "react";
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
} from "@dnd-kit/core";
import { PipelineLane } from "./PipelineLane";
import { useUpdateStage } from "../../api/opportunities";
import type { Opportunity, Stage } from "../../types/opportunity";

const LANES: Array<{ stage: Stage; label: string }> = [
  { stage: "new", label: "New" },
  { stage: "researching", label: "Researching" },
  { stage: "contacted", label: "Contacted" },
  { stage: "replied", label: "Replied" },
  { stage: "meeting", label: "Meeting" },
  { stage: "won", label: "Won" },
  { stage: "lost", label: "Lost" },
];

interface Props {
  opps: Opportunity[];
}

export function PipelineBoard({ opps }: Props) {
  const updateStage = useUpdateStage();

  // 8px activation distance prevents click-to-drag on small accidental moves.
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  const grouped = useMemo(() => {
    const map: Record<Stage, Opportunity[]> = {
      new: [],
      researching: [],
      contacted: [],
      replied: [],
      meeting: [],
      won: [],
      lost: [],
    };
    opps.forEach((o) => {
      if (map[o.stage]) map[o.stage].push(o);
    });
    return map;
  }, [opps]);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over) return;
    const oppId = String(active.id);
    const targetStage = String(over.id) as Stage;
    const opp = opps.find((o) => o.id === oppId);
    if (!opp || opp.stage === targetStage) return;
    if (!LANES.some((l) => l.stage === targetStage)) return;
    updateStage.mutate({ id: oppId, stage: targetStage });
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={handleDragEnd}>
      <div className="flex gap-3 overflow-x-auto p-1">
        {LANES.map(({ stage, label }) => (
          <PipelineLane key={stage} stage={stage} label={label} opps={grouped[stage]} />
        ))}
      </div>
    </DndContext>
  );
}
