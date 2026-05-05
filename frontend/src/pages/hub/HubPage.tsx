import { useHubStats } from "../../api/hub";
import { HeroStat } from "./HeroStat";
import { HottestOpps } from "./HottestOpps";
import { ScraperStatusGrid } from "./ScraperStatusGrid";
import { ActivityFeed } from "./ActivityFeed";

export function HubPage() {
  const { data: stats } = useHubStats();
  const pipeline = stats?.pipeline_total_usd ?? 0;
  const won = stats?.won_total_usd ?? 0;
  const week = stats?.this_week_usd ?? 0;
  const responseRate = stats?.response_rate ?? 0;

  return (
    <div className="p-6 flex flex-col gap-4 w-full">
      {/* Hero row: 1 big + 3 small */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
        <div className="lg:col-span-2">
          <HeroStat label="Pipeline this month" usd={pipeline} />
        </div>
        <HeroStat label="This week" usd={week} />
        <HeroStat label="Won this month" usd={won} />
      </div>

      {/* Secondary metric row */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
        <div className="lg:col-span-1 p-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
          <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium mb-1">
            Response rate
          </div>
          <div className="text-2xl font-mono tabular-nums text-[var(--color-text-primary)] font-medium">
            {(responseRate * 100).toFixed(1)}%
          </div>
        </div>
        <div className="lg:col-span-3 grid grid-cols-3 gap-3">
          <Tiny label="Total opps" value={stats?.count_total ?? 0} />
          <Tiny label="In pipeline" value={stats?.count_pipeline ?? 0} />
          <Tiny label="Won" value={stats?.count_won ?? 0} />
        </div>
      </div>

      {/* Body: hottest + status side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <HottestOpps />
        <ScraperStatusGrid />
      </div>

      {/* Activity feed full width */}
      <ActivityFeed />
    </div>
  );
}

function Tiny({ label, value }: { label: string; value: number }) {
  return (
    <div className="p-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
      <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium mb-1">
        {label}
      </div>
      <div className="text-2xl font-mono tabular-nums text-[var(--color-text-primary)] font-medium">
        {value}
      </div>
    </div>
  );
}
