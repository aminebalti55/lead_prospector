import { useState } from "react";
import { Play, Pencil, Trash2, Plus } from "lucide-react";
import { Button, Card, Pill } from "../../design/primitives";
import {
  useSavedSearches,
  useDeleteSavedSearch,
  useRunSavedSearch,
  useUpdateSavedSearch,
} from "../../api/direct";
import { SavedSearchEditor } from "./SavedSearchEditor";
import type { SavedSearch } from "../../types/source";

function fmtLastRun(iso: string | null): string {
  if (!iso) return "never";
  const ms = Date.now() - new Date(iso).getTime();
  const h = Math.floor(ms / 3_600_000);
  if (h < 1) return "<1h ago";
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function SavedSearchesList() {
  const { data, isLoading } = useSavedSearches();
  const searches = (data?.searches ?? []) as SavedSearch[];

  const runMut = useRunSavedSearch();
  const updateMut = useUpdateSavedSearch();
  const deleteMut = useDeleteSavedSearch();

  const [editing, setEditing] = useState<SavedSearch | null>(null);
  const [creating, setCreating] = useState(false);

  return (
    <Card className="p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
            Saved searches
          </div>
          <div className="text-[11px] text-[var(--color-text-tertiary)]">
            {searches.length} {searches.length === 1 ? "search" : "searches"}
          </div>
        </div>
        <Button variant="primary" size="sm" onClick={() => setCreating(true)}>
          <Plus className="w-3 h-3" /> New
        </Button>
      </div>

      {isLoading && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">Loading…</div>
      )}

      {!isLoading && searches.length === 0 && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4 text-center">
          No saved searches yet. Click "New" to create one.
        </div>
      )}

      <div className="flex flex-col">
        {searches.map((s) => (
          <div
            key={s.id}
            className="flex items-center gap-3 py-2 border-b border-[var(--color-border)] last:border-0"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-medium text-[var(--color-text-primary)] truncate">
                  {s.name}
                </span>
                {!s.enabled && <Pill tone="neutral">paused</Pill>}
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-[var(--color-text-tertiary)] mt-0.5">
                <span className="truncate">{(s.keywords || []).join(", ")}</span>
                <span>·</span>
                <span>{s.frequency}</span>
                <span>·</span>
                <span>{(s.sources || []).length} sources</span>
                <span>·</span>
                <span>last run {fmtLastRun(s.last_run)}</span>
              </div>
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                updateMut.mutate({ id: s.id, body: { ...s, enabled: !s.enabled } })
              }
              disabled={updateMut.isPending}
            >
              {s.enabled ? "Pause" : "Resume"}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => runMut.mutate(s.id)}
              disabled={runMut.isPending}
            >
              <Play className="w-3 h-3" /> Run
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setEditing(s)}
            >
              <Pencil className="w-3 h-3" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                if (confirm(`Delete "${s.name}"?`)) deleteMut.mutate(s.id);
              }}
              disabled={deleteMut.isPending}
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
        ))}
      </div>

      {creating && <SavedSearchEditor onClose={() => setCreating(false)} />}
      {editing && <SavedSearchEditor initial={editing} onClose={() => setEditing(null)} />}
    </Card>
  );
}
