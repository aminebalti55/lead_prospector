import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { useDirectScans } from "../../api/direct";

interface DirectScan {
  id: string;
  status: string;
  sources: string[];
  keywords: string[];
  progress: number;
  leads_found: number;
  created_at: string;
}

export function DirectScans() {
  const { data, isLoading } = useDirectScans();
  const scans: DirectScan[] = data?.scans || [];

  if (isLoading) {
    return <div className="text-text-secondary text-sm p-8 font-medium">Loading...</div>;
  }

  return (
    <div>
      <PageHeader title="Direct Scans" subtitle="Track your direct lead scanning jobs">
        <Link to="/direct/scans/new">
          <Button>New Scan</Button>
        </Link>
      </PageHeader>

      {scans.length === 0 ? (
        <EmptyState
          message="No scans yet."
          action={{ label: "Start your first scan", href: "/direct/scans/new" }}
        />
      ) : (
        <div className="space-y-3">
          {scans.map((scan) => (
            <div
              key={scan.id}
              className="bg-surface rounded-xl border border-border p-5 shadow-[--shadow-sm] hover:shadow-[--shadow-md] transition-shadow duration-200"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2.5 mb-1">
                    <span className="text-sm font-semibold text-text-primary">
                      {scan.keywords?.join(", ") || "Scan"}
                    </span>
                    <StatusBadge status={scan.status} />
                  </div>
                  <p className="text-[13px] text-text-secondary font-medium">
                    Sources: {scan.sources?.join(", ") || "All"}
                  </p>
                  <p className="text-xs text-text-tertiary mt-0.5">
                    Started {scan.created_at ? new Date(scan.created_at).toLocaleString() : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-text-primary">{scan.leads_found || 0} leads</p>
                  <p className="text-xs text-text-secondary font-medium">
                    {Math.round(scan.progress || 0)}% complete
                  </p>
                </div>
              </div>

              <div className="mt-4 h-1.5 bg-bg rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(scan.progress || 0, 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
