import { useEffect, useMemo, useState } from "react";
import { X, Send, AlertTriangle, CheckCircle2 } from "lucide-react";
import { Button, Card } from "../../design/primitives";
import { useTemplates } from "../../api/templates";
import { useSendOutreach, useBulkSendOutreach } from "../../api/outreach";
import type { Opportunity } from "../../types/opportunity";

interface Props {
  recipients: Opportunity[];
  onClose: () => void;
}

const inputClass =
  "h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)] w-full";

function buildVariables(opp: Opportunity): Record<string, string> {
  return {
    company: opp.company_name || opp.title || "",
    title: opp.title || "",
    contact_name: opp.contact_email ? opp.contact_email.split("@")[0] : "",
    location: opp.location || "",
    source: opp.source || "",
  };
}

function substitute(text: string, vars: Record<string, string>): string {
  let out = text;
  for (const [k, v] of Object.entries(vars)) {
    out = out.replaceAll(`{${k}}`, v);
  }
  return out;
}

export function SendTemplateModal({ recipients, onClose }: Props) {
  const isBulk = recipients.length > 1;
  const single = !isBulk ? recipients[0] : null;

  const templatesQ = useTemplates();
  const send = useSendOutreach();
  const bulkSend = useBulkSendOutreach();

  const [templateId, setTemplateId] = useState<string>("");
  const [overrideEmail, setOverrideEmail] = useState<string>(single?.contact_email ?? "");
  const [result, setResult] = useState<string | null>(null);

  // Default to first template once they load.
  useEffect(() => {
    const templates = templatesQ.data?.templates;
    if (templates && templates.length > 0 && !templateId) {
      setTemplateId(templates[0].id);
    }
  }, [templatesQ.data, templateId]);

  const currentTemplate = useMemo(() => {
    return templatesQ.data?.templates.find((t) => t.id === templateId);
  }, [templatesQ.data, templateId]);

  // Active leads = not yet contacted/replied/meeting/won/lost. Sending again
  // to a lead already past "researching" risks looking spammy and undoes the
  // pipeline state, so we skip them automatically.
  const ALREADY_CONTACTED_STAGES = new Set(["contacted", "replied", "meeting", "won", "lost"]);
  const withEmail = recipients.filter(
    (r) =>
      r.contact_email &&
      r.contact_email.includes("@") &&
      !ALREADY_CONTACTED_STAGES.has(r.stage),
  );
  const alreadyContacted = recipients.filter((r) =>
    ALREADY_CONTACTED_STAGES.has(r.stage),
  ).length;
  const withoutEmail = recipients.length - withEmail.length - alreadyContacted;

  const previewVars = single
    ? { ...buildVariables(single), sender_name: "You" }
    : recipients[0]
      ? { ...buildVariables(recipients[0]), sender_name: "You" }
      : {};

  const previewSubject = currentTemplate
    ? substitute(currentTemplate.subject, previewVars)
    : "";
  const previewBody = currentTemplate
    ? substitute(currentTemplate.body, previewVars)
    : "";

  async function handleSend() {
    if (!currentTemplate) return;
    setResult(null);

    if (isBulk) {
      const recList = withEmail.map((r) => ({
        opportunity_id: r.id,
        opportunity_type: r.type,
        source_file: r.source_file,
        raw_lead_id: r.raw_lead_id,
        current_stage: r.stage,
        to_email: r.contact_email,
        to_name: r.company_name || r.contact_email.split("@")[0],
        variables: buildVariables(r),
      }));
      if (recList.length === 0) {
        setResult("No selected leads have an email address.");
        return;
      }
      try {
        const res = await bulkSend.mutateAsync({
          template_id: currentTemplate.id,
          recipients: recList,
        });
        setResult(`Sent ${res.sent}, failed ${res.failed} of ${recList.length}.`);
      } catch (e: any) {
        setResult(`Error: ${e?.message || e}`);
      }
      return;
    }

    if (!single) return;
    const to = (overrideEmail || single.contact_email || "").trim();
    if (!to) {
      setResult("This lead has no email — paste one above or use Reply now to open the source.");
      return;
    }
    try {
      const res = await send.mutateAsync({
        opportunity_id: single.id,
        opportunity_type: single.type,
        source_file: single.source_file,
        raw_lead_id: single.raw_lead_id,
        current_stage: single.stage,
        template_id: currentTemplate.id,
        to_email: to,
        to_name: single.company_name || to.split("@")[0],
        variables: buildVariables(single),
      });
      setResult(res.success ? `✓ ${res.message}` : `✗ ${res.message}`);
    } catch (e: any) {
      setResult(`Error: ${e?.message || e}`);
    }
  }

  const isPending = send.isPending || bulkSend.isPending;
  const noTemplates = !templatesQ.isLoading && (templatesQ.data?.templates.length ?? 0) === 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <Card
        className="w-[680px] max-h-[90vh] overflow-auto p-5 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-[14px] font-semibold text-[var(--color-text-primary)]">
            {isBulk ? `Send template to ${recipients.length} leads` : "Send template"}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Bulk gating banner */}
        {isBulk && (withoutEmail > 0 || alreadyContacted > 0) && (
          <div className="flex gap-2 items-start text-[12px] p-2.5 rounded-[var(--radius-sm)] bg-[var(--color-warm)]/15 text-[var(--color-warm)]">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <div className="flex flex-col gap-0.5">
              {withoutEmail > 0 && (
                <span>{withoutEmail} have no email — skipped.</span>
              )}
              {alreadyContacted > 0 && (
                <span>{alreadyContacted} already contacted — skipped to avoid double-send.</span>
              )}
              <span className="text-[var(--color-warm)]/80">
                Sending to {withEmail.length} of {recipients.length} selected.
              </span>
            </div>
          </div>
        )}

        {/* Single-lead email override */}
        {single && (
          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
              Recipient email
            </label>
            <input
              className={inputClass}
              value={overrideEmail}
              onChange={(e) => setOverrideEmail(e.target.value)}
              placeholder={single.contact_email || "no@email.on-file"}
            />
            {!single.contact_email && (
              <span className="text-[11px] text-[var(--color-text-tertiary)]">
                This lead has no email on file. Paste one above to send.
              </span>
            )}
          </div>
        )}

        {/* Template picker */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
            Template
          </label>
          {noTemplates ? (
            <div className="text-[12px] text-[var(--color-text-tertiary)]">
              You have no templates yet. Open the Templates page to create one.
            </div>
          ) : (
            <select
              className={inputClass}
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
            >
              {templatesQ.data?.templates.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          )}
        </div>

        {/* Preview */}
        {currentTemplate && (
          <div className="flex flex-col gap-2">
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
              Preview {isBulk ? `(using first recipient: ${recipients[0]?.company_name || "—"})` : ""}
            </div>
            <div className="border border-[var(--color-border)] rounded-[var(--radius-sm)] p-3 bg-[var(--color-surface-raised)]/50">
              <div className="text-[12px] font-semibold text-[var(--color-text-primary)] mb-2">
                {previewSubject}
              </div>
              <div className="text-[12px] text-[var(--color-text-secondary)] whitespace-pre-wrap leading-relaxed">
                {previewBody}
              </div>
            </div>
          </div>
        )}

        {/* Result banner */}
        {result && (
          <div
            className={
              "flex gap-2 items-start text-[12px] p-2.5 rounded-[var(--radius-sm)] " +
              (result.startsWith("✓") || result.startsWith("Sent")
                ? "bg-[var(--color-accent)]/15 text-[var(--color-accent)]"
                : "bg-[var(--color-hot)]/15 text-[var(--color-hot)]")
            }
          >
            {result.startsWith("✓") || result.startsWith("Sent") ? (
              <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            )}
            <span>{result}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-1">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            onClick={handleSend}
            disabled={isPending || noTemplates || !currentTemplate}
          >
            <Send className="w-3.5 h-3.5 mr-1.5" />
            {isPending
              ? "Sending…"
              : isBulk
                ? `Send to ${withEmail.length}`
                : "Send"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
