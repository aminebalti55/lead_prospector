import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { EmptyState } from "../../components/EmptyState";
import { Button } from "../../components/Button";
import { useDirectLeads, useUpdateDirectLead } from "../../api/direct";
import {
  Search,
  ExternalLink,
  Building2,
  MapPin,
  Clock,
  Flame,
  Zap,
  LayoutGrid,
  List,
  ChevronDown,
} from "lucide-react";

type Lead = Record<string, unknown>;

const PRIORITY_STYLES: Record<string, { bg: string; text: string; border: string; label: string }> = {
  HOT: { bg: "bg-red-50", text: "text-red-600", border: "border-red-200", label: "HOT" },
  WARM: { bg: "bg-amber-50", text: "text-amber-600", border: "border-amber-200", label: "WARM" },
  COLD: { bg: "bg-slate-50", text: "text-slate-500", border: "border-slate-200", label: "COLD" },
};

const SOURCE_ICONS: Record<string, string> = {
  reddit: "🟠",
  indeed: "🔵",
  linkedin: "🔷",
  linkedin_posts: "📣",
  clutch: "🟢",
  goodfirms: "🟣",
  twitter: "🐦",
};

const STATUS_OPTIONS = ["new", "contacted", "replied", "meeting", "converted", "passed"];

export function DirectLeads() {
  const { data: leadsData, isLoading } = useDirectLeads();
  const updateLead = useUpdateDirectLead();
  const [filter, setFilter] = useState("");
  const [view, setView] = useState<"cards" | "table">("cards");
  const [sortBy, setSortBy] = useState<"relevance" | "date" | "priority">("relevance");

  const allLeads: Lead[] = leadsData?.leads || [];

  // Filter
  const leads = allLeads.filter((lead) => {
    if (!filter) return true;
    const q = filter.toLowerCase();
    return (
      String(lead.Title || "").toLowerCase().includes(q) ||
      String(lead.Company || "").toLowerCase().includes(q) ||
      String(lead.Description || "").toLowerCase().includes(q) ||
      String(lead.Source || "").toLowerCase().includes(q) ||
      String(lead.Location || "").toLowerCase().includes(q) ||
      String(lead.Matched_Skills || "").toLowerCase().includes(q)
    );
  });

  // Sort
  const sorted = [...leads].sort((a, b) => {
    if (sortBy === "relevance") return Number(b.Relevance_Score || 0) - Number(a.Relevance_Score || 0);
    if (sortBy === "priority") {
      const order: Record<string, number> = { HOT: 0, WARM: 1, COLD: 2 };
      return (order[String(a.Priority)] ?? 3) - (order[String(b.Priority)] ?? 3);
    }
    return String(b.Posted_Date || "").localeCompare(String(a.Posted_Date || ""));
  });

  return (
    <div>
      <PageHeader title="Direct Leads" subtitle={`${allLeads.length} leads found`}>
        <Link to="/direct/scans/new">
          <Button>New Scan</Button>
        </Link>
      </PageHeader>

      {/* Toolbar */}
      <div className="flex items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-md">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
          <input
            type="text"
            placeholder="Search leads..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full text-sm border border-border rounded-lg pl-9 pr-3 py-2 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
          />
        </div>

        <div className="flex items-center gap-1.5 text-sm text-text-secondary">
          <span className="font-medium text-[13px]">Sort:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="text-[13px] font-medium border border-border rounded-lg px-2.5 py-1.5 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors"
          >
            <option value="relevance">Relevance</option>
            <option value="priority">Priority</option>
            <option value="date">Newest</option>
          </select>
        </div>

        <div className="flex border border-border rounded-lg overflow-hidden">
          <button
            onClick={() => setView("cards")}
            className={`p-1.5 transition-colors ${view === "cards" ? "bg-primary text-white" : "bg-surface text-text-secondary hover:bg-bg"}`}
          >
            <LayoutGrid size={16} />
          </button>
          <button
            onClick={() => setView("table")}
            className={`p-1.5 transition-colors ${view === "table" ? "bg-primary text-white" : "bg-surface text-text-secondary hover:bg-bg"}`}
          >
            <List size={16} />
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-text-secondary text-sm font-medium p-8">Loading...</div>
      ) : sorted.length === 0 ? (
        <EmptyState
          message={filter ? "No leads match your search." : "No direct leads found."}
          action={!filter ? { label: "Start your first scan", href: "/direct/scans/new" } : undefined}
        />
      ) : view === "cards" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sorted.map((lead) => (
            <LeadCard key={String(lead.Lead_ID)} lead={lead} updateLead={updateLead} />
          ))}
        </div>
      ) : (
        <TableView leads={sorted} updateLead={updateLead} />
      )}
    </div>
  );
}

