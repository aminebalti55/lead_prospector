import { useMemo, useState } from "react";
import { Send } from "lucide-react";
import { Button, Card, MoneyValue, Pill } from "../../design/primitives";
import { useOpportunities } from "../../api/opportunities";
import { useTemplates } from "../../api/templates";
import { useSendOutreach } from "../../api/outreach";
import type { Opportunity } from "../../types/opportunity";
import type { EmailTemplate } from "../../types/template";

function buildVariables(opp: Opportunity): Record<string, string> {
  const fullName = (opp.contact_email && opp.contact_email.split("@")[0]) || opp.company_name || "";
  const cleanedName = (opp.company_name || fullName || "(no name)").trim();
  const firstName = cleanedName.split(/\s+/)[0] || cleanedName;
  return {
    name: cleanedName,
    first_name: firstName,
    company: opp.company_name || cleanedName,
    title: opp.title || "",
    value: opp.estimated_value_usd > 0 ? `$${opp.estimated_value_usd.toLocaleString("en-US")}` : "",
    source: opp.source || "",
    location: opp.location || "",
  };
}

function substitute(text: string, variables: Record<string, string>): string {
  let out = text;
  for (const [key, value] of Object.entries(variables)) {
    out = out.split("{" + key + "}").join(value);
  }
  return out;
}

export function OutreachPage() {
  const { data: oppData } = useOpportunities({ sort: "score", limit: 200 });
  const { data: tplData } = useTemplates();
  const opps = (oppData?.opportunities ?? []).filter((o) => o.contact_email);
  const templates = tplData?.templates ?? [];

  const [selectedOppId, setSelectedOppId] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [customSubject, setCustomSubject] = useState<string | null>(null);
  const [customBody, setCustomBody] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  const send = useSendOutreach();
  const [result, setResult] = useState<string | null>(null);

  const opp = opps.find((o) => o.id === selectedOppId) ?? null;
  const template = templates.find((t) => t.id === selectedTemplateId) ?? null;

  const variables = useMemo(() => (opp ? buildVariables(opp) : {}), [opp]);

  const baseSubject = template?.subject ?? "";
  const baseBody = template?.body ?? "";
  const previewSubject = substitute(customSubject ?? baseSubject, variables);
  const previewBody = substitute(customBody ?? baseBody, variables);

  function reset() {
    setCustomSubject(null);
    setCustomBody(null);
    setEditing(false);
  }

  async function handleSend() {
    if (!opp || !template) return;
    setResult(null);
    const res = await send.mutateAsync({
      opportunity_id: opp.id,
      opportunity_type: opp.type,
      source_file: opp.source_file,
      raw_lead_id: opp.raw_lead_id,
      current_stage: opp.stage,
      template_id: template.id,
      custom_subject: customSubject ?? undefined,
      custom_body: customBody ?? undefined,
      to_email: opp.contact_email,
      to_name: variables.name,
      variables,
    });
    setResult(res.message);
    if (res.success) reset();
  }

  return (
    <div className="p-6 flex flex-col gap-4 w-full h-full">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Outreach</div>
          <div className="text-[11px] text-[var(--color-text-tertiary)]">
            {opps.length} opportunities have an email · pick one and a template to send
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4 flex-1 min-h-0">
        {/* Opportunity picker */}
        <Card className="p-3 flex flex-col gap-2 overflow-hidden">
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium px-1">
            Opportunities with email
          </div>
          <div className="flex-1 overflow-auto flex flex-col">
            {opps.length === 0 && (
              <div className="text-[12px] text-[var(--color-text-tertiary)] p-4 text-center">
                No opportunities have a contact email yet. Run a scan with email extraction first.
              </div>
            )}
            {opps.map((o) => (
              <button
                key={o.id}
                type="button"
                onClick={() => { setSelectedOppId(o.id); reset(); }}
                className={
                  "px-2 py-2 text-left rounded-[var(--radius-sm)] flex flex-col gap-0.5 transition-colors " +
                  (o.id === selectedOppId ? "bg-[var(--color-surface-raised)]" : "hover:bg-[var(--color-surface-raised)]")
                }
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-[12px] font-medium text-[var(--color-text-primary)] truncate flex-1">
                    {o.title || o.company_name || "(no title)"}
                  </span>
                  <MoneyValue usd={o.estimated_value_usd} size="sm" tone="accent" />
                </div>
                <div className="text-[10px] text-[var(--color-text-tertiary)] flex items-center gap-1.5">
                  <Pill tone="neutral">{o.source}</Pill>
                  <span className="truncate">{o.contact_email}</span>
                </div>
              </button>
            ))}
          </div>
        </Card>

        {/* Composer */}
        <Card className="p-5 flex flex-col gap-3 overflow-auto">
          {!opp && (
            <div className="text-[12px] text-[var(--color-text-tertiary)] p-8 text-center">
              Select an opportunity from the left to compose.
            </div>
          )}

          {opp && (
            <>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[14px] font-semibold text-[var(--color-text-primary)]">{opp.title}</div>
                  <div className="text-[11px] text-[var(--color-text-tertiary)] mt-0.5">
                    To: {variables.name} &lt;{opp.contact_email}&gt;
                  </div>
                </div>
                <MoneyValue usd={opp.estimated_value_usd} size="lg" tone="accent" />
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Template</span>
                <select
                  value={selectedTemplateId ?? ""}
                  onChange={(e) => { setSelectedTemplateId(e.target.value || null); reset(); }}
                  className="h-8 px-2 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[12px] text-[var(--color-text-primary)] flex-1"
                >
                  <option value="">— choose a template —</option>
                  {templates.map((t) => (<option key={t.id} value={t.id}>{t.name}</option>))}
                </select>
                {template && (
                  <Button variant="ghost" size="sm" onClick={() => setEditing(!editing)}>
                    {editing ? "Use preview" : "Edit"}
                  </Button>
                )}
              </div>

              {template && !editing && (
                <div className="flex flex-col gap-3 bg-[var(--color-bg)] p-4 rounded-[var(--radius-md)] border border-[var(--color-border)]">
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium mb-1">Subject</div>
                    <div className="text-[13px] text-[var(--color-text-primary)]">{previewSubject}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium mb-1">Body</div>
                    <pre className="text-[12px] text-[var(--color-text-primary)] whitespace-pre-wrap font-sans leading-relaxed">{previewBody}</pre>
                  </div>
                </div>
              )}

              {template && editing && (
                <div className="flex flex-col gap-3">
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Subject (override)</label>
                    <input
                      value={customSubject ?? baseSubject}
                      onChange={(e) => setCustomSubject(e.target.value)}
                      className="h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)]"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Body (override)</label>
                    <textarea
                      value={customBody ?? baseBody}
                      onChange={(e) => setCustomBody(e.target.value)}
                      rows={14}
                      className="px-2.5 py-2 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[12px] text-[var(--color-text-primary)] font-mono resize-y"
                    />
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2 pt-2">
                <Button variant="primary" onClick={handleSend} disabled={!template || send.isPending}>
                  <Send className="w-3.5 h-3.5" />
                  {send.isPending ? "Sending…" : "Send email"}
                </Button>
                {result && (
                  <span className={"text-[12px] " + (result.toLowerCase().includes("sent") ? "text-[var(--color-accent)]" : "text-[var(--color-hot)]")}>
                    {result}
                  </span>
                )}
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
