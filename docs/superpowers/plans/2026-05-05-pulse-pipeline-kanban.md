# Pulse — Pipeline Kanban Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Commit message rule (project-wide):** NEVER add `Co-Authored-By: Claude`, "Generated with Claude Code", or any AI/assistant attribution to any commit message. Each task spec gives the exact message — use it verbatim.

**Goal:** Build the **Pipeline** page — a 7-column kanban board (New → Researching → Contacted → Replied → Meeting → Won → Lost) with drag-and-drop between lanes, `$` totals per lane header, and a top toolbar (type filter + search). Each card shows the dollar value, title, source, and location. Dragging fires the existing `PATCH /api/opportunities/{id}/stage` with optimistic UI; failure rolls back. After this plan, the user can visually triage their entire pipeline by dragging deals across stages — the third visual from the prototype mockups becomes real.

**Architecture:**
- **Frontend only.** Backend already has `PATCH /api/opportunities/{id}/stage` from Plan 1 + `useUpdateStage` hook from Plan 1. We add `@dnd-kit/core` for drag-and-drop, build 4 new components (`PipelineCard`, `PipelineLane`, `PipelineBoard`, `PipelineToolbar`), compose a `PipelinePage`, and wire the `/pipeline` route to it.
- **Optimistic updates via react-query** `onMutate` / `onError` hooks. The card visually jumps to the target lane the moment the drop is registered; if the PATCH fails, the card snaps back and a toast appears.
- **Lane grouping is computed in the frontend** from the existing `useOpportunities()` hook. No new backend endpoint — same filter+sort URL with a higher `limit` (default 500) covers it.
- **Click a card → navigate to `/inbox?opp=<id>`.** Inbox reads the query param and pre-selects that opportunity. Small enhancement to `InboxPage`.

**Tech Stack:** React 18, react-router-dom 6, Tailwind v4, @tanstack/react-query 5, lucide-react, **@dnd-kit/core**, **@dnd-kit/sortable**. No backend changes.

---

## Scope decision

This is **Plan 3 of 5+**. After this:

| # | Plan | Status |
|---|---|---|
| 1 | Foundation & Inbox | ✅ Shipped |
| 2 | Hub & Live PulseBar | ✅ Shipped + bug-fixed |
| **3 (this)** | **Pipeline Kanban** | About to ship |
| 4 | Sources & scheduler upgrades (Run Now / Pause / Edit / Toggle / freq fixes) | Pending |
| 5 | Outreach + Settings round-trip + cleanup | Pending |
| 6 | Tanit Jobs scraper (Cloudflare-protected, Scrapling stealth) | Pending |
| 7 | Supabase migration | Pending (last) |

---

## File structure (this plan)

**New frontend files:**
- `frontend/src/pages/pipeline/PipelinePage.tsx` — page composition
- `frontend/src/pages/pipeline/PipelineToolbar.tsx` — type filter chips + search + result count
- `frontend/src/pages/pipeline/PipelineBoard.tsx` — 7-column grid with `<DndContext>`
- `frontend/src/pages/pipeline/PipelineLane.tsx` — single column with droppable zone, header (name + count + $ total)
- `frontend/src/pages/pipeline/PipelineCard.tsx` — single opp card with drag handle, $, title, source pill, location

**New frontend hooks:**
- `frontend/src/api/opportunities.ts` — extend `useUpdateStage` with optimistic update logic (modify in place; preserve existing call sites used by InboxPage)

**Modified frontend files:**
- `frontend/package.json` — add `@dnd-kit/core` + `@dnd-kit/sortable`
- `frontend/src/App.tsx` — replace `/pipeline` PlaceholderPage with `<PipelinePage />`
- `frontend/src/pages/inbox/InboxPage.tsx` — read `?opp=<id>` query param; pre-select that opportunity

**Untouched (preserved):**
- All Plan 1+2 code: backend, primitives, shell, opportunities router, hub router, hooks
- Backend remains unchanged (no new endpoints)

---

## Conventions

- **Lane order = Stage enum order** (matches `src/core/models.py`):
  1. New
  2. Researching
  3. Contacted
  4. Replied
  5. Meeting
  6. Won
  7. Lost
