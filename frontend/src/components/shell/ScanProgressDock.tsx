import { useState } from "react";
import { ChevronDown, ChevronUp, X, Activity, Check, AlertTriangle } from "lucide-react";
import clsx from "clsx";
import { useActiveScans, type ScanRecord } from "../../api/scans";

/** Floats bottom-right whenever any scan is `running` or `queued`.
 * Auto-disappears 5s after the last scan finishes. The progress bar reflects
 * the backend-emitted `progress` (0-100); `phase` is the current step.
 *
 * Renders the live tail of `logs[]` (last 8 lines) so the user can watch
 * exactly which source/keyword the pipeline is on right now. */
export function ScanProgressDock() {
  const { data } = useActiveScans();
  const [collapsed, setCollapsed] = useState(false);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const scans = data?.scans ?? [];
  const visible = scans
    .filter((s) => !dismissed.has(s.id))
    .filter((s) => {
      if (s.status === "running" || s.status === "queued") return true;
      // Keep recently-finished scans for 30s so the user sees the success state.
      if (!s.finished_at) return false;
      const age = Date.now() - new Date(s.finished_at).getTime();
      return age < 30_000;
    })
    .slice(0, 3);

  if (visible.length === 0) return null;

  return (
    <div className="fixed bottom-10 right-4 z-40 flex flex-col gap-2 w-[420px] max-w-[calc(100vw-2rem)]">
      {visible.map((scan) => (
        <ScanCard
          key={scan.id}
          scan={scan}
          collapsed={collapsed}
          onCollapse={() => setCollapsed((c) => !c)}
          onDismiss={() =>
            setDismissed((prev) => new Set(prev).add(scan.id))
          }
        />
      ))}
    </div>
  );
}

interface ScanCardProps {
  scan: ScanRecord;
  collapsed: boolean;
  onCollapse: () => void;
  onDismiss: () => void;
}

function ScanCard({ scan, collapsed, onCollapse, onDismiss }: ScanCardProps) {
  const isRunning = scan.status === "running" || scan.status === "queued";
  const isFailed = scan.status === "failed";
  const isDone = scan.status === "completed";
  const phase =
    scan.phase ||
    (scan.status === "queued" ? "Queued…" : scan.status === "running" ? "Running…" : scan.status);

  const tone = isFailed
    ? "border-[var(--color-hot)] bg-[var(--color-hot)]/10"
    : isDone
      ? "border-[var(--color-accent)] bg-[var(--color-accent)]/10"
      : "border-[var(--color-border)] bg-[var(--color-surface)]";

  const subtitle = scan.keywords.length
    ? scan.keywords.slice(0, 3).join(", ")
    : scan.locations.length
      ? `${scan.locations[0]}`
      : scan.type;

  return (
    <div
      className={clsx(
        "rounded-[var(--radius-md)] border p-3 shadow-lg backdrop-blur-md transition-colors",
        tone,
      )}
    >
      {/* Header row */}
      <div className="flex items-center gap-2 mb-2">
        <ScanIcon status={scan.status} />
        <div className="flex-1 min-w-0">
          <div className="text-[12px] font-semibold text-[var(--color-text-primary)] truncate">
            {scan.type === "cold" ? "Cold scan" : "Direct scan"} · {subtitle}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] truncate">
            {phase}
          </div>
        </div>
        <button
          type="button"
          onClick={onCollapse}
          className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]"
          aria-label={collapsed ? "Expand" : "Collapse"}
        >
          {collapsed ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]"
          aria-label="Dismiss"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-[var(--color-surface-raised)] rounded-full overflow-hidden mb-1">
        <div
          className={clsx(
            "h-full transition-all duration-500",
            isFailed ? "bg-[var(--color-hot)]" : "bg-[var(--color-accent)]",
          )}
          style={{ width: `${scan.progress}%` }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-[var(--color-text-tertiary)] tabular-nums mb-2">
        <span>{scan.progress}%</span>
        <span>
          {isRunning && scan.leads_found > 0 && (
            <>{scan.leads_found} found · </>
          )}
          {isDone && (
            <span className="text-[var(--color-accent)]">
              {scan.leads_found} leads
              {scan.emails_extracted > 0 && ` · ${scan.emails_extracted} emails`}
            </span>
          )}
          {isFailed && scan.error && (
            <span className="text-[var(--color-hot)]">{scan.error.slice(0, 40)}…</span>
          )}
        </span>
      </div>

      {/* Live log tail */}
      {!collapsed && scan.logs.length > 0 && (
        <div className="border-t border-[var(--color-border)] pt-2 max-h-[100px] overflow-y-auto">
          <ul className="space-y-0.5 text-[10px] font-mono text-[var(--color-text-secondary)]">
            {scan.logs.slice(-8).map((line, i) => (
              <li key={i} className="truncate" title={line}>
                {line}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ScanIcon({ status }: { status: ScanRecord["status"] }) {
  if (status === "completed") {
    return (
      <div className="w-5 h-5 rounded-full bg-[var(--color-accent)]/20 flex items-center justify-center">
        <Check className="w-3 h-3 text-[var(--color-accent)]" />
      </div>
    );
  }
  if (status === "failed") {
    return (
      <div className="w-5 h-5 rounded-full bg-[var(--color-hot)]/20 flex items-center justify-center">
        <AlertTriangle className="w-3 h-3 text-[var(--color-hot)]" />
      </div>
    );
  }
  return (
    <div className="w-5 h-5 rounded-full bg-[var(--color-accent)]/15 flex items-center justify-center">
      <Activity className="w-3 h-3 text-[var(--color-accent)] animate-pulse" />
    </div>
  );
}
