import { useParams, useNavigate } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { Button } from "../../components/Button";
import { useDirectLead, useUpdateDirectLead } from "../../api/direct";
import { ArrowLeft, ExternalLink, Building2, MapPin, Calendar, DollarSign, Zap } from "lucide-react";

export function DirectLeadDetail() {
  const { leadId } = useParams<{ leadId: string }>();
  const navigate = useNavigate();
  const { data, isLoading } = useDirectLead(leadId || "");
  const updateLead = useUpdateDirectLead();

  if (isLoading) {
    return <div className="text-text-secondary text-sm p-8 font-medium">Loading...</div>;
  }

  const lead = data?.lead || data;
  if (!lead) {
    return <div className="text-text-secondary text-sm p-8 font-medium">Lead not found.</div>;
  }

  const skills = String(lead.Matched_Skills || "")
    .split(",")
    .map((s: string) => s.trim())
    .filter(Boolean);

  function handleStatusChange(status: string) {
    if (!leadId) return;
    updateLead.mutate({ leadId, data: { Outreach_Status: status } });
  }

  return (
    <div>
      <PageHeader title="">
        <Button variant="ghost" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} className="mr-1.5" />
          Back
        </Button>
      </PageHeader>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <div className="bg-surface rounded-xl border border-border p-6 shadow-[--shadow-sm]">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-lg font-bold text-text-primary tracking-tight">
                  {lead.Title || "Untitled"}
                </h1>
                <p className="text-sm text-text-secondary font-medium mt-1">
                  {lead.Company_Name || lead.Company || "Unknown company"}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={String(lead.Priority || "new")} />
                <span className="text-xl font-bold text-primary">{lead.Relevance_Score || 0}</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-4 text-[13px] text-text-secondary font-medium">
              {lead.Source && (
                <span className="flex items-center gap-1.5"><Building2 size={14} />{lead.Source}</span>
              )}
              {lead.Location && (
                <span className="flex items-center gap-1.5"><MapPin size={14} />{lead.Location}</span>
              )}
              {lead.Posted_Date && (
                <span className="flex items-center gap-1.5">
                  <Calendar size={14} />
                  {new Date(String(lead.Posted_Date)).toLocaleDateString()}
                </span>
              )}
              {lead.Budget_Signal && (
                <span className="flex items-center gap-1.5 text-primary font-semibold">
                  <DollarSign size={14} />{lead.Budget_Signal}
                </span>
              )}
              {lead.Urgency_Signal && (
                <span className="flex items-center gap-1.5 text-hot font-semibold">
                  <Zap size={14} />{lead.Urgency_Signal}
                </span>
              )}
            </div>

            {lead.URL && (
              <a
                href={String(lead.URL)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-primary hover:text-primary-hover font-semibold mt-4 transition-colors"
              >
                View original posting <ExternalLink size={13} />
              </a>
            )}
          </div>

          {lead.Description && (
            <div className="bg-surface rounded-xl border border-border p-6 shadow-[--shadow-sm]">
              <h3 className="text-sm font-semibold text-text-primary mb-3">Description</h3>
              <div className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                {lead.Description}
              </div>
            </div>
          )}

          {skills.length > 0 && (
            <div className="bg-surface rounded-xl border border-border p-6 shadow-[--shadow-sm]">
              <h3 className="text-sm font-semibold text-text-primary mb-3">Matched Skills</h3>
              <div className="flex gap-2 flex-wrap">
                {skills.map((s: string) => (
                  <span
                    key={s}
                    className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold bg-success-light text-success border border-success/20"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-surface rounded-xl border border-border p-6 shadow-[--shadow-sm]">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Outreach Status</h3>
            <select
              value={String(lead.Outreach_Status || "new")}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="w-full text-sm font-medium border border-border rounded-lg px-3 py-2.5 bg-surface text-text-primary mb-4 cursor-pointer hover:border-border-strong transition-colors"
            >
              {["new", "contacted", "replied", "meeting", "converted", "passed"].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>

            {lead.Notes && (
              <div className="mt-2">
                <p className="text-xs font-semibold text-text-secondary mb-1">Notes</p>
                <p className="text-sm text-text-primary">{lead.Notes}</p>
              </div>
            )}
          </div>

          <div className="bg-surface rounded-xl border border-border p-6 shadow-[--shadow-sm]">
            <h3 className="text-sm font-semibold text-text-primary mb-4">Company Info</h3>
            <dl className="space-y-3 text-sm">
              {lead.Company_Name && (
                <div>
                  <dt className="text-xs text-text-tertiary font-semibold uppercase tracking-wider">Name</dt>
                  <dd className="text-text-primary font-medium mt-0.5">{lead.Company_Name}</dd>
                </div>
              )}
              {lead.Company_Website && (
                <div>
                  <dt className="text-xs text-text-tertiary font-semibold uppercase tracking-wider">Website</dt>
                  <dd className="mt-0.5">
                    <a
                      href={String(lead.Company_Website).startsWith("http") ? String(lead.Company_Website) : `https://${lead.Company_Website}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:text-primary-hover text-xs font-semibold transition-colors"
                    >
                      {lead.Company_Website}
                    </a>
                  </dd>
                </div>
              )}
              {lead.Company_Size && (
                <div>
                  <dt className="text-xs text-text-tertiary font-semibold uppercase tracking-wider">Size</dt>
                  <dd className="text-text-primary mt-0.5">{lead.Company_Size}</dd>
                </div>
              )}
              {lead.Contact_Name && (
                <div>
                  <dt className="text-xs text-text-tertiary font-semibold uppercase tracking-wider">Contact</dt>
                  <dd className="text-text-primary font-medium mt-0.5">{lead.Contact_Name}</dd>
                </div>
              )}
              {lead.Contact_Email && (
                <div>
                  <dt className="text-xs text-text-tertiary font-semibold uppercase tracking-wider">Email</dt>
                  <dd className="mt-0.5">
                    <a href={`mailto:${lead.Contact_Email}`} className="text-primary hover:text-primary-hover text-xs font-semibold transition-colors">
                      {lead.Contact_Email}
                    </a>
                  </dd>
                </div>
              )}
              {lead.Contact_Phone && (
                <div>
                  <dt className="text-xs text-text-tertiary font-semibold uppercase tracking-wider">Phone</dt>
                  <dd className="text-text-primary mt-0.5">{lead.Contact_Phone}</dd>
                </div>
              )}
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