- **Lane $ total** = sum of `estimated_value_usd` for opportunities currently visible (post-filter) in that lane.
- **Card priority dot** uses the same `StatusDot` color mapping as Inbox (hot/warm/cold).
- **Drag-drop library**: `@dnd-kit/core` for the context + sensors; `@dnd-kit/sortable` for the per-card sortable behavior inside a lane (lets users reorder within a lane in v1+ — for v1 we only USE the cross-lane drop, but installing both libraries means future ordering is one prop away).
- **Optimistic update**: on `mutate`, capture current state via `queryClient.getQueryData(["opportunities", filters])`, apply local stage change, set new data via `setQueryData`. On `onError`, restore original. On `onSettled`, invalidate to re-sync.
- **Toast feedback**: minimal — use `console.error` for rollback in v1 (no toast lib introduced yet). User sees the card snap back, which is enough signal.

---

## Pre-flight

- [ ] **Step 0.1: Verify Plan 2 + QA fixes are committed and branch is clean**

Run from repo root:
```bash
cd C:\Users\JIMMY\lead_prospector
git status
git log --oneline pulse-foundation -5
```
Expected: working tree clean, on `pulse-foundation`, latest commit is `5e54622 fix(stats): make this_week comparison TZ-aware...` or later.

- [ ] **Step 0.2: Backend + frontend running**

Start them in separate terminals if not already running:
```powershell
.venv\Scripts\python.exe run_server.py --no-reload
cd frontend; npm run dev
```

- [ ] **Step 0.3: Confirm test data exists**

```bash
curl -s "http://localhost:8000/api/opportunities?limit=10" | python -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"total\"]} opportunities'); print('Stages:', sorted({o[\"stage\"] for o in d['opportunities']}))"
```
Expected: a few opportunities exist across multiple stages. If only `new`, manually PATCH a couple to other stages so kanban testing has visible cards in different lanes.

---

## Task 1: Install drag-drop dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1.1: Install @dnd-kit/core and @dnd-kit/sortable**

```powershell
cd frontend
npm install @dnd-kit/core @dnd-kit/sortable
```

Expected: both added to dependencies. Likely versions: `@dnd-kit/core@^6.x`, `@dnd-kit/sortable@^8.x` (the libraries are stable; minor variation is fine).

- [ ] **Step 1.2: Verify build still passes**

```powershell
npm run build
```
Expected: build succeeds.

- [ ] **Step 1.3: Commit**

```bash
cd ..
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(deps): add @dnd-kit/core + @dnd-kit/sortable for Pipeline kanban"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 2: `PipelineCard` component

**Why:** A single opportunity card rendered inside a lane. Pure presentation — wired into the drag system in Task 4. Click navigates to `/inbox?opp=<id>`.

**File:** `frontend/src/pages/pipeline/PipelineCard.tsx`

- [ ] **Step 2.1: Create the file**

```tsx
import { useNavigate } from "react-router-dom";
import { MapPin } from "lucide-react";
import { MoneyValue, Pill, StatusDot } from "../../design/primitives";
import type { Opportunity } from "../../types/opportunity";

interface Props {
  opp: Opportunity;
  isDragging?: boolean;
}