function LeadCard({ lead, updateLead }: { lead: Lead; updateLead: ReturnType<typeof useUpdateDirectLead> }) {
  const priority = String(lead.Priority || "COLD");
  const style = PRIORITY_STYLES[priority] || PRIORITY_STYLES.COLD;
  const score = Number(lead.Relevance_Score || 0);
  const source = String(lead.Source || "");
  const title = String(lead.Title || "Untitled");
  const company = String(lead.Company || "");
  const location = String(lead.Location || "");
  const description = String(lead.Description || "");
  const url = String(lead.URL || "");
  const leadId = String(lead.Lead_ID || "");
  const budgetSignal = String(lead.Budget_Signal || "");
  const urgencySignal = String(lead.Urgency_Signal || "");
  const skills = String(lead.Matched_Skills || "").split(",").map((s) => s.trim()).filter(Boolean);
  const postedDate = String(lead.Posted_Date || "");
  const outreachStatus = String(lead.Outreach_Status || "new");

  const scoreColor = score >= 70 ? "text-red-500" : score >= 40 ? "text-amber-500" : "text-slate-400";

  return (
    <div className={`bg-surface rounded-xl border ${style.border} shadow-[--shadow-sm] hover:shadow-[--shadow-md] transition-all duration-200 flex flex-col`}>
      {/* Header */}
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between gap-2 mb-2.5">
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-bold ${style.bg} ${style.text} border ${style.border}`}>
              {style.label}
            </span>
            <span className="text-[11px] text-text-tertiary font-medium">
              {SOURCE_ICONS[source] || "📋"} {source}
            </span>
          </div>
          <div className={`text-lg font-bold ${scoreColor} tabular-nums`}>{score}</div>
        </div>

        {/* Title */}
        <Link
          to={`/direct/leads/${leadId}`}
          className="text-[14px] font-semibold text-text-primary hover:text-primary leading-snug line-clamp-2 transition-colors"
        >
          {title}
        </Link>

        {/* Company & Location */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-[12px] text-text-secondary">
          {company && (
            <span className="inline-flex items-center gap-1">
              <Building2 size={12} className="text-text-tertiary" />
              <span className="font-medium">{company}</span>
            </span>
          )}
          {location && (
            <span className="inline-flex items-center gap-1">
              <MapPin size={12} className="text-text-tertiary" />
              {location}
            </span>
          )}
          {postedDate && (
            <span className="inline-flex items-center gap-1">
              <Clock size={12} className="text-text-tertiary" />
              {formatDate(postedDate)}
            </span>
          )}
        </div>
      </div>

      {/* Description */}
      {description && description !== title && (
        <div className="px-4 pb-3">
          <p className="text-[12px] text-text-secondary leading-relaxed line-clamp-3">
            {description}
          </p>
        </div>
      )}

      {/* Tags */}
      <div className="px-4 pb-3 flex flex-wrap gap-1.5">
        {budgetSignal && (
          <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-primary-light text-primary border border-primary/20">
            <Flame size={10} /> {budgetSignal}
          </span>
        )}
        {urgencySignal && (
          <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-red-50 text-red-600 border border-red-200">
            <Zap size={10} /> {urgencySignal}
          </span>
        )}
        {skills.map((s) => (
          <span key={s} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-success-light text-success border border-success/20">
            {s}
          </span>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-auto px-4 py-3 border-t border-border/50 flex items-center justify-between">
        <select
          value={outreachStatus}
          onChange={(e) => updateLead.mutate({ leadId, data: { Outreach_Status: e.target.value } })}
          className="text-[11px] font-semibold border border-border rounded-md px-2 py-1 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary hover:text-primary-hover transition-colors"
          >
            Open <ExternalLink size={11} />
          </a>
        )}
      </div>
    </div>
  );
}

function TableView({ leads, updateLead }: { leads: Lead[]; updateLead: ReturnType<typeof useUpdateDirectLead> }) {
  return (
    <div className="bg-surface rounded-xl border border-border overflow-auto shadow-[--shadow-sm]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-bg/50">
            <th className="px-3 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Priority</th>
            <th className="px-3 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Score</th>
            <th className="px-3 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Source</th>
            <th className="px-3 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Title</th>
            <th className="px-3 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Company</th>
            <th className="px-3 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Location</th>
            <th className="px-3 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Skills</th>
            <th className="px-3 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => {
            const priority = String(lead.Priority || "COLD");
            const style = PRIORITY_STYLES[priority] || PRIORITY_STYLES.COLD;
            const leadId = String(lead.Lead_ID || "");
            const skills = String(lead.Matched_Skills || "").split(",").map((s) => s.trim()).filter(Boolean);
            return (
              <tr key={leadId} className="border-b border-border last:border-0 hover:bg-bg/50 transition-colors">
                <td className="px-3 py-2.5">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-bold ${style.bg} ${style.text} border ${style.border}`}>
                    {style.label}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-[13px] font-bold text-text-primary">{String(lead.Relevance_Score || 0)}</td>
                <td className="px-3 py-2.5 text-[13px] font-medium text-text-secondary">
                  {SOURCE_ICONS[String(lead.Source)] || ""} {String(lead.Source || "")}
                </td>
                <td className="px-3 py-2.5">
                  <Link to={`/direct/leads/${leadId}`} className="text-[13px] text-primary hover:text-primary-hover font-semibold truncate block max-w-[250px] transition-colors">
                    {String(lead.Title || "Untitled")}
                  </Link>
                </td>
                <td className="px-3 py-2.5 text-[13px] font-medium text-text-primary">{String(lead.Company || "")}</td>
                <td className="px-3 py-2.5 text-[13px] text-text-secondary">{String(lead.Location || "")}</td>
                <td className="px-3 py-2.5">
                  <div className="flex gap-1 flex-wrap max-w-[160px]">
                    {skills.slice(0, 3).map((s) => (
                      <span key={s} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-success-light text-success border border-success/20">{s}</span>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <select
                    value={String(lead.Outreach_Status || "new")}
                    onChange={(e) => updateLead.mutate({ leadId, data: { Outreach_Status: e.target.value } })}
                    className="text-[11px] font-semibold border border-border rounded-md px-2 py-1 bg-surface text-text-primary cursor-pointer"
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffH = Math.floor(diffMs / 3600000);
    if (diffH < 1) return "Just now";
    if (diffH < 24) return `${diffH}h ago`;
    const diffD = Math.floor(diffH / 24);
    if (diffD < 7) return `${diffD}d ago`;
    return d.toLocaleDateString();
  } catch {
    return dateStr;
  }
}
