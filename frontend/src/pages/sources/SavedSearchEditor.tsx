import { useMemo, useState } from "react";
import { X, Briefcase, Users } from "lucide-react";
import clsx from "clsx";
import { Button, Card } from "../../design/primitives";
import { useCreateSavedSearch, useUpdateSavedSearch } from "../../api/direct";
import { useNiches } from "../../api/cold";
import type { SavedSearch } from "../../types/source";

const FREQUENCIES = ["hourly", "daily", "weekly", "biweekly", "monthly"];

// Sources we render per mode. Direct = job boards. Cold = directory scrapers.
// Lists are intentionally kept short here — when we add new sources we just
// extend these arrays.
const DIRECT_SOURCES = [
  "reddit", "linkedin", "linkedin_posts", "indeed", "remoteok",
  "twitter", "clutch", "goodfirms", "tanit",
] as const;

const COLD_SOURCES = [
  "google_maps", "yelp", "yellowpages", "bbb", "manta",
] as const;

interface Props {
  initial?: SavedSearch;
  onClose: () => void;
}

type Mode = "direct" | "cold";

export function SavedSearchEditor({ initial, onClose }: Props) {
  const [mode, setMode] = useState<Mode>(initial?.type ?? "direct");
  const [name, setName] = useState(initial?.name ?? "");
  const [keywordsRaw, setKeywordsRaw] = useState((initial?.keywords ?? []).join(", "));
  const [locationsRaw, setLocationsRaw] = useState((initial?.locations ?? []).join(", "));
  const [selectedNiches, setSelectedNiches] = useState<string[]>(initial?.niches ?? []);
  const [sources, setSources] = useState<string[]>(
    initial?.sources && initial.sources.length > 0
      ? initial.sources
      : (initial?.type ?? "direct") === "direct"
        ? ["reddit", "linkedin", "indeed", "remoteok"]
        : ["google_maps", "yelp", "yellowpages", "manta"],
  );
  const [frequency, setFrequency] = useState(initial?.frequency ?? "daily");
  const [maxResults, setMaxResults] = useState(initial?.max_results ?? 50);

  const niches = useNiches();
  const create = useCreateSavedSearch();
  const update = useUpdateSavedSearch();

  // Switching mode resets sources to that mode's sensible defaults so the
  // user doesn't accidentally save a "direct" search with cold sources.
  function changeMode(next: Mode) {
    if (next === mode) return;
    setMode(next);
    setSources(
      next === "direct"
        ? ["reddit", "linkedin", "indeed", "remoteok"]
        : ["google_maps", "yelp", "yellowpages", "manta"],
    );
  }

  function toggleSource(s: string) {
    setSources((curr) => (curr.includes(s) ? curr.filter((x) => x !== s) : [...curr, s]));
  }

  function toggleNiche(n: string) {
    setSelectedNiches((curr) => (curr.includes(n) ? curr.filter((x) => x !== n) : [...curr, n]));
  }

  /** Group niches by category for the picker. */
  const nichesByCategory = useMemo(() => {
    const groups: Record<string, typeof niches.data extends { niches: infer T } ? T : never> = {} as any;
    (niches.data?.niches ?? []).forEach((n) => {
      if (!groups[n.category]) groups[n.category] = [] as any;
      (groups[n.category] as any).push(n);
    });
    return groups;
  }, [niches.data]);

  const isPending = create.isPending || update.isPending;

  const isDirectValid =
    mode === "direct" &&
    !!name.trim() &&
    keywordsRaw.split(",").map((k) => k.trim()).filter(Boolean).length > 0 &&
    sources.length > 0;

  const isColdValid =
    mode === "cold" &&
    !!name.trim() &&
    locationsRaw.split(",").map((l) => l.trim()).filter(Boolean).length > 0 &&
    selectedNiches.length > 0 &&
    sources.length > 0;

  const canSubmit = mode === "direct" ? isDirectValid : isColdValid;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    const keywords = keywordsRaw.split(",").map((k) => k.trim()).filter(Boolean);
    const locations = locationsRaw.split(",").map((l) => l.trim()).filter(Boolean);

    const body = {
      name: name.trim(),
      type: mode,
      keywords: mode === "direct" ? keywords : [],
      locations: mode === "cold" ? locations : [],
      niches: mode === "cold" ? selectedNiches : [],
      sources,
      frequency,
      max_results: maxResults,
      is_paused: initial?.is_paused ?? false,
    };

    if (initial) {
      await update.mutateAsync({ id: initial.id, body });
    } else {
      await create.mutateAsync(body);
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <Card
        className="w-[640px] max-h-[85vh] overflow-auto p-5 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-[14px] font-semibold text-[var(--color-text-primary)]">
            {initial ? "Edit saved search" : "New saved search"}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Mode tabs — disabled when editing because you can't change a
            saved-search's type without invalidating its history. */}
        <div className="flex gap-1 p-0.5 bg-[var(--color-surface-raised)] rounded-[var(--radius-sm)]">
          <ModeTab
            active={mode === "direct"}
            disabled={!!initial && initial.type !== "direct"}
            onClick={() => changeMode("direct")}
            icon={<Briefcase className="w-3.5 h-3.5" />}
            title="Direct leads"
            subtitle="Jobs to apply to"
          />
          <ModeTab
            active={mode === "cold"}
            disabled={!!initial && initial.type !== "cold"}
            onClick={() => changeMode("cold")}
            icon={<Users className="w-3.5 h-3.5" />}
            title="Cold outreach"
            subtitle="Businesses to sell to"
          />
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          {/* Name — same for both modes */}
          <Field label="Name">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={
                mode === "direct"
                  ? "e.g. React jobs Tunisia"
                  : "e.g. Plumbers in Austin"
              }
              required
              className="h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)] w-full"
            />
          </Field>

          {/* Direct mode — Keywords */}
          {mode === "direct" && (
            <Field
              label="Keywords (comma-separated)"
              hint="What roles to search for. Each keyword is run separately, results merge."
            >
              <input
                value={keywordsRaw}
                onChange={(e) => setKeywordsRaw(e.target.value)}
                placeholder="react developer, next.js, fullstack"
                className="h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)] w-full"
              />
            </Field>
          )}

          {/* Cold mode — Locations + Niches */}
          {mode === "cold" && (
            <>
              <Field
                label="Locations (comma-separated)"
                hint="Cities you can serve. Each location runs as a separate scrape."
              >
                <input
                  value={locationsRaw}
                  onChange={(e) => setLocationsRaw(e.target.value)}
                  placeholder="Austin, TX · Houston, TX · Dallas, TX"
                  className="h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)] w-full"
                />
              </Field>

              <Field
                label={`Niches (${selectedNiches.length} selected)`}
                hint="Pick what kinds of businesses to find. We use a curated list with proven outreach pain-points."
              >
                {niches.isLoading ? (
                  <div className="text-[12px] text-[var(--color-text-tertiary)]">Loading niches…</div>
                ) : Object.keys(nichesByCategory).length === 0 ? (
                  <div className="text-[12px] text-[var(--color-text-tertiary)]">No niches available.</div>
                ) : (
                  <div className="flex flex-col gap-2">
                    {Object.entries(nichesByCategory).map(([category, list]) => (
                      <div key={category}>
                        <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium mb-1">
                          {category}
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {(list as any[]).map((n) => {
                            const active = selectedNiches.includes(n.key);
                            return (
                              <button
                                key={n.key}
                                type="button"
                                onClick={() => toggleNiche(n.key)}
                                className={clsx(
                                  "h-7 px-2.5 text-[11px] rounded-[var(--radius-sm)] border transition-colors",
                                  active
                                    ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)] border-[var(--color-accent)]"
                                    : "text-[var(--color-text-secondary)] border-[var(--color-border)] hover:border-[var(--color-border-strong)]",
                                )}
                              >
                                {n.label}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={() => {
                        const all = (niches.data?.niches ?? []).map((n) => n.key);
                        if (selectedNiches.length === all.length) {
                          setSelectedNiches([]);
                        } else {
                          setSelectedNiches(all);
                        }
                      }}
                      className="self-start text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] font-medium mt-1"
                    >
                      {selectedNiches.length === (niches.data?.niches.length ?? 0)
                        ? "Clear all"
                        : "Select all niches"}
                    </button>
                  </div>
                )}
              </Field>
            </>
          )}

          {/* Sources — different list per mode */}
          <Field label="Sources">
            <div className="flex flex-wrap gap-1">
              {(mode === "direct" ? DIRECT_SOURCES : COLD_SOURCES).map((s) => {
                const active = sources.includes(s);
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => toggleSource(s)}
                    className={clsx(
                      "h-7 px-2.5 text-[11px] rounded-[var(--radius-sm)] border transition-colors",
                      active
                        ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)] border-[var(--color-accent)]"
                        : "text-[var(--color-text-secondary)] border-[var(--color-border)] hover:border-[var(--color-border-strong)]",
                    )}
                  >
                    {s}
                  </button>
                );
              })}
            </div>
          </Field>

          {/* Frequency + Max results */}
          <div className="grid grid-cols-2 gap-3">
            <Field label="Frequency">
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value)}
                className="h-8 px-2 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)] w-full"
              >
                {FREQUENCIES.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </Field>
            <Field label="Max results">
              <input
                type="number"
                min={1}
                max={500}
                value={maxResults}
                onChange={(e) => setMaxResults(parseInt(e.target.value) || 50)}
                className="h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)] w-full"
              />
            </Field>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose} disabled={isPending}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={isPending || !canSubmit}>
              {isPending ? "Saving…" : initial ? "Save changes" : "Create"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

function ModeTab({
  active, disabled, onClick, icon, title, subtitle,
}: {
  active: boolean;
  disabled: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={clsx(
        "flex-1 flex items-start gap-2 px-3 py-2 rounded-[var(--radius-sm)] text-left transition-colors",
        active
          ? "bg-[var(--color-bg)] shadow-sm"
          : "hover:bg-[var(--color-bg)]/40",
        disabled && "opacity-50 cursor-not-allowed",
      )}
    >
      <span
        className={clsx(
          "mt-0.5",
          active ? "text-[var(--color-accent)]" : "text-[var(--color-text-tertiary)]",
        )}
      >
        {icon}
      </span>
      <span className="flex flex-col leading-tight">
        <span
          className={clsx(
            "text-[12px] font-semibold",
            active ? "text-[var(--color-text-primary)]" : "text-[var(--color-text-secondary)]",
          )}
        >
          {title}
        </span>
        <span className="text-[10px] text-[var(--color-text-tertiary)]">{subtitle}</span>
      </span>
    </button>
  );
}

function Field({
  label, hint, children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
        {label}
      </label>
      {children}
      {hint && (
        <span className="text-[10px] text-[var(--color-text-tertiary)] leading-snug">
          {hint}
        </span>
      )}
    </div>
  );
}
