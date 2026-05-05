import clsx from "clsx";
import { StatusDot, Pill } from "../../design/primitives";
import type { PulseSource } from "../../types/hub";

const LABEL: Record<string, string> = {
  reddit: "Reddit",
  linkedin: "LinkedIn Jobs",
  linkedin_posts: "LinkedIn Posts",
  indeed: "Indeed",
  twitter: "Twitter",
  clutch: "Clutch",
  goodfirms: "GoodFirms",
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
  src: PulseSource;
}

export function ScraperStatusCard({ src }: Props) {
  return (
    <div
      className={clsx(
        "p-3 rounded-[var(--radius-md)] border bg-[var(--color-surface)]",
        src.status === "error"
          ? "border-[var(--color-hot-soft)]"
          : "border-[var(--color-border)]",
      )}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <StatusDot status={src.status} />
        <span className="text-[12px] font-medium text-[var(--color-text-primary)] flex-1 truncate">
          {LABEL[src.source] ?? src.source}
        </span>
        {src.today_count > 0 && (
          <Pill tone="accent">{src.today_count}</Pill>
        )}
      </div>
      <div className="text-[11px] text-[var(--color-text-tertiary)] flex items-center justify-between">
        <span className="truncate">{src.label}</span>
        <span className="tabular-nums shrink-0 ml-2">{fmtAge(src.last_fetch)}</span>
      </div>
    </div>
  );
}
