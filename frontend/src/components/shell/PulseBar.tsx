import { StatusDot } from "../../design/primitives";
import { usePulseStatus } from "../../api/hub";
import type { PulseSource } from "../../types/hub";

function fmtAge(iso: string | null): string {
  if (!iso) return "never";
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.floor(ms / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return `${h}h ago`;
}

// Show only the most informative slice of sources in the bar (running first,
// then errors, then any with today_count > 0, then a couple idle to fill).
function pickShown(sources: PulseSource[]): PulseSource[] {
  const live = sources.filter((s) => s.status === "live");
  const error = sources.filter((s) => s.status === "error");
  const active = sources.filter((s) => s.status === "idle" && s.today_count > 0);
  const filler = sources.filter((s) => s.status === "idle" && s.today_count === 0).slice(0, 3);
  const merged = [...live, ...error, ...active, ...filler];
  // Dedup by source name (keep first occurrence)
  const seen = new Set<string>();
  return merged.filter((s) => {
    if (seen.has(s.source)) return false;
    seen.add(s.source);
    return true;
  }).slice(0, 6);
}

export function PulseBar() {
  const { data } = usePulseStatus();
  const sources = data?.sources ?? [];
  const shown = pickShown(sources);

  // Most recent last_fetch across all sources for the right-side timestamp
  const lastSyncs = sources.map((s) => s.last_fetch).filter((x): x is string => !!x);
  const lastSync = lastSyncs.sort().slice(-1)[0] ?? null;

  return (
    <footer className="h-7 shrink-0 border-t border-[var(--color-border)] bg-[var(--color-surface)] flex items-center px-4 gap-5 text-[11px] text-[var(--color-text-tertiary)] select-none">
      {shown.length === 0 && (
        <span className="text-[var(--color-text-tertiary)]">No scrapers configured</span>
      )}
      {shown.map((s) => (
        <span key={s.source} className="flex items-center gap-1.5">
          <StatusDot status={s.status} />
          <span className="text-[var(--color-text-secondary)] tabular-nums">{s.source}</span>
          <span>·</span>
          <span>
            {s.label}
            {s.today_count > 0 && s.status !== "live" && (
              <span className="text-[var(--color-accent)]"> · {s.today_count} new</span>
            )}
          </span>
        </span>
      ))}
      <span className="ml-auto text-[var(--color-text-tertiary)]">
        last sync {fmtAge(lastSync)}
      </span>
    </footer>
  );
}
