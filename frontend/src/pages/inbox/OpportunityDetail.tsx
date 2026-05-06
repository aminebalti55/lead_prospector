import { useState } from "react";
import { ExternalLink, Mail, Phone, MapPin, Calendar } from "lucide-react";
import { Opportunity, Stage } from "../../types/opportunity";
import { Button, Pill, MoneyValue, StatusDot, Card } from "../../design/primitives";
import { useUpdateStage } from "../../api/opportunities";
import { SendTemplateModal } from "./SendTemplateModal";

const STAGES: Stage[] = ["new", "researching", "contacted", "replied", "meeting", "won", "lost"];

interface Props {
  opp: Opportunity;
}

export function OpportunityDetail({ opp }: Props) {
  const updateStage = useUpdateStage();
  const [showSend, setShowSend] = useState(false);

  return (
    <div className="flex-1 overflow-auto p-6 flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col gap-3">
        <div className="flex items-start gap-3">
          <StatusDot
            status={opp.priority === "hot" ? "hot" : opp.priority === "warm" ? "warm" : "cold"}
            className="mt-2"
          />
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)] leading-tight flex-1">
            {opp.title || "(no title)"}
          </h1>
          <MoneyValue usd={opp.estimated_value_usd} size="xl" tone="accent" />
        </div>

        <div className="flex flex-wrap items-center gap-2 text-[12px] text-[var(--color-text-secondary)]">
          <Pill tone="neutral">{opp.source}</Pill>
          {opp.company_name && <span>{opp.company_name}</span>}
          {opp.location && (
            <span className="flex items-center gap-1">
              <MapPin className="w-3 h-3" /> {opp.location}
            </span>
          )}
          {opp.posted_date && (
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {new Date(opp.posted_date).toLocaleDateString()}
            </span>
          )}
          {opp.url && (
            <a
              href={opp.url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 text-[var(--color-accent)] hover:underline"
            >
              Open original <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>

      {/* Stage selector */}
      <Card className="p-3">
        <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium mb-2">
          Stage
        </div>
        <div className="flex flex-wrap gap-1">
          {STAGES.map((s) => (
            <button
              key={s}
              type="button"
              disabled={updateStage.isPending}
              onClick={() => updateStage.mutate({ id: opp.id, stage: s })}
              className={
                opp.stage === s
                  ? "px-2.5 h-7 text-[12px] rounded-[var(--radius-sm)] bg-[var(--color-accent)] text-[#0A0A0B] font-medium"
                  : "px-2.5 h-7 text-[12px] rounded-[var(--radius-sm)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-raised)]"
              }
            >
              {s}
            </button>
          ))}
        </div>
      </Card>

      {/* Description */}
      {opp.description && (
        <Card className="p-4">
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium mb-2">
            Description
          </div>
          <p className="text-[13px] text-[var(--color-text-primary)] whitespace-pre-wrap leading-relaxed">
            {opp.description}
          </p>
        </Card>
      )}

      {/* Signals */}
      {(opp.matched_skills.length > 0 || opp.budget_signal || opp.urgency_signal || opp.pain_tags.length > 0) && (
        <Card className="p-4 flex flex-col gap-3">
          {opp.matched_skills.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium mb-1.5">
                Matched skills
              </div>
              <div className="flex flex-wrap gap-1">
                {opp.matched_skills.map((s) => (
                  <Pill key={s} tone="accent">{s}</Pill>
                ))}
              </div>
            </div>
          )}
          {opp.budget_signal && (
            <div className="text-[12px]">
              <span className="text-[var(--color-text-tertiary)]">Budget signal: </span>
              <span className="text-[var(--color-text-primary)]">{opp.budget_signal}</span>
            </div>
          )}
          {opp.urgency_signal && (
            <div className="text-[12px]">
              <span className="text-[var(--color-text-tertiary)]">Urgency: </span>
              <span className="text-[var(--color-text-primary)]">{opp.urgency_signal}</span>
            </div>
          )}
          {opp.pain_tags.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium mb-1.5">
                Pain tags
              </div>
              <div className="flex flex-wrap gap-1">
                {opp.pain_tags.map((t) => (
                  <Pill key={t} tone="warm">{t}</Pill>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Contact */}
      {(opp.contact_email || opp.contact_phone) && (
        <Card className="p-4 flex flex-col gap-2">
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
            Contact
          </div>
          {opp.contact_email && (
            <a
              href={`mailto:${opp.contact_email}`}
              className="text-[13px] text-[var(--color-accent)] hover:underline flex items-center gap-2"
            >
              <Mail className="w-3.5 h-3.5" /> {opp.contact_email}
            </a>
          )}
          {opp.contact_phone && (
            <a
              href={`tel:${opp.contact_phone}`}
              className="text-[13px] text-[var(--color-text-primary)] flex items-center gap-2"
            >
              <Phone className="w-3.5 h-3.5" /> {opp.contact_phone}
            </a>
          )}
        </Card>
      )}

      {/* Quick actions */}
      <div className="flex gap-2 pt-2">
        {opp.url && (
          <Button variant="primary" onClick={() => window.open(opp.url, "_blank")}>
            Reply now
          </Button>
        )}
        <Button variant="secondary" onClick={() => setShowSend(true)}>
          Send template
        </Button>
        <Button
          variant="ghost"
          onClick={() => updateStage.mutate({ id: opp.id, stage: "lost" })}
        >
          Dismiss
        </Button>
      </div>

      {showSend && (
        <SendTemplateModal recipients={[opp]} onClose={() => setShowSend(false)} />
      )}
    </div>
  );
}
