import { ArrowUpRight } from "lucide-react";
import { Card, MoneyValue, Sparkline } from "../../design/primitives";

interface Props {
  label: string;
  usd: number;
  trend?: number[]; // optional sparkline series
  delta?: number;   // optional % change vs previous period
}

export function HeroStat({ label, usd, trend, delta }: Props) {
  return (
    <Card className="p-5 flex items-center gap-6">
      <div className="flex flex-col gap-1 min-w-0">
        <span className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
          {label}
        </span>
        <MoneyValue usd={usd} size="xl" tone="accent" abbreviate={false} />
        {delta !== undefined && (
          <span className="flex items-center gap-1 text-[11px] text-[var(--color-text-secondary)]">
            <ArrowUpRight className="w-3 h-3 text-[var(--color-accent)]" />
            <span className="tabular-nums">{(delta * 100).toFixed(1)}%</span>
            <span className="text-[var(--color-text-tertiary)]">vs last month</span>
          </span>
        )}
      </div>
      {trend && trend.length > 1 && (
        <div className="ml-auto">
          <Sparkline data={trend} width={140} height={42} />
        </div>
      )}
    </Card>
  );
}
