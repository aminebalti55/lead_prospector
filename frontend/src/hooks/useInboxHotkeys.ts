import { useHotkeys } from "react-hotkeys-hook";
import type { Opportunity } from "../types/opportunity";
import { useUpdateStage } from "../api/opportunities";

interface Args {
  items: Opportunity[];
  selectedId: string | null;
  setSelectedId: (id: string) => void;
  /** Whether the inbox is the focused page — disable shortcuts elsewhere. */
  enabled?: boolean;
}

/** Inbox keyboard shortcuts. Bound while the user is on /inbox.
 *
 *  J / ↓        next lead
 *  K / ↑        previous lead
 *  A            mark applied (direct) / contacted (cold)
 *  R            mark rejected (lost)
 *  V            mark viewing (researching)
 *  O / Enter    open original URL in a new tab + auto-flip stage to viewing
 *
 * `enableOnFormTags` is intentionally OFF so typing in the notes textarea
 * doesn't accidentally fire shortcuts.
 */
export function useInboxHotkeys({ items, selectedId, setSelectedId, enabled = true }: Args) {
  const updateStage = useUpdateStage();
  const idx = items.findIndex((o) => o.id === selectedId);
  const current = idx >= 0 ? items[idx] : null;

  function move(delta: number) {
    if (items.length === 0) return;
    const next = Math.max(0, Math.min(items.length - 1, (idx < 0 ? 0 : idx) + delta));
    setSelectedId(items[next].id);
  }

  useHotkeys("j, down", () => move(+1), { enabled }, [items, idx]);
  useHotkeys("k, up",   () => move(-1), { enabled }, [items, idx]);

  useHotkeys(
    "a",
    () => {
      if (current) updateStage.mutate({ id: current.id, stage: "contacted" });
    },
    { enabled },
    [current],
  );

  useHotkeys(
    "r",
    () => {
      if (current) updateStage.mutate({ id: current.id, stage: "lost" });
    },
    { enabled },
    [current],
  );

  useHotkeys(
    "v",
    () => {
      if (current) updateStage.mutate({ id: current.id, stage: "researching" });
    },
    { enabled },
    [current],
  );

  useHotkeys(
    "o, enter",
    () => {
      if (!current?.url) return;
      if (current.stage === "new") {
        updateStage.mutate({ id: current.id, stage: "researching" });
      }
      window.open(current.url, "_blank", "noopener,noreferrer");
    },
    { enabled },
    [current],
  );
}
