import { Play, Pause, AlertCircle } from "lucide-react";
import { Card, MoneyValue, Sparkline, StatusDot, Button } from "../../design/primitives";
import { useRunSource, useToggleSource } from "../../api/sources";
import type { SourceSummary } from "../../types/source";

const LABEL: Record<string, string> = {
  reddit: "Reddit",
  linkedin: "LinkedIn Jobs",
  linkedin_posts: "LinkedIn Posts",
  indeed: "Indeed",
  twitter: "Twitter",
  clutch: "Clutch",
  goodfirms: "GoodFirms",
  tanit: "Tanit Jobs",
  google_maps: "Google Maps",
  yelp: "Yelp",
  bbb: "BBB",
  yellowpages: "YellowPages",
  manta: "Manta",
};

function fmtAge(iso: string | null): string {
  if (!iso) return "never";
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.floor(ms / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

interface Props {
  src: SourceSummary;
}

export function SourceCard({ src }: Props) {
  const runSource = useRunSource();
  const toggleSource = useToggleSource();

  const handleRun = () => {
    runSource.mutate(src.source, {
      onError: (err: any) => {
        // Show backend error message via alert (toast lib not yet introduced)
        const msg = err?.message || "Run failed";
        alert(`${LABEL[src.source] ?? src.source}: ${msg}`);
      },
    });
  };

  return (
    <Card className={`p-4 flex flex-col gap-3 ${src.enabled ? "" : "opacity-60"}`}>
      {/* Header row */}
      <div className="flex items-start gap-2">
        <StatusDot status={src.status} className="mt-1" />
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-medium text-[var(--color-text-primary)] truncate">
            {LABEL[src.source] ?? src.source}
          </div>
          <div className="text-[11px] text-[var(--color-text-tertiary)] flex items-center gap-1">
            <span>{src.label}</span>
            <span>·</span>
            <span>{fmtAge(src.last_fetch)}</span>
          </div>
        </div>
        {!src.enabled && (
          <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] bg-[var(--color-surface-raised)] px-1.5 py-0.5 rounded-[var(--radius-sm)]">
            paused
          </span>
        )}
      </div>

      {/* Big number row */}
      <div className="flex items-end justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
            Today
          </div>
          {src.today_value_usd > 0 ? (
            <MoneyValue usd={src.today_value_usd} size="lg" tone="accent" />
          ) : (
            <div className="text-lg font-mono tabular-nums text-[var(--color-text-secondary)]">
              {src.today_count} new
            </div>
          )}
        </div>
        <Sparkline data={src.seven_day_series} width={100} height={32} />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button
          variant="primary"
          size="sm"
          onClick={handleRun}
          disabled={runSource.isPending || src.status === "live"}
        >
          <Play className="w-3 h-3" />
          {runSource.isPending ? "Starting…" : "Run Now"}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => toggleSource.mutate(src.source)}
          disabled={toggleSource.isPending}
        >
          {src.enabled ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
          {src.enabled ? "Pause" : "Resume"}
        </Button>
        {src.last_error && (
          <span className="ml-auto flex items-center gap-1 text-[11px] text-[var(--color-hot)]" title={src.last_error}>
            <AlertCircle className="w-3 h-3" /> error
          </span>
        )}
      </div>
    </Card>
  );
}
