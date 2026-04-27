import { useState, useEffect, useMemo } from "react";
import { cn } from "../lib/cn";
import { Button } from "./Button";
import { useEmailTemplates, useBatchEmail, usePreviewEmail } from "../api/shared";
import {
  X,
  Send,
  CheckCircle,
  XCircle,
  Mail,
  ChevronDown,
  ChevronUp,
  Eye,
  Clock,
} from "lucide-react";

type Lead = Record<string, unknown>;

interface Props {
  open: boolean;
  onClose: () => void;
  leads: Lead[];
  filename?: string;
}

interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  body: string;
}

interface BatchResult {
  to_email: string;
  to_name: string;
  success: boolean;
  message: string;
}

export function BatchEmailDialog({ open, onClose, leads, filename }: Props) {
  const [selectedTemplate, setSelectedTemplate] = useState("initial");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [delaySeconds, setDelaySeconds] = useState(3);
  const [results, setResults] = useState<BatchResult[] | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [previewLeadIdx, setPreviewLeadIdx] = useState(0);

  const { data: templatesData } = useEmailTemplates();
  const batchEmail = useBatchEmail();
  const previewEmail = usePreviewEmail();

  const templates: EmailTemplate[] = templatesData?.templates || [];

  const leadsWithEmail = useMemo(
    () => leads.filter((l) => l.Email && String(l.Email).includes("@")),
    [leads]
  );

  // Load template on open
  useEffect(() => {
    if (open && !body) {
      previewEmail.mutate(
        { template_id: "initial", variables: { business_name: "{business_name}", city: "{city}", niche: "{niche}", website: "{website}", website_review: "{website_review}" } },
        { onSuccess: (d: any) => { setSubject(d.subject); setBody(d.body); } }
      );
    }
  }, [open]);

  function handleTemplateChange(id: string) {
    setSelectedTemplate(id);
    previewEmail.mutate(
      { template_id: id, variables: { business_name: "{business_name}", city: "{city}", niche: "{niche}", website: "{website}", website_review: "{website_review}" } },
      { onSuccess: (d: any) => { setSubject(d.subject); setBody(d.body); } }
    );
  }

  function formatPainTags(lead: Lead): string {
    const tags = String(lead.Pain_Tags || "");
    const map: Record<string, string> = {
      no_website: "No website or website not found",
      few_reviews: "Limited online reviews",
      slow_site: "Website loads slowly",
      no_ssl: "Missing security certificate (HTTPS)",
      not_mobile_friendly: "Not optimized for mobile devices",
      no_booking: "No online booking option",
      no_contact_form: "No contact form found",
    };
    return tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean)
      .map((t) => `  - ${map[t] || t}`)
      .join("\n") || "  - Opportunities to improve online visibility";
  }

  function getPreview() {
    const lead = leadsWithEmail[previewLeadIdx];
    if (!lead) return { subject: "", body: "" };
    const replacements: Record<string, string> = {
      "{business_name}": String(lead.Business_Name || "Your Business"),
      "{city}": String(lead.City || "your city"),
      "{niche}": String(lead.Niche || "business"),
      "{website}": String(lead.Website || "your website"),
      "{website_review}": formatPainTags(lead),
    };
    let s = subject, b = body;
    for (const [k, v] of Object.entries(replacements)) {
      const re = new RegExp(k.replace(/[{}]/g, "\\$&"), "g");
      s = s.replace(re, v);
      b = b.replace(re, v);
    }
    return { subject: s, body: b };
  }

  function handleSend() {
    const recipients = leadsWithEmail.map((lead) => ({
      to_email: String(lead.Email),
      to_name: String(lead.Business_Name || "Business"),
      lead_id: String(lead.Lead_ID || ""),
      variables: {
        business_name: String(lead.Business_Name || "there"),
        contact_name: String(lead.Business_Name || "there"),
        city: String(lead.City || ""),
        niche: String(lead.Niche || "business").toLowerCase(),
        website: String(lead.Website || "your website"),
        website_review: formatPainTags(lead),
      },
    }));
    batchEmail.mutate(
      {
        template_id: selectedTemplate,
        recipients,
        custom_subject: subject || undefined,
        custom_body: body || undefined,
        delay_seconds: delaySeconds,
        filename,
      },
      { onSuccess: (d: any) => setResults(d.results) }
    );
  }

  function handleClose() {
    setResults(null);
    setSelectedTemplate("initial");
    setSubject("");
    setBody("");
    setShowPreview(false);
    setPreviewLeadIdx(0);
    onClose();
  }

  if (!open) return null;

  const successCount = results?.filter((r) => r.success).length || 0;
  const failedCount = results?.filter((r) => !r.success).length || 0;
  const preview = getPreview();
  const skippedCount = leads.length - leadsWithEmail.length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={handleClose} />

      {/* Dialog */}
      <div className="relative bg-surface rounded-2xl border border-border shadow-[--shadow-lg] w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
              <Send size={18} className="text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-text-primary">Send Outreach Campaign</h2>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-success-light text-success border border-success/20">
                  <Mail size={10} /> {leadsWithEmail.length} recipients
                </span>
                {skippedCount > 0 && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold bg-warning-light text-warning border border-warning/20">
                    {skippedCount} skipped (no email)
                  </span>
                )}
              </div>
            </div>
          </div>
          <button onClick={handleClose} className="text-text-tertiary hover:text-text-primary transition-colors p-1 rounded-lg hover:bg-bg">
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {results ? (
            /* Results View */
            <div className="p-6">
              <div className={cn(
                "rounded-xl p-4 mb-4 border",
                failedCount === 0
                  ? "bg-success-light text-success border-success/20"
                  : "bg-warning-light text-warning border-warning/20"
              )}>
                <p className="font-bold text-sm">Campaign Complete</p>
                <p className="text-[13px] mt-0.5">
                  Successfully sent {successCount} of {results.length} emails
                  {failedCount > 0 && ` (${failedCount} failed)`}
                </p>
              </div>
              <div className="border border-border rounded-xl overflow-hidden">
                {results.map((r, i) => (
                  <div
                    key={i}
                    className={cn(
                      "flex items-center gap-3 px-4 py-2.5 text-sm",
                      i < results.length - 1 && "border-b border-border",
                      !r.success && "bg-hot-light/30"
                    )}
                  >
                    {r.success ? (
                      <CheckCircle size={16} className="text-success flex-shrink-0" />
                    ) : (
                      <XCircle size={16} className="text-hot flex-shrink-0" />
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-text-primary text-[13px] truncate">{r.to_name}</p>
                      <p className={cn("text-[12px]", r.success ? "text-text-tertiary" : "text-hot")}>
                        {r.success ? r.to_email : r.message}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Compose View */
            <div>
              <div className="p-6 space-y-4">
                {/* Template + Delay */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2">
                    <label className="block text-[13px] font-semibold text-text-secondary mb-1.5">Template</label>
                    <select
                      value={selectedTemplate}
                      onChange={(e) => handleTemplateChange(e.target.value)}
                      className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors"
                    >
                      {templates.map((t) => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[13px] font-semibold text-text-secondary mb-1.5">Send Delay</label>
                    <select
                      value={delaySeconds}
                      onChange={(e) => setDelaySeconds(Number(e.target.value))}
                      className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors"
                    >
                      <option value={2}>2s (fast)</option>
                      <option value={3}>3s (normal)</option>
                      <option value={5}>5s (safe)</option>
                      <option value={10}>10s (very safe)</option>
                    </select>
                  </div>
                </div>

                {/* Subject */}
                <div>
                  <label className="block text-[13px] font-semibold text-text-secondary mb-1.5">Subject Line</label>
                  <input
                    type="text"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="w-full text-sm border border-border rounded-lg px-3.5 py-2.5 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                  />
                </div>

                {/* Body */}
                <div>
                  <label className="block text-[13px] font-semibold text-text-secondary mb-1.5">Email Body</label>
                  <textarea
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    rows={8}
                    className="w-full text-sm border border-border rounded-lg px-3.5 py-2.5 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-y font-mono text-[13px] leading-relaxed transition-all"
                  />
                </div>
              </div>

              {/* Preview Toggle */}
              <div className="border-t border-border">
                <button
                  onClick={() => setShowPreview(!showPreview)}
                  className="w-full flex items-center justify-between px-6 py-3 text-sm font-semibold text-text-secondary hover:bg-bg transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <Eye size={15} /> Preview with Real Data
                  </span>
                  {showPreview ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>

                {showPreview && (
                  <div className="px-6 pb-5">
                    {leadsWithEmail.length > 0 && (
                      <select
                        value={previewLeadIdx}
                        onChange={(e) => setPreviewLeadIdx(Number(e.target.value))}
                        className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors mb-3"
                      >
                        {leadsWithEmail.slice(0, 10).map((l, i) => (
                          <option key={i} value={i}>
                            {String(l.Business_Name || "Lead")} ({String(l.City || "")})
                          </option>
                        ))}
                      </select>
                    )}
                    <div className="border border-border rounded-xl p-5 bg-bg">
                      <p className="text-[11px] font-semibold text-primary uppercase tracking-wider mb-3">Email Preview</p>
                      <p className="text-[12px] text-text-tertiary">To: {String(leadsWithEmail[previewLeadIdx]?.Email || "...")}</p>
                      <p className="text-sm font-semibold text-text-primary mt-1 mb-3 pb-3 border-b border-border">{preview.subject}</p>
                      <p className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">{preview.body}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Progress */}
              {batchEmail.isPending && (
                <div className="px-6 pb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock size={14} className="text-primary animate-spin" />
                    <p className="text-[13px] text-text-tertiary">Sending emails with {delaySeconds}s delay between each...</p>
                  </div>
                  <div className="h-1.5 bg-bg rounded-full overflow-hidden">
                    <div className="h-full bg-primary rounded-full animate-pulse w-2/3" />
                  </div>
                </div>
              )}

              {/* Warnings */}
              {leadsWithEmail.length === 0 && (
                <div className="mx-6 mb-4 rounded-xl p-3 bg-warning-light text-warning border border-warning/20 text-sm font-medium">
                  No leads with valid email addresses in this list.
                </div>
              )}
              {leadsWithEmail.length > 30 && (
                <div className="mx-6 mb-4 rounded-xl p-3 bg-primary-light text-primary border border-primary/20 text-sm font-medium">
                  Sending to {leadsWithEmail.length} recipients. Estimated time: ~{Math.ceil((leadsWithEmail.length * delaySeconds) / 60)} minutes.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-border bg-bg/50">
          <p className="text-[12px] text-text-muted">Emails sent from configured SMTP account</p>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={handleClose}>
              {results ? "Close" : "Cancel"}
            </Button>
            {!results && (
              <Button
                size="sm"
                onClick={handleSend}
                disabled={leadsWithEmail.length === 0 || batchEmail.isPending}
              >
                <Send size={14} className="mr-1.5" />
                {batchEmail.isPending ? "Sending..." : `Send to ${leadsWithEmail.length} Leads`}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
