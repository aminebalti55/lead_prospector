import { Activity, AlertCircle, CheckCircle2, Plus, Loader2 } from "lucide-react";
import { Card, MoneyValue, Pill } from "../../design/primitives";
import { useHubActivity } from "../../api/hub";
import type { ActivityEvent } from "../../types/hub";

function fmtAge(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.floor(ms / 60_000);
  if (m < 1) return "now";
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

function EventIcon({ kind }: { kind: ActivityEvent["kind"] }) {
  const props = { className: "w-3.5 h-3.5", strokeWidth: 1.75 };
  switch (kind) {
    case "scan_running":
      return <Loader2 {...props} className="w-3.5 h-3.5 text-[var(--color-accent)] animate-spin" />;
    case "scan_completed":
      return <CheckCircle2 {...props} className="w-3.5 h-3.5 text-[var(--color-accent)]" />;
    case "scan_failed":
      return <AlertCircle {...props} className="w-3.5 h-3.5 text-[var(--color-hot)]" />;
    case "lead_added":
      return <Plus {...props} className="w-3.5 h-3.5 text-[var(--color-cool)]" />;
    default:
      return <Activity {...props} className="w-3.5 h-3.5" />;
  }
}

function EventRow({ e }: { e: ActivityEvent }) {
  let middle: React.ReactNode = null;

  if (e.kind === "scan_completed") {
    middle = (
      <span>
        Scan completed: <span className="text-[var(--color-text-primary)]">{(e.keywords || []).join(", ")}</span>
        {e.sources && e.sources.length > 0 && (
          <> on {e.sources.join(", ")}</>
        )} — caught {e.leads_found ?? 0} leads
      </span>
    );
  } else if (e.kind === "scan_running") {
    middle = (
      <span>
        Scanning: <span className="text-[var(--color-text-primary)]">{(e.keywords || []).join(", ")}</span>
      </span>
    );
  } else if (e.kind === "scan_failed") {
    middle = (
      <span>
        Scan failed: <span className="text-[var(--color-text-primary)]">{(e.keywords || []).join(", ")}</span>
        {e.error && <span className="text-[var(--color-hot)]"> — {e.error}</span>}
      </span>
    );
  } else if (e.kind === "lead_added") {
    middle = (
      <span className="flex items-center gap-1.5 min-w-0">
        <span className="truncate">New lead: <span className="text-[var(--color-text-primary)]">{e.title}</span></span>
        {e.source && <Pill tone="neutral">{e.source}</Pill>}
      </span>
    );
  }

  return (
    <div className="flex items-center gap-2.5 py-2 border-b border-[var(--color-border)] last:border-0 text-[12px] text-[var(--color-text-secondary)]">
      <EventIcon kind={e.kind} />
      <div className="flex-1 min-w-0 flex items-center gap-2">
        {middle}
      </div>
      {e.kind === "lead_added" && typeof e.value_usd === "number" && e.value_usd > 0 && (
        <MoneyValue usd={e.value_usd} size="sm" tone="accent" />
      )}
      <span className="text-[11px] text-[var(--color-text-tertiary)] tabular-nums shrink-0">
        {fmtAge(e.ts)}
      </span>
    </div>
  );
}

export function ActivityFeed() {
  const { data, isLoading } = useHubActivity(20);
  const events = data?.events ?? [];

  return (
    <Card className="p-4 flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
          Recent activity
        </span>
        <span className="text-[11px] text-[var(--color-text-tertiary)]">
          {events.length} events
        </span>
      </div>

      {isLoading && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">Loading…</div>
      )}

      {!isLoading && events.length === 0 && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">
          No activity yet. Run a scan to start the feed.
        </div>
      )}

      <div className="flex flex-col">
        {events.map((e) => (
          <EventRow key={e.id} e={e} />
        ))}
      </div>
    </Card>
  );
}
