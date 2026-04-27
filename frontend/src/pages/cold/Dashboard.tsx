import { PageHeader } from "../../components/PageHeader";
import { StatCard } from "../../components/StatCard";
import { EmptyState } from "../../components/EmptyState";
import { useColdStats } from "../../api/shared";
import { Users, Flame, ThermometerSun, TrendingUp } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

const PIE_COLORS = ["#DC2626", "#D97706", "#94A3B8"];

export function ColdDashboard() {
  const { data, isLoading } = useColdStats();

  if (isLoading)
    return (
      <div className="text-text-secondary text-sm p-8 font-medium">Loading...</div>
    );

  if (!data)
    return (
      <EmptyState
        message="No data yet."
        action={{ label: "Start your first run", href: "/cold/runs/new" }}
      />
    );

  const pieData = [
    { name: "Hot", value: data.hot_leads || 0 },
    { name: "Warm", value: data.warm_leads || 0 },
    { name: "Cold", value: data.cold_leads || 0 },
  ].filter((d) => d.value > 0);

  const sourceData = (data.leads_by_source || []).map(
    (s: { source: string; count: number }) => ({ name: s.source, count: s.count })
  );

  return (
    <div>
      <PageHeader title="Cold Outreach Dashboard" subtitle="Overview of your cold outreach pipeline" />

      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Leads" value={data.total_leads || 0} icon={<Users size={18} />} />
        <StatCard label="Hot Leads" value={data.hot_leads || 0} color="text-hot" icon={<Flame size={18} />} />
        <StatCard label="Warm Leads" value={data.warm_leads || 0} color="text-warning" icon={<ThermometerSun size={18} />} />
        <StatCard label="Avg Score" value={data.avg_score || 0} icon={<TrendingUp size={18} />} />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {sourceData.length > 0 && (
          <div className="bg-surface rounded-xl border border-border p-6 shadow-[--shadow-sm]">
            <h3 className="text-sm font-semibold text-text-primary mb-5">
              Leads by Source
            </h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={sourceData}>
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#475569" }} axisLine={{ stroke: "#E2E8F0" }} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "#FFFFFF",
                    border: "1px solid #E2E8F0",
                    borderRadius: "8px",
                    boxShadow: "0 4px 12px rgba(15,23,42,0.08)",
                    fontSize: "13px",
                    fontWeight: 500,
                  }}
                />
                <Bar dataKey="count" fill="#4F46E5" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {pieData.length > 0 && (
          <div className="bg-surface rounded-xl border border-border p-6 shadow-[--shadow-sm]">
            <h3 className="text-sm font-semibold text-text-primary mb-5">
              Priority Distribution
            </h3>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  outerRadius={85}
                  innerRadius={45}
                  dataKey="value"
                  strokeWidth={2}
                  stroke="#FFFFFF"
                  label={({ name, value }: { name: string; value: number }) =>
                    `${name}: ${value}`
                  }
                >
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "#FFFFFF",
                    border: "1px solid #E2E8F0",
                    borderRadius: "8px",
                    boxShadow: "0 4px 12px rgba(15,23,42,0.08)",
                    fontSize: "13px",
                    fontWeight: 500,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
