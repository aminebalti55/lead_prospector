import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { useColdRuns } from "../../api/cold";
import { Download } from "lucide-react";

interface ColdRun {
  id: string;
  status: string;
  niches: string[];
  locations: string[];
  progress: number;
  leads_found: number;
  output_files: { name: string; url: string }[];
  created_at: string;
}

export function ColdRuns() {
  const { data, isLoading } = useColdRuns();
  const runs: ColdRun[] = data?.runs || [];

  if (isLoading)
    return <div className="text-text-secondary text-sm p-8 font-medium">Loading...</div>;

  return (
    <div>
      <PageHeader title="Scraping Runs" subtitle="Track and manage your cold outreach runs">
        <Link to="/cold/runs/new">
          <Button>New Run</Button>
        </Link>
      </PageHeader>

      {runs.length === 0 ? (
        <EmptyState
          message="No runs yet."
          action={{ label: "Start your first run", href: "/cold/runs/new" }}
        />
      ) : (
        <div className="space-y-3">
          {runs.map((run) => (
            <div
              key={run.id}
              className="bg-surface rounded-xl border border-border p-5 shadow-[--shadow-sm] hover:shadow-[--shadow-md] transition-shadow duration-200"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2.5 mb-1">
                    <span className="text-sm font-semibold text-text-primary">
                      {run.niches?.join(", ") || "Run"}
                    </span>
                    <StatusBadge status={run.status} />
                  </div>
                  <p className="text-[13px] text-text-secondary font-medium">
                    {run.locations?.join(", ")}
                  </p>
                  <p className="text-xs text-text-tertiary mt-0.5">
                    Started {run.created_at ? new Date(run.created_at).toLocaleString() : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-text-primary">
                    {run.leads_found || 0} leads
                  </p>
                  <p className="text-xs text-text-secondary font-medium">
                    {Math.round(run.progress || 0)}% complete
                  </p>
                </div>
              </div>

              <div className="mt-4 h-1.5 bg-bg rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(run.progress || 0, 100)}%` }}
                />
              </div>

              {run.output_files && run.output_files.length > 0 && (
                <div className="mt-3 flex gap-2 flex-wrap">
                  {run.output_files.map((f) => (
                    <a
                      key={f.name}
                      href={f.url}
                      download
                      className="inline-flex items-center gap-1.5 text-xs text-primary hover:text-primary-hover font-semibold transition-colors"
                    >
                      <Download size={12} />
                      {f.name}
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
