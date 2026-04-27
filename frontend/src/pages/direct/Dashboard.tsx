import { PageHeader } from "../../components/PageHeader";
import { StatCard } from "../../components/StatCard";
import { EmptyState } from "../../components/EmptyState";
import { useDirectStats } from "../../api/shared";
import { useDirectLeads } from "../../api/direct";
import { CalendarPlus, Flame, Users, Target } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const TOOLTIP_STYLE = {
  background: "#FFFFFF",
  border: "1px solid #E2E8F0",
  borderRadius: "8px",
  boxShadow: "0 4px 12px rgba(15,23,42,0.08)",
  fontSize: "13px",
  fontWeight: 500,
};

export function DirectDashboard() {
  const { data: stats, isLoading: statsLoading } = useDirectStats();
  const { data: leadsData, isLoading: leadsLoading } = useDirectLeads();

  const leads: Record<string, unknown>[] = leadsData?.leads || [];
  const hotCount = leads.filter(
    (l) => String(l.Priority || "").toUpperCase() === "HOT"
  ).length;
  const today = new Date().toISOString().split("T")[0];
  const newToday = leads.filter((l) =>
    String(l.Posted_Date || "").startsWith(today)
  ).length;

  const avgRelevance =
    leads.length > 0
      ? Math.round(
          leads.reduce((s, l) => s + Number(l.Relevance_Score || 0), 0) / leads.length
        )
      : 0;

  const sourceCounts: Record<string, number> = {};
  leads.forEach((l) => {
    const src = String(l.Source || "unknown");
    sourceCounts[src] = (sourceCounts[src] || 0) + 1;
  });
  const sourceData = Object.entries(sourceCounts).map(([name, count]) => ({ name, count }));

  const skillCounts: Record<string, number> = {};
  leads.forEach((l) => {
    const skills = String(l.Matched_Skills || "").split(",").map((s) => s.trim()).filter(Boolean);
    skills.forEach((s) => { skillCounts[s] = (skillCounts[s] || 0) + 1; });
  });
  const skillData = Object.entries(skillCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([name, count]) => ({ name, count }));

  if (statsLoading || leadsLoading) {
    return <div className="text-text-secondary text-sm p-8 font-medium">Loading...</div>;
  }

  if (!leads.length) {
    return (
      <div>
        <PageHeader title="Direct Leads Dashboard" />
        <EmptyState
          message="No direct leads yet."
          action={{ label: "Start your first scan", href: "/direct/scans/new" }}
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Direct Leads Dashboard" subtitle="Real-time overview of your direct lead pipeline" />

      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="New Today" value={newToday} icon={<CalendarPlus size={18} />} />
        <StatCard label="Hot Opportunities" value={hotCount} color="text-hot" icon={<Flame size={18} />} />
        <StatCard label="Total Leads" value={stats?.total_leads ?? leads.length} icon={<Users size={18} />} />
        <StatCard label="Avg Relevance" value={avgRelevance} icon={<Target size={18} />} />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {sourceData.length > 0 && (
          <div className="bg-surface rounded-xl border border-border p-6 shadow-[--shadow-sm]">
            <h3 className="text-sm font-semibold text-text-primary mb-5">Leads by Source</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={sourceData}>
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#475569" }} axisLine={{ stroke: "#E2E8F0" }} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="count" fill="#4F46E5" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {skillData.length > 0 && (
          <div className="bg-surface rounded-xl border border-border p-6 shadow-[--shadow-sm]">
            <h3 className="text-sm font-semibold text-text-primary mb-5">Top Matched Skills</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={skillData} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 12, fill: "#475569" }} axisLine={{ stroke: "#E2E8F0" }} tickLine={false} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: "#475569", fontWeight: 500 }} width={80} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="count" fill="#059669" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
