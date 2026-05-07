import { useEffect, useMemo, useRef, useState } from "react";
import { X } from "lucide-react";
import clsx from "clsx";

export interface Suggestion {
  /** Stable key — duplicates suppressed. */
  value: string;
  /** Primary label shown in the suggestion row + the chip. */
  label: string;
  /** Optional subtitle — e.g. "Texas, US" under "Austin". */
  hint?: string;
}

interface Props {
  values: string[];
  onChange: (next: string[]) => void;
  /** Async resolver. Called on every keystroke after `debounceMs`. */
  onSearch?: (query: string) => Promise<Suggestion[]>;
  /** Static suggestions — useful when no remote API is needed. */
  staticSuggestions?: Suggestion[];
  placeholder?: string;
  /** Allow free-text entry (Enter key turns the typed string into a chip). */
  allowFreeText?: boolean;
  debounceMs?: number;
  /** Minimum query length before `onSearch` is called. Default 2. */
  minQueryLength?: number;
  ariaLabel?: string;
}

/** Chip multi-select with optional async autocomplete. Keeps the UX
 * consistent across the app (locations, keywords, niches if needed).
 *
 * Keyboard model:
 *   - Enter / Tab          add the typed string as a chip (when free-text)
 *                          OR pick the highlighted suggestion
 *   - ↑ / ↓                navigate suggestions
 *   - Esc                  close suggestion list
 *   - Backspace (empty)    remove the last chip
 *   - Click on a chip's X  remove that chip
 */
export function ChipMultiSelect({
  values,
  onChange,
  onSearch,
  staticSuggestions,
  placeholder = "",
  allowFreeText = true,
  debounceMs = 200,
  minQueryLength = 2,
  ariaLabel,
}: Props) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [highlight, setHighlight] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced async search.
  useEffect(() => {
    const q = query.trim();
    if (!q || q.length < minQueryLength) {
      setSuggestions(filterStatic(staticSuggestions, q, values));
      setLoading(false);
      return;
    }
    if (!onSearch && !staticSuggestions) {
      return;
    }
    if (!onSearch) {
      setSuggestions(filterStatic(staticSuggestions, q, values));
      return;
    }

    let cancelled = false;
    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const results = await onSearch(q);
        if (cancelled) return;
        setSuggestions(results.filter((r) => !values.includes(r.value)));
        setHighlight(0);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, debounceMs);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, debounceMs, onSearch, staticSuggestions, values, minQueryLength]);

  // Close on outside click.
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function addChip(value: string, label?: string) {
    const v = value.trim();
    if (!v) return;
    if (values.includes(v)) return;
    onChange([...values, v]);
    setQuery("");
    setSuggestions([]);
    setOpen(false);
    setHighlight(0);
    inputRef.current?.focus();
    void label; // label is informational only — chips display the value as their label
  }

  function removeChip(v: string) {
    onChange(values.filter((x) => x !== v));
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === "Tab") {
      // Pick highlighted suggestion if present, otherwise free-text fallback.
      const picked = suggestions[highlight];
      if (picked) {
        e.preventDefault();
        addChip(picked.value);
      } else if (allowFreeText && query.trim()) {
        e.preventDefault();
        addChip(query);
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setHighlight((h) => Math.min(h + 1, suggestions.length - 1));
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(0, h - 1));
      return;
    }
    if (e.key === "Escape") {
      setOpen(false);
      return;
    }
    if (e.key === "Backspace" && !query && values.length > 0) {
      // Remove the last chip when the input is empty.
      onChange(values.slice(0, -1));
    }
  }

  const showDropdown = open && (loading || suggestions.length > 0);

  return (
    <div ref={containerRef} className="relative">
      <div
        className="flex flex-wrap items-center gap-1 px-2 py-1.5 min-h-[36px] bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] focus-within:border-[var(--color-accent)] transition-colors"
        onClick={() => inputRef.current?.focus()}
      >
        {values.map((v) => (
          <Chip key={v} label={v} onRemove={() => removeChip(v)} />
        ))}
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={values.length === 0 ? placeholder : ""}
          aria-label={ariaLabel}
          className="flex-1 min-w-[140px] bg-transparent text-[13px] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none"
        />
      </div>

      {showDropdown && (
        <div className="absolute z-20 left-0 right-0 mt-1 max-h-[260px] overflow-y-auto bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-sm)] shadow-lg">
          {loading && (
            <div className="px-3 py-2 text-[12px] text-[var(--color-text-tertiary)]">
              Searching…
            </div>
          )}
          {!loading && suggestions.length === 0 && (
            <div className="px-3 py-2 text-[12px] text-[var(--color-text-tertiary)]">
              No matches
            </div>
          )}
          {suggestions.map((s, i) => (
            <button
              key={s.value}
              type="button"
              onClick={() => addChip(s.value, s.label)}
              onMouseEnter={() => setHighlight(i)}
              className={clsx(
                "w-full flex items-baseline gap-2 px-3 py-1.5 text-left transition-colors",
                i === highlight
                  ? "bg-[var(--color-surface-raised)]"
                  : "hover:bg-[var(--color-surface-raised)]/60",
              )}
            >
              <span className="text-[13px] text-[var(--color-text-primary)]">{s.label}</span>
              {s.hint && (
                <span className="text-[11px] text-[var(--color-text-tertiary)]">{s.hint}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function filterStatic(
  list: Suggestion[] | undefined,
  query: string,
  values: string[],
): Suggestion[] {
  if (!list) return [];
  const q = query.trim().toLowerCase();
  return list
    .filter((s) => !values.includes(s.value))
    .filter((s) => !q || s.label.toLowerCase().includes(q) || s.value.toLowerCase().includes(q))
    .slice(0, 12);
}

function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="flex items-center gap-1 px-2 h-6 rounded-[var(--radius-xs)] bg-[var(--color-accent)]/15 text-[var(--color-accent)] text-[12px] leading-none">
      {label}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        className="ml-0.5 hover:text-[var(--color-text-primary)]"
        aria-label={`Remove ${label}`}
      >
        <X className="w-3 h-3" />
      </button>
    </span>
  );
}