export function PipelineCard({ opp, isDragging = false }: Props) {
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate(`/inbox?opp=${opp.id}`)}
      className={
        "p-2.5 rounded-[var(--radius-md)] border bg-[var(--color-surface)] cursor-grab active:cursor-grabbing flex flex-col gap-1.5 transition-shadow " +
        (isDragging
          ? "border-[var(--color-accent)] shadow-[0_4px_12px_rgba(0,0,0,0.4)]"
          : "border-[var(--color-border)] hover:border-[var(--color-border-strong)]")
      }
    >
      <div className="flex items-center gap-1.5 min-w-0">
        <MoneyValue usd={opp.estimated_value_usd} size="md" tone="accent" />
        <span className="ml-auto">
          <StatusDot
            status={
              opp.priority === "hot"
                ? "hot"
                : opp.priority === "warm"
                ? "warm"
                : "cold"
            }
          />
        </span>
      </div>
      <div className="text-[12px] text-[var(--color-text-primary)] leading-snug line-clamp-2">
        {opp.title || "(no title)"}
      </div>
      <div className="flex items-center gap-1.5 text-[10px] text-[var(--color-text-tertiary)]">
        <Pill tone="neutral">{opp.source}</Pill>
        {opp.location && (
          <span className="flex items-center gap-0.5 truncate">
            <MapPin className="w-2.5 h-2.5" /> {opp.location}
          </span>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2.2: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```
```bash
git add frontend/src/pages/pipeline/PipelineCard.tsx
git commit -m "feat(pipeline): add PipelineCard"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 3: `PipelineLane` component

**Why:** One column = one Stage. Header shows stage name + card count + sum-`$`. Body holds cards. Whole lane is a droppable zone.

**File:** `frontend/src/pages/pipeline/PipelineLane.tsx`

- [ ] **Step 3.1: Create the file**

```tsx
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
```

- [ ] **Step 3.2: Commit (build will fail until Task 4 lands — that's OK, we commit now and verify the chain at end)**

```bash
git add frontend/src/pages/pipeline/PipelineLane.tsx
git commit -m "feat(pipeline): add PipelineLane (droppable column with $ total + count)"
```

**Reminder: NO `Co-Authored-By` trailer.**

> Note: this commit will reference `SortablePipelineCard` which is created in the next task. The build won't pass until Task 4 lands. This is intentional — we keep commits granular but verify the full chain in Task 6's smoke step. If you really want a green build at every commit, do Tasks 3+4 in a single commit. Either is fine; pick the one that matches your team's discipline.

---

## Task 4: `SortablePipelineCard` (drag wrapper)

**Why:** `PipelineCard` is presentational. This wrapper handles the drag mechanics from `@dnd-kit/sortable`. Splitting them keeps the visual component testable in isolation.

**File:** `frontend/src/pages/pipeline/SortablePipelineCard.tsx`

- [ ] **Step 4.1: Create the file**

```tsx
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
```

- [ ] **Step 4.2: Verify build (now Task 3+4 chain compiles)**

```powershell
cd frontend && npm run build
cd ..
```
Expected: build succeeds.

- [ ] **Step 4.3: Commit**

```bash
git add frontend/src/pages/pipeline/SortablePipelineCard.tsx
git commit -m "feat(pipeline): add SortablePipelineCard drag wrapper"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 5: Extend `useUpdateStage` with optimistic updates

**Why:** Drag-drop UX needs the card to jump to the target lane instantly, not after the network round-trip. React-query's `onMutate` lets us mutate the cache pre-flight; `onError` rolls back.

**File:** `frontend/src/api/opportunities.ts` (modify in place — preserve the existing API; only add optimistic logic to `useUpdateStage`)

- [ ] **Step 5.1: Read current file**

```bash
cat frontend/src/api/opportunities.ts
```

- [ ] **Step 5.2: Replace `useUpdateStage` definition**

Find the current export:

```ts
export function useUpdateStage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, stage }: { id: string; stage: Stage }) =>
      apiFetch(`/opportunities/${id}/stage`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stage }),
      }),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ["opportunities"] });
      qc.invalidateQueries({ queryKey: ["opportunity", id] });
    },
  });
}
```

Replace with:

```ts
export function useUpdateStage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, stage }: { id: string; stage: Stage }) =>
      apiFetch(`/opportunities/${id}/stage`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stage }),
      }),
    // Optimistic: snapshot every active opportunities query, mutate the matching opp's stage in place.
    onMutate: async ({ id, stage }) => {
      await qc.cancelQueries({ queryKey: ["opportunities"] });
      const snapshots = qc.getQueriesData<OpportunityListResponse>({ queryKey: ["opportunities"] });
      snapshots.forEach(([key, data]) => {
        if (!data) return;
        const next: OpportunityListResponse = {
          ...data,
          opportunities: data.opportunities.map((o) =>
            o.id === id ? { ...o, stage } : o,
          ),
        };
        qc.setQueryData(key, next);
      });
      return { snapshots };
    },
    onError: (_err, _vars, context) => {
      // Roll back on failure
      context?.snapshots.forEach(([key, data]) => qc.setQueryData(key, data));
      console.error("Stage update failed; rolled back optimistic change");
    },
    onSettled: (_data, _err, { id }) => {
      qc.invalidateQueries({ queryKey: ["opportunities"] });
      qc.invalidateQueries({ queryKey: ["opportunity", id] });
      qc.invalidateQueries({ queryKey: ["hub"] });
    },
  });
}
```

- [ ] **Step 5.3: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/api/opportunities.ts
git commit -m "feat(api): add optimistic update + rollback to useUpdateStage"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 6: `PipelineBoard` component (DndContext + 7 lanes)

**Why:** Wires the drag-and-drop together. Owns the `<DndContext>`, the sensor config, and the drag-end handler that calls `useUpdateStage`.

**File:** `frontend/src/pages/pipeline/PipelineBoard.tsx`

- [ ] **Step 6.1: Create the file**

```tsx
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
```

- [ ] **Step 6.2: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/pages/pipeline/PipelineBoard.tsx
git commit -m "feat(pipeline): add PipelineBoard with 7 lanes + drag-drop stage updates"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 7: `PipelineToolbar` component

**Why:** Top-of-page filter chips (All / Direct / Cold) + search input + result count. Filters apply to the data fetched, which the Board groups into lanes.

**File:** `frontend/src/pages/pipeline/PipelineToolbar.tsx`

- [ ] **Step 7.1: Create the file**

```tsx
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
```

- [ ] **Step 7.2: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/pages/pipeline/PipelineToolbar.tsx
git commit -m "feat(pipeline): add PipelineToolbar with type filter + search"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 8: `PipelinePage` composition

**File:** `frontend/src/pages/pipeline/PipelinePage.tsx`

- [ ] **Step 8.1: Create the file**

```tsx
import { useState } from "react";
import { useOpportunities } from "../../api/opportunities";
import type { OpportunityFilters } from "../../types/opportunity";
import { PipelineToolbar } from "./PipelineToolbar";
import { PipelineBoard } from "./PipelineBoard";

