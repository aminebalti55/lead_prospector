import { useState } from "react";
import { X } from "lucide-react";
import { Button, Card } from "../../design/primitives";
import { useCreateSavedSearch } from "../../api/direct";
import { useUpdateSavedSearch } from "../../api/direct";
import type { SavedSearch } from "../../types/source";

const ALL_SOURCES = [
  "reddit", "linkedin", "linkedin_posts", "indeed", "twitter", "clutch", "goodfirms", "tanit",
  "google_maps", "yelp", "bbb", "yellowpages", "manta",
];

const FREQUENCIES = ["hourly", "daily", "weekly", "biweekly", "monthly"];

interface Props {
  initial?: SavedSearch;
  onClose: () => void;
}

export function SavedSearchEditor({ initial, onClose }: Props) {
  const [name, setName] = useState(initial?.name ?? "");
  const [keywordsRaw, setKeywordsRaw] = useState((initial?.keywords ?? []).join(", "));
  const [sources, setSources] = useState<string[]>(initial?.sources ?? ["reddit"]);
  const [frequency, setFrequency] = useState(initial?.frequency ?? "daily");
  const [maxResults, setMaxResults] = useState(initial?.max_results ?? 50);

  const create = useCreateSavedSearch();
  const update = useUpdateSavedSearch();

  function toggleSource(s: string) {
    setSources((curr) => (curr.includes(s) ? curr.filter((x) => x !== s) : [...curr, s]));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const keywords = keywordsRaw.split(",").map((k) => k.trim()).filter(Boolean);
    if (!name.trim() || keywords.length === 0 || sources.length === 0) return;
    const body = {
      name: name.trim(),
      keywords,
      sources,
      frequency,
      max_results: maxResults,
      enabled: initial?.enabled ?? true,
    };
    if (initial) {
      await update.mutateAsync({ id: initial.id, body });
    } else {
      await create.mutateAsync(body);
    }
    onClose();
  }

  const isPending = create.isPending || update.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <Card
        className="w-[520px] max-h-[80vh] overflow-auto p-5 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-[14px] font-semibold text-[var(--color-text-primary)]">
            {initial ? "Edit saved search" : "New saved search"}
          </h2>
          <button type="button" onClick={onClose} className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)]"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Keywords (comma-separated)</label>
            <input
              value={keywordsRaw}
              onChange={(e) => setKeywordsRaw(e.target.value)}
              placeholder="webflow, react developer"
              required
              className="h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)]"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Sources</label>
            <div className="flex flex-wrap gap-1">
              {ALL_SOURCES.map((s) => {
                const active = sources.includes(s);
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => toggleSource(s)}
                    className={
                      "h-7 px-2.5 text-[11px] rounded-[var(--radius-sm)] border transition-colors " +
                      (active
                        ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)] border-[var(--color-accent)]"
                        : "text-[var(--color-text-secondary)] border-[var(--color-border)] hover:border-[var(--color-border-strong)]")
                    }
                  >
                    {s}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Frequency</label>
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value)}
                className="h-8 px-2 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)]"
              >
                {FREQUENCIES.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Max results</label>
              <input
                type="number"
                min={1}
                max={500}
                value={maxResults}
                onChange={(e) => setMaxResults(parseInt(e.target.value) || 50)}
                className="h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)]"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose} disabled={isPending}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={isPending}>
              {isPending ? "Saving…" : initial ? "Save changes" : "Create"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
