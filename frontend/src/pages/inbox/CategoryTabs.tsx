import clsx from "clsx";
import {
  Linkedin, Briefcase, MessageCircle, Building2, Globe2,
  MapPin, Twitter as TwitterIcon, Code2, Users,
} from "lucide-react";
import type { Opportunity } from "../../types/opportunity";

interface Props {
  items: Opportunity[];
  activeSource?: string;
  onSelect: (source?: string) => void;
}

/** Friendly display labels per source. Anything not in this map renders
 * as the raw source slug, capitalized. */
const SOURCE_LABELS: Record<string, string> = {
  linkedin: "LinkedIn",
  linkedin_posts: "LinkedIn Posts",
  reddit: "Reddit",
  indeed: "Indeed",
  twitter: "Twitter / X",
  remoteok: "RemoteOK",
  tanit: "Tanit Jobs",
  clutch: "Clutch",
  goodfirms: "GoodFirms",
  google_maps: "Google Maps",
  yelp: "Yelp",
  bbb: "BBB",
  yellowpages: "Yellow Pages",
  manta: "Manta",
};

const SOURCE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  linkedin: Linkedin,
  linkedin_posts: Linkedin,
  reddit: MessageCircle,
  indeed: Briefcase,
  twitter: TwitterIcon,
  remoteok: Code2,
  tanit: MapPin,
  clutch: Building2,
  goodfirms: Building2,
  google_maps: MapPin,
  yelp: Users,
  bbb: Building2,
  yellowpages: Globe2,
  manta: Globe2,
};

interface Tab {
  key: string | undefined;     // undefined = "All"
  label: string;
  count: number;
  icon?: React.ComponentType<{ className?: string }>;
}

/** Build the tab list from the visible items (already filtered by Type +
 * Priority in the parent). We always render "All" first, then each unique
 * source sorted by count descending so the busiest sources are easy to
 * grab. Sources with 0 results are hidden so the strip doesn't clutter
 * with dead options. */
function buildTabs(items: Opportunity[]): Tab[] {
  const counts = new Map<string, number>();
  for (const o of items) {
    counts.set(o.source, (counts.get(o.source) ?? 0) + 1);
  }
  const sourceTabs: Tab[] = Array.from(counts.entries())
    .filter(([, c]) => c > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([source, count]) => ({
      key: source,
      label: SOURCE_LABELS[source] ?? capitalize(source),
      count,
      icon: SOURCE_ICONS[source],
    }));

  return [
    { key: undefined, label: "All", count: items.length },
    ...sourceTabs,
  ];
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function CategoryTabs({ items, activeSource, onSelect }: Props) {
  const tabs = buildTabs(items);
  // Always render the bar when there's any data — gives the user a clear
  // "this is what category I'm looking at" label, and the strip auto-grows
  // as new sources start producing leads.
  if (tabs.length === 0) return null;

  return (
    <div className="border-b border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 overflow-x-auto">
      <div className="flex items-center gap-1.5 min-w-max">
        {tabs.map((tab) => {
          const isActive =
            (tab.key === undefined && !activeSource) ||
            tab.key === activeSource;
          const Icon = tab.icon;
          return (
            <button
              key={tab.key ?? "__all"}
              type="button"
              onClick={() => onSelect(tab.key)}
              className={clsx(
                "flex items-center gap-1.5 px-2.5 h-7 rounded-[var(--radius-sm)] text-[12px] transition-colors shrink-0",
                isActive
                  ? "bg-[var(--color-accent)] text-[#0A0A0B] font-medium"
                  : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-raised)]",
              )}
            >
              {Icon && <Icon className="w-3 h-3" />}
              <span>{tab.label}</span>
              <span
                className={clsx(
                  "tabular-nums px-1 py-0 rounded text-[10px] font-medium",
                  isActive
                    ? "bg-black/15 text-black/70"
                    : "bg-[var(--color-surface-raised)] text-[var(--color-text-tertiary)]",
                )}
              >
                {tab.count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