export function PipelinePage() {
  const [filters, setFilters] = useState<OpportunityFilters>({ sort: "score", limit: 500 });
  const { data, isLoading } = useOpportunities(filters);
  const opps = data?.opportunities ?? [];

  return (
    <div className="p-6 flex flex-col h-full max-w-full overflow-hidden">
      <PipelineToolbar value={filters} onChange={setFilters} totalCount={data?.total ?? 0} />

      {isLoading && (
        <div className="flex-1 flex items-center justify-center text-[12px] text-[var(--color-text-tertiary)]">
          Loading…
        </div>
      )}

      {!isLoading && opps.length === 0 && (
        <div className="flex-1 flex items-center justify-center text-[12px] text-[var(--color-text-tertiary)]">
          No opportunities match. Run a scan or clear your filters.
        </div>
      )}

      {!isLoading && opps.length > 0 && (
        <div className="flex-1 overflow-x-auto">
          <PipelineBoard opps={opps} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 8.2: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/pages/pipeline/PipelinePage.tsx
git commit -m "feat(pipeline): compose PipelinePage from toolbar + board"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 9: Wire `/pipeline` route to `PipelinePage`

**File:** `frontend/src/App.tsx`

- [ ] **Step 9.1: Read current `App.tsx`**

```bash
cat frontend/src/App.tsx
```

- [ ] **Step 9.2: Add the import**

Find the import line:
```tsx
import { HubPage } from "./pages/hub/HubPage";
```
Add directly after:
```tsx
import { PipelinePage } from "./pages/pipeline/PipelinePage";
```

- [ ] **Step 9.3: Replace the `/pipeline` route element**

Find:
```tsx
<Route path="/pipeline" element={<PlaceholderPage title="Pipeline" shipping="Plan 3 — Pipeline Kanban" />} />
```
Replace with:
```tsx
<Route path="/pipeline" element={<PipelinePage />} />
```

- [ ] **Step 9.4: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/App.tsx
git commit -m "feat(routes): mount PipelinePage at /pipeline"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 10: Inbox `?opp=<id>` deep-link support

**Why:** Pipeline cards link to `/inbox?opp=<id>` so users can jump from a kanban card straight into the full opportunity detail. Tiny enhancement to `InboxPage`.

**File:** `frontend/src/pages/inbox/InboxPage.tsx`

- [ ] **Step 10.1: Read current `InboxPage.tsx`**

```bash
cat frontend/src/pages/inbox/InboxPage.tsx
```

- [ ] **Step 10.2: Add `useSearchParams` import + initial selection logic**

Find the existing imports at the top:

```tsx
import { useEffect, useMemo, useState } from "react";
```

Replace with:

```tsx
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
```

Then find the existing `useState` for `selectedId`:

```tsx
const [selectedId, setSelectedId] = useState<string | null>(null);
```

Replace with this block:

```tsx
const [searchParams] = useSearchParams();
const oppFromUrl = searchParams.get("opp");
const [selectedId, setSelectedId] = useState<string | null>(oppFromUrl);
```

Then find the existing auto-select effect:

```tsx
useEffect(() => {
  if (!selectedId && items.length > 0) setSelectedId(items[0].id);
}, [items, selectedId]);
```

Replace with:

```tsx
// If URL ?opp= param changes, prefer it over current selection
useEffect(() => {
  if (oppFromUrl && oppFromUrl !== selectedId) setSelectedId(oppFromUrl);
}, [oppFromUrl, selectedId]);

useEffect(() => {
  if (!selectedId && items.length > 0) setSelectedId(items[0].id);
}, [items, selectedId]);
```

- [ ] **Step 10.3: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/pages/inbox/InboxPage.tsx
git commit -m "feat(inbox): support ?opp=<id> deep link from Pipeline cards"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 11: E2E smoke + visual check

- [ ] **Step 11.1: Run all backend tests** (no backend changes in this plan, but confirm nothing broke):

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_hub_aggregator.py tests/backend/test_hub_router.py tests/backend/test_opportunity_aggregator.py tests/backend/test_opportunities_router.py -v
```
Expected: all pass.

- [ ] **Step 11.2: Final frontend build**

```powershell
cd frontend && npm run build
cd ..
```
Expected: success.

- [ ] **Step 11.3: Manual end-to-end check**

Make sure backend + frontend are running. Then:

1. Open `http://localhost:5173/pipeline`. Expected: 7 columns visible (New, Researching, Contacted, Replied, Meeting, Won, Lost), each header showing `0` count and `$0` total if empty.
2. If you have opportunities in different stages (PATCH a few via the API or via Inbox first), expected: cards appear in the matching lane. Each lane header shows correct count + summed `$`.
3. **Drag a card from "New" to "Contacted"**. Expected: card visually jumps instantly. No reload needed. Within ~1 second the lane totals update (mutation succeeds + invalidate fires).
4. Click a card. Expected: navigates to `/inbox?opp=<id>` and the right pane shows that opportunity's detail.
5. Type in the search box. Expected: lanes filter in place — cards that don't match disappear; lane totals adjust.
6. Click "Direct (jobs)" filter. Expected: only direct-type opportunities visible.
7. **Force a network failure to verify rollback**: open DevTools → Network → set "Offline". Drag a card to a different lane. Expected: card jumps optimistically, then snaps back when the request fails. Check console for the rollback error message.

- [ ] **Step 11.4: Final commit (if anything outstanding)**

```bash
git status
# If anything is uncommitted, commit with a chore: prefix
```

---

## Self-review notes (already addressed inline)

- **Spec coverage:** 7 lanes ✓, drag-drop between lanes ✓, $ totals per lane ✓, type filter + search toolbar ✓, optimistic update + rollback ✓, click-card → inbox detail ✓.
- **Placeholders:** None. Every task has full code.
- **Type consistency:** `Stage` type from `frontend/src/types/opportunity.ts` is used throughout. The `LANES` array in `PipelineBoard.tsx` lists all 7 in Stage enum order. The `grouped` map in `PipelineBoard` initializes all 7 stages explicitly.
- **Backwards compat:** `useUpdateStage` keeps the same signature (still callable as `mutate({id, stage})` from InboxPage's `OpportunityDetail`). The optimistic logic is additive. Only behavior change: stage updates from Inbox now feel instant too (free win).
- **Lane visual order**: hardcoded in `PipelineBoard.LANES` matching the prototype's left-to-right flow.
- **No backend changes**: this plan is pure frontend. The PATCH endpoint and the opportunities GET endpoint are reused from Plan 1. The Hub stats endpoint will pick up changes automatically on its 30s poll.
- **Risk**: optimistic update could desync from backend if multiple writes race. For solo single-user use (this app's scope), that's not a concern. If multi-user is added later (Plan 5+), revisit.
