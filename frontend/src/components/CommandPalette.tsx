import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useHotkeys } from "react-hotkeys-hook";
import {
  Search, Briefcase, Users, Inbox as InboxIcon, Layers,
  Radio, Send, FileText, Settings as SettingsIcon, Activity,
  CornerDownLeft, ArrowUp, ArrowDown,
} from "lucide-react";
import clsx from "clsx";
import { useOpportunities } from "../api/opportunities";
import type { Opportunity } from "../types/opportunity";

/** Global Cmd/Ctrl+K command palette.
 *
 * Sources of results:
 *  1. Pages — instant nav to Hub / Inbox / Pipeline / Sources / Outreach /
 *     Templates / Settings.
 *  2. Opportunities — fuzzy match against title / company / source / location.
 *
 * Keyboard:
 *  - Cmd/Ctrl+K        toggles open
 *  - Esc               closes
 *  - ↑ / ↓             move selection
 *  - Enter             open selected result
 */

interface PageResult {
  kind: "page";
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface OpportunityResult {
  kind: "opportunity";
  opp: Opportunity;
}

type Result = PageResult | OpportunityResult;

const PAGES: PageResult[] = [
  { kind: "page", label: "Hub",       path: "/hub",       icon: Activity },
  { kind: "page", label: "Inbox",     path: "/inbox",     icon: InboxIcon },
  { kind: "page", label: "Pipeline",  path: "/pipeline",  icon: Layers },
  { kind: "page", label: "Sources",   path: "/sources",   icon: Radio },
  { kind: "page", label: "Outreach",  path: "/outreach",  icon: Send },
  { kind: "page", label: "Templates", path: "/templates", icon: FileText },
  { kind: "page", label: "Settings",  path: "/settings",  icon: SettingsIcon },
];

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CommandPalette({ open, onOpenChange }: Props) {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [highlight, setHighlight] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  // Reduce noise: only fetch leads while the palette is open. Once it closes
  // the cached query goes stale and refetches next open.
  const { data } = useOpportunities(open ? { sort: "score", limit: 200 } : { sort: "score", limit: 0 });

  // Auto-focus on open + reset state
  useEffect(() => {
    if (open) {
      setQ("");
      setHighlight(0);
      // Defer to ensure the input is in the DOM
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  const results: Result[] = useMemo(() => {
    const opps = data?.opportunities ?? [];
    const ql = q.trim().toLowerCase();

    if (!ql) {
      // Empty query → just show all pages, no opps (clean default).
      return PAGES;
    }

    const pageHits = PAGES.filter((p) => p.label.toLowerCase().includes(ql));

    // Fuzzy-ish: substring match across the most-relevant fields, ranked by
    // which field hit. Title/company > source/location.
    const oppHits: { opp: Opportunity; score: number }[] = [];
    for (const o of opps) {
      const title = (o.title || "").toLowerCase();
      const company = (o.company_name || "").toLowerCase();
      const source = (o.source || "").toLowerCase();
      const location = (o.location || "").toLowerCase();
      let score = 0;
      if (title.includes(ql)) score += 4;
      if (company.includes(ql)) score += 3;
      if (source.includes(ql)) score += 2;
      if (location.includes(ql)) score += 1;
      if (score > 0) oppHits.push({ opp: o, score });
    }
    oppHits.sort((a, b) => b.score - a.score);

    return [
      ...pageHits,
      ...oppHits.slice(0, 30).map<OpportunityResult>(({ opp }) => ({
        kind: "opportunity",
        opp,
      })),
    ];
  }, [q, data]);

  // Clamp highlight whenever results change.
  useEffect(() => {
    if (highlight >= results.length) setHighlight(Math.max(0, results.length - 1));
  }, [results.length, highlight]);

  function activate(result: Result) {
    if (result.kind === "page") {
      navigate(result.path);
    } else {
      navigate(`/inbox?opp=${encodeURIComponent(result.opp.id)}`);
    }
    onOpenChange(false);
  }

  // Inside-modal arrow / enter / escape — bound only while open.
  useHotkeys(
    "esc",
    () => onOpenChange(false),
    { enabled: open, enableOnFormTags: true, preventDefault: true },
  );
  useHotkeys(
    "down",
    () => setHighlight((h) => Math.min(h + 1, results.length - 1)),
    { enabled: open, enableOnFormTags: true, preventDefault: true },
    [results.length],
  );
  useHotkeys(
    "up",
    () => setHighlight((h) => Math.max(0, h - 1)),
    { enabled: open, enableOnFormTags: true, preventDefault: true },
  );
  useHotkeys(
    "enter",
    () => {
      const r = results[highlight];
      if (r) activate(r);
    },
    { enabled: open, enableOnFormTags: true, preventDefault: true },
    [results, highlight],
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center bg-black/60 pt-[15vh]"
      onClick={() => onOpenChange(false)}
    >
      <div
        className="w-[640px] max-w-[calc(100vw-2rem)] bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-md)] shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-2 px-3 h-11 border-b border-[var(--color-border)]">
          <Search className="w-4 h-4 text-[var(--color-text-tertiary)] shrink-0" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setHighlight(0);
            }}
            placeholder="Search jobs, companies, pages…"
            className="flex-1 bg-transparent text-[14px] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none"
          />
          <kbd className="text-[10px] text-[var(--color-text-tertiary)] border border-[var(--color-border)] rounded px-1.5 py-0.5">
            esc
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[50vh] overflow-y-auto">
          {results.length === 0 && (
            <div className="px-4 py-8 text-center text-[12px] text-[var(--color-text-tertiary)]">
              No results for &ldquo;{q}&rdquo;
            </div>
          )}
          {results.map((r, idx) => (
            <ResultRow
              key={r.kind === "page" ? r.path : r.opp.id}
              result={r}
              active={idx === highlight}
              onClick={() => activate(r)}
              onHover={() => setHighlight(idx)}
            />
          ))}
        </div>

        {/* Footer hints */}
        <div className="flex items-center gap-3 px-3 h-7 border-t border-[var(--color-border)] text-[10px] text-[var(--color-text-tertiary)] bg-[var(--color-bg)]">
          <span className="flex items-center gap-1">
            <ArrowUp className="w-2.5 h-2.5" />
            <ArrowDown className="w-2.5 h-2.5" />
            navigate
          </span>
          <span className="flex items-center gap-1">
            <CornerDownLeft className="w-2.5 h-2.5" /> open
          </span>
          <span className="ml-auto">{results.length} result{results.length === 1 ? "" : "s"}</span>
        </div>
      </div>
    </div>
  );
}

function ResultRow({
  result, active, onClick, onHover,
}: {
  result: Result;
  active: boolean;
  onClick: () => void;
  onHover: () => void;
}) {
  if (result.kind === "page") {
    const Icon = result.icon;
    return (
      <button
        type="button"
        onClick={onClick}
        onMouseEnter={onHover}
        className={clsx(
          "w-full flex items-center gap-3 px-3 py-2 text-left transition-colors",
          active
            ? "bg-[var(--color-surface-raised)]"
            : "hover:bg-[var(--color-surface-raised)]/60",
        )}
      >
        <Icon className="w-4 h-4 text-[var(--color-text-tertiary)] shrink-0" />
        <span className="text-[13px] text-[var(--color-text-primary)] flex-1">
          Go to {result.label}
        </span>
        <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)]">
          page
        </span>
      </button>
    );
  }

  const opp = result.opp;
  const Icon = opp.type === "direct" ? Briefcase : Users;
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={onHover}
      className={clsx(
        "w-full flex items-center gap-3 px-3 py-2 text-left transition-colors",
        active
          ? "bg-[var(--color-surface-raised)]"
          : "hover:bg-[var(--color-surface-raised)]/60",
      )}
    >
      <Icon className="w-4 h-4 text-[var(--color-text-tertiary)] shrink-0" />
      <div className="flex flex-col flex-1 min-w-0">
        <span className="text-[13px] text-[var(--color-text-primary)] truncate">
          {opp.title || "(no title)"}
        </span>
        <span className="text-[11px] text-[var(--color-text-tertiary)] truncate">
          {[opp.source, opp.company_name, opp.location].filter(Boolean).join(" · ")}
        </span>
      </div>
      <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] shrink-0">
        {opp.type}
      </span>
    </button>
  );
}
