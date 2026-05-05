import { StatusDot } from "../../design/primitives";

// Static placeholder — Plan 2 wires this to live scraper status via WebSocket.
const TICKERS: Array<{ source: string; status: "live" | "idle" | "error"; label: string }> = [
  { source: "reddit", status: "live", label: "scraping" },
  { source: "linkedin", status: "idle", label: "idle" },
  { source: "indeed", status: "idle", label: "idle" },
  { source: "tanit", status: "error", label: "blocked" },
  { source: "twitter", status: "idle", label: "idle" },
];

export function PulseBar() {
  return (
    <footer className="h-7 shrink-0 border-t border-[var(--color-border)] bg-[var(--color-surface)] flex items-center px-4 gap-5 text-[11px] text-[var(--color-text-tertiary)] select-none">
      {TICKERS.map((t) => (
        <span key={t.source} className="flex items-center gap-1.5">
          <StatusDot status={t.status} />
          <span className="text-[var(--color-text-secondary)] tabular-nums">{t.source}</span>
          <span>·</span>
          <span>{t.label}</span>
        </span>
      ))}
      <span className="ml-auto text-[var(--color-text-tertiary)]">
        last sync 2m ago
      </span>
    </footer>
  );
}
