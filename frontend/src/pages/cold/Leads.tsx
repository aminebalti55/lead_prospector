import { useState, useMemo } from "react";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { EmptyState } from "../../components/EmptyState";
import { Button } from "../../components/Button";
import { BatchEmailDialog } from "../../components/BatchEmailDialog";
import { useColdFiles, useColdLeads, useUpdateColdLead } from "../../api/cold";
import { downloadUrl } from "../../api/client";
import { cn } from "../../lib/cn";
import {
  Search,
  Download,
  Mail,
  Send,
  Flame,
  FileSpreadsheet,
  RefreshCw,
} from "lucide-react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";

type Lead = Record<string, unknown>;

const PRIORITY_FILTERS: { label: string; value: string | null; color?: string }[] = [
  { label: "All", value: null },
  { label: "Hot", value: "hot", color: "bg-hot-light text-hot border-hot/20" },
  { label: "Warm", value: "warm", color: "bg-warning-light text-warning border-warning/20" },
  { label: "Cold", value: "cold", color: "bg-bg text-text-secondary border-border" },
];

export function ColdLeads() {
  const { data: filesData, refetch: refetchFiles } = useColdFiles();
  const [selectedFile, setSelectedFile] = useState("");
  const { data: leadsData, isLoading, refetch: refetchLeads } = useColdLeads(selectedFile);
  const updateLead = useUpdateColdLead();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [filter, setFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState<string | null>(null);
  const [batchEmailOpen, setBatchEmailOpen] = useState(false);

  const files: { name: string; size_bytes?: number; modified_at?: string }[] = filesData?.files || [];
  const allRows: Lead[] = leadsData?.rows || [];

  if (!selectedFile && files.length > 0) {
    setSelectedFile(files[0].name);
  }

  // Priority-filtered rows
  const rows = useMemo(() => {
    if (!priorityFilter) return allRows;
    return allRows.filter(
      (l) => String(l.Priority || "cold").toLowerCase() === priorityFilter
    );
  }, [allRows, priorityFilter]);

  // Stats
  const stats = useMemo(() => {
    const total = allRows.length;
    const hot = allRows.filter((l) => String(l.Priority || "").toLowerCase() === "hot").length;
    const warm = allRows.filter((l) => String(l.Priority || "").toLowerCase() === "warm").length;
    const cold = allRows.filter((l) => String(l.Priority || "").toLowerCase() === "cold").length;
    const withEmail = allRows.filter((l) => l.Email && String(l.Email).includes("@")).length;
    return { total, hot, warm, cold, withEmail };
  }, [allRows]);

  const columns: ColumnDef<Lead>[] = [
    {
      accessorKey: "Priority",
      header: "Priority",
      cell: ({ getValue }) => (
        <StatusBadge status={String(getValue() || "cold")} />
      ),
      size: 90,
    },
    {
      accessorKey: "Score",
      header: "Score",
      size: 60,
      cell: ({ getValue }) => {
        const score = Number(getValue() || 0);
        return <span className="font-semibold text-text-primary">{score}</span>;
      },
    },
    {
      accessorKey: "Business_Name",
      header: "Business",
      size: 200,
      cell: ({ getValue }) => (
        <span className="font-medium text-text-primary">{String(getValue() || "")}</span>
      ),
    },
    { accessorKey: "City", header: "City", size: 100 },
    { accessorKey: "State", header: "ST", size: 40 },
    { accessorKey: "Phone", header: "Phone", size: 130 },
    {
      accessorKey: "Website",
      header: "Website",
      cell: ({ getValue }) => {
        const v = String(getValue() || "");
        return v ? (
          <a
            href={v.startsWith("http") ? v : `https://${v}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:text-primary-hover hover:underline text-xs font-medium truncate block max-w-[150px]"
          >
            {v}
          </a>
        ) : (
          <span className="text-text-tertiary">&mdash;</span>
        );
      },
      size: 150,
    },
    { accessorKey: "Email", header: "Email", size: 180 },
    { accessorKey: "Pain_Tags", header: "Pain Tags", size: 150 },
    {
      accessorKey: "Outreach_Status",
      header: "Status",
      cell: ({ row }) => {
        const leadId = String(row.original.Lead_ID || "");
        const current = String(row.original.Outreach_Status || "new");
        return (
          <select
            value={current}
            onChange={(e) =>
              updateLead.mutate({
                leadId,
                data: { Outreach_Status: e.target.value },
              })
            }
            className="text-xs font-medium border border-border rounded-md px-2 py-1 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors"
          >
            {["new", "queued", "contacted", "replied", "meeting", "converted", "passed"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        );
      },
      size: 120,
    },
    {
      id: "actions",
      header: "",
      size: 40,
      cell: ({ row }) => {
        const email = String(row.original.Email || "");
        if (!email.includes("@")) return null;
        return (
          <a
            href={`/cold/email?lead=${encodeURIComponent(String(row.original.Lead_ID || ""))}&file=${encodeURIComponent(selectedFile)}`}
            className="inline-flex items-center justify-center w-7 h-7 rounded-md text-text-tertiary hover:text-primary hover:bg-primary-light transition-colors"
            title="Send email to this lead"
          >
            <Send size={13} />
          </a>
        );
      },
    },
  ];

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting, globalFilter: filter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div>
      <PageHeader title="Cold Outreach Leads" subtitle={`${stats.total} leads loaded`} />

      {/* Toolbar: file picker, search, actions */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        {/* File selector */}
        <div className="flex items-center gap-2">
          <FileSpreadsheet size={15} className="text-text-tertiary" />
          <select
            value={selectedFile}
            onChange={(e) => { setSelectedFile(e.target.value); setPriorityFilter(null); }}
            className="text-sm font-medium border border-border rounded-lg px-3 py-2 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors"
          >
            {files.map((f) => (
              <option key={f.name} value={f.name}>{f.name}</option>
            ))}
          </select>
        </div>

        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
          <input
            type="text"
            placeholder="Search leads..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full text-sm border border-border rounded-lg pl-9 pr-3 py-2 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
          />
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => setBatchEmailOpen(true)}
            disabled={stats.withEmail === 0}
          >
            <Mail size={14} className="mr-1.5" />
            Email All ({stats.withEmail})
          </Button>
          {selectedFile && (
            <a href={downloadUrl(selectedFile)} download>
              <Button variant="secondary" size="sm" type="button">
                <Download size={14} className="mr-1.5" />
                Download Excel
              </Button>
            </a>
          )}
          <button
            onClick={() => { refetchFiles(); refetchLeads(); }}
            className="p-2 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-bg border border-border transition-colors"
            title="Refresh"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Stats row */}
      {stats.total > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          <div className="bg-surface rounded-xl border border-border p-3">
            <p className="text-[11px] font-semibold text-text-tertiary uppercase tracking-wider">Total</p>
            <p className="text-xl font-bold text-text-primary mt-0.5">{stats.total}</p>
          </div>
          <div className="bg-surface rounded-xl border border-hot/15 p-3">
            <p className="text-[11px] font-semibold text-hot uppercase tracking-wider flex items-center gap-1"><Flame size={11} /> Hot</p>
            <p className="text-xl font-bold text-text-primary mt-0.5">{stats.hot}</p>
          </div>
          <div className="bg-surface rounded-xl border border-warning/15 p-3">
            <p className="text-[11px] font-semibold text-warning uppercase tracking-wider">Warm</p>
            <p className="text-xl font-bold text-text-primary mt-0.5">{stats.warm}</p>
          </div>
          <div className="bg-surface rounded-xl border border-success/15 p-3">
            <p className="text-[11px] font-semibold text-success uppercase tracking-wider flex items-center gap-1"><Mail size={11} /> With Email</p>
            <p className="text-xl font-bold text-text-primary mt-0.5">{stats.withEmail}</p>
          </div>
        </div>
      )}

      {/* Priority filter chips */}
      {stats.total > 0 && (
        <div className="flex items-center gap-2 mb-5">
          {PRIORITY_FILTERS.map((pf) => {
            const isActive = priorityFilter === pf.value;
            const count = pf.value === null
              ? stats.total
              : pf.value === "hot" ? stats.hot
              : pf.value === "warm" ? stats.warm
              : stats.cold;
            return (
              <button
                key={pf.label}
                onClick={() => setPriorityFilter(pf.value)}
                className={cn(
                  "inline-flex items-center px-3 py-1.5 rounded-lg text-[12px] font-semibold border transition-all cursor-pointer",
                  isActive
                    ? pf.color || "bg-primary-light text-primary border-primary/20"
                    : "bg-surface text-text-tertiary border-border hover:border-border-strong hover:text-text-secondary"
                )}
              >
                {pf.label} ({count})
              </button>
            );
          })}
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <div className="text-text-secondary text-sm font-medium">Loading...</div>
      ) : rows.length === 0 ? (
        <EmptyState
          message={priorityFilter ? `No ${priorityFilter} leads found.` : "No leads in this file."}
          action={!priorityFilter ? { label: "Start a new run", href: "/cold/runs/new" } : undefined}
        />
      ) : (
        <div className="bg-surface rounded-xl border border-border overflow-auto shadow-[--shadow-sm]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-bg/50">
                {table.getHeaderGroups().map((hg) =>
                  hg.headers.map((h) => (
                    <th
                      key={h.id}
                      onClick={h.column.getToggleSortingHandler()}
                      className="px-3 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider cursor-pointer hover:text-text-primary whitespace-nowrap transition-colors"
                    >
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      {h.column.getIsSorted() === "asc" ? " \u2191" : h.column.getIsSorted() === "desc" ? " \u2193" : ""}
                    </th>
                  ))
                )}
              </tr>
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-border last:border-0 hover:bg-bg/50 transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2.5 text-[13px] text-text-secondary whitespace-nowrap">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Batch Email Dialog */}
      <BatchEmailDialog
        open={batchEmailOpen}
        onClose={() => setBatchEmailOpen(false)}
        leads={rows}
        filename={selectedFile}
      />
    </div>
  );
}
