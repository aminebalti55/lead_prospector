import { useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { useEmailTemplates, useSendEmail } from "../../api/shared";
import { useColdFiles, useColdLeads } from "../../api/cold";
import { CheckCircle, AlertCircle } from "lucide-react";

interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  body: string;
}

export function ColdEmail() {
  const { data: templatesData } = useEmailTemplates();
  const { data: filesData } = useColdFiles();
  const sendEmail = useSendEmail();

  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [selectedFile, setSelectedFile] = useState("");
  const [selectedLeadId, setSelectedLeadId] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [sent, setSent] = useState(false);

  const templates: EmailTemplate[] = templatesData?.templates || [];
  const files: { name: string }[] = filesData?.files || [];
  const { data: leadsData } = useColdLeads(selectedFile);
  const leads: Record<string, unknown>[] = leadsData?.rows || [];

  if (!selectedFile && files.length > 0) {
    setSelectedFile(files[0].name);
  }

  function handleTemplateChange(templateId: string) {
    setSelectedTemplate(templateId);
    const tpl = templates.find((t) => t.id === templateId);
    if (tpl) {
      setSubject(tpl.subject);
      setBody(tpl.body);
    }
  }

  function handleLeadChange(leadId: string) {
    setSelectedLeadId(leadId);
    const lead = leads.find((l) => String(l.Lead_ID) === leadId);
    if (lead) {
      setRecipientEmail(String(lead.Email || ""));
      if (body) {
        let filled = body;
        filled = filled.replace(/\{\{business_name\}\}/gi, String(lead.Business_Name || ""));
        filled = filled.replace(/\{\{city\}\}/gi, String(lead.City || ""));
        filled = filled.replace(/\{\{state\}\}/gi, String(lead.State || ""));
        setBody(filled);
      }
    }
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    await sendEmail.mutateAsync({
      to: recipientEmail,
      subject,
      body,
      lead_id: selectedLeadId,
      template_id: selectedTemplate,
    });
    setSent(true);
    setTimeout(() => setSent(false), 3000);
  }

  if (templates.length === 0 && !templatesData) {
    return (
      <div>
        <PageHeader title="Email Outreach" />
        <EmptyState message="Loading templates..." />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Email Outreach" subtitle="Send personalized emails to your leads" />

      <div className="grid grid-cols-2 gap-6">
        <form
          onSubmit={handleSend}
          className="bg-surface rounded-xl border border-border p-6 space-y-5 shadow-[--shadow-sm]"
        >
          <h3 className="text-sm font-semibold text-text-primary">Compose</h3>

          <div>
            <label className="block text-[13px] font-semibold text-text-secondary mb-1.5">Template</label>
            <select
              value={selectedTemplate}
              onChange={(e) => handleTemplateChange(e.target.value)}
              className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors"
            >
              <option value="">Select a template...</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[13px] font-semibold text-text-secondary mb-1.5">File</label>
              <select
                value={selectedFile}
                onChange={(e) => { setSelectedFile(e.target.value); setSelectedLeadId(""); }}
                className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors"
              >
                {files.map((f) => (
                  <option key={f.name} value={f.name}>{f.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[13px] font-semibold text-text-secondary mb-1.5">Lead</label>
              <select
                value={selectedLeadId}
                onChange={(e) => handleLeadChange(e.target.value)}
                className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors"
              >
                <option value="">Select a lead...</option>
                {leads.map((l) => (
                  <option key={String(l.Lead_ID)} value={String(l.Lead_ID)}>
                    {String(l.Business_Name || l.Lead_ID)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-[13px] font-semibold text-text-secondary mb-1.5">Recipient Email</label>
            <input
              type="email"
              value={recipientEmail}
              onChange={(e) => setRecipientEmail(e.target.value)}
              className="w-full text-sm border border-border rounded-lg px-3.5 py-2.5 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              required
            />
          </div>

          <div>
            <label className="block text-[13px] font-semibold text-text-secondary mb-1.5">Subject</label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full text-sm border border-border rounded-lg px-3.5 py-2.5 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              required
            />
          </div>

          <div>
            <label className="block text-[13px] font-semibold text-text-secondary mb-1.5">Body</label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={8}
              className="w-full text-sm border border-border rounded-lg px-3.5 py-2.5 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-y transition-all leading-relaxed"
              required
            />
          </div>

          <div className="flex items-center gap-3 pt-2">
            <Button type="submit" disabled={sendEmail.isPending}>
              {sendEmail.isPending ? "Sending..." : "Send Email"}
            </Button>
            {sent && (
              <span className="inline-flex items-center gap-1.5 text-sm text-success font-semibold">
                <CheckCircle size={14} /> Sent successfully!
              </span>
            )}
            {sendEmail.isError && (
              <span className="inline-flex items-center gap-1.5 text-sm text-hot font-semibold">
                <AlertCircle size={14} /> Failed to send.
              </span>
            )}
          </div>
        </form>

        <div className="bg-surface rounded-xl border border-border p-6 shadow-[--shadow-sm]">
          <h3 className="text-sm font-semibold text-text-primary mb-4">Preview</h3>
          <div className="border border-border rounded-lg p-5 bg-bg min-h-[300px]">
            <p className="text-xs text-text-tertiary mb-1 font-medium">To: {recipientEmail || "..."}</p>
            <p className="text-sm font-semibold text-text-primary mb-3 pb-3 border-b border-border">
              {subject || "Subject line"}
            </p>
            <div className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">
              {body || "Email body will appear here..."}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
