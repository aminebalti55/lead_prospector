import { useState } from "react";
import {
  ExternalLink, Mail, Phone, MapPin, Calendar,
  CheckCircle2, MessageSquare, CalendarCheck, Trophy, X as XIcon,
} from "lucide-react";
import { Opportunity, Stage } from "../../types/opportunity";
import { Button, Pill, MoneyValue, StatusDot, Card } from "../../design/primitives";
import { useUpdateStage } from "../../api/opportunities";
import { SendTemplateModal } from "./SendTemplateModal";

const STAGES: Stage[] = ["new", "researching", "contacted", "replied", "meeting", "won", "lost"];

/** Stage labels are context-sensitive. A `direct` (job) lead in 'contacted'
 * means "I applied", while a `cold` (prospect) lead in 'contacted' means
 * "I sent them an email". The pipeline is the same column; only the UI
 * label changes so the user reads the right verb. */
function stageLabel(stage: Stage, type: "direct" | "cold"): string {
  if (type === "direct") {
    return {
      new: "New",
      researching: "Viewing",
      contacted: "Applied",
      replied: "Heard back",
      meeting: "Interview",
      won: "Hired",
      lost: "Rejected",
    }[stage];
  }
  return {
    new: "New",
    researching: "Researching",
    contacted: "Contacted",
    replied: "Replied",
    meeting: "Meeting",
    won: "Won",
    lost: "Passed",
  }[stage];
}

interface Props {
  opp: Opportunity;
}

export function OpportunityDetail({ opp }: Props) {
  const updateStage = useUpdateStage();
  const [showSend, setShowSend] = useState(false);

  const isDirect = opp.type === "direct";
  const alreadyApplied = opp.stage === "contacted" || ["replied", "meeting", "won", "lost"].includes(opp.stage);

  /** Click "Open original" → mark this lead as 'researching' (= "I'm looking
   * at it") so the inbox row visually flips state. We only auto-advance from
   * 'new' so we never downgrade a stage the user already set manually. */
  function openOriginal() {
    if (!opp.url) return;
    if (opp.stage === "new") {
      updateStage.mutate({ id: opp.id, stage: "researching" });
    }
    window.open(opp.url, "_blank", "noopener,noreferrer");
  }

  function markApplied() {
    updateStage.mutate({ id: opp.id, stage: "contacted" });
  }

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
          {/* Prominent stage badge — visible at a glance */}
          <StageBadge stage={opp.stage} type={opp.type} />
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
            <button
              type="button"
              onClick={openOriginal}
              className="flex items-center gap-1 text-[var(--color-accent)] hover:underline"
            >
              Open original <ExternalLink className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Stage selector — re-labelled for direct vs cold */}
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
              {stageLabel(s, opp.type)}
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

      {/* Quick actions — DIFFERENT for direct vs cold */}
      <div className="flex gap-2 pt-2">
        {isDirect ? (
          <>
            {opp.url && (
              <Button variant="primary" onClick={openOriginal}>
                <ExternalLink className="w-3.5 h-3.5 mr-1.5" />
                Open & Apply on LinkedIn
              </Button>
            )}
            {alreadyApplied ? (
              <Button variant="secondary" disabled>
                <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                {stageLabel(opp.stage, "direct")}
              </Button>
            ) : (
              <Button variant="secondary" onClick={markApplied}>
                <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                Mark as Applied
              </Button>
            )}
            <Button
              variant="ghost"
              onClick={() => updateStage.mutate({ id: opp.id, stage: "lost" })}
            >
              Not interested
            </Button>
          </>
        ) : (
          <>
            {opp.url && (
              <Button variant="primary" onClick={openOriginal}>
                Open site
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
          </>
        )}
      </div>

      {showSend && (
        <SendTemplateModal recipients={[opp]} onClose={() => setShowSend(false)} />
      )}
    </div>
  );
}

/** Visible-at-a-glance stage chip in the header. Color-coded by phase:
 *  green for progressing (applied/replied/meeting/won), red for lost,
 *  neutral for new/researching. */
function StageBadge({ stage, type }: { stage: Stage; type: "direct" | "cold" }) {
  const label = stageLabel(stage, type);
  if (stage === "new") return null;

  const config: Record<Stage, { tone: "accent" | "warm" | "hot" | "neutral"; icon: React.ReactNode }> = {
    new: { tone: "neutral", icon: null },
    researching: { tone: "neutral", icon: null },
    contacted: { tone: "accent", icon: <CheckCircle2 className="w-3 h-3" /> },
    replied: { tone: "accent", icon: <MessageSquare className="w-3 h-3" /> },
    meeting: { tone: "accent", icon: <CalendarCheck className="w-3 h-3" /> },
    won: { tone: "accent", icon: <Trophy className="w-3 h-3" /> },
    lost: { tone: "hot", icon: <XIcon className="w-3 h-3" /> },
  };
  const { tone, icon } = config[stage];
  return (
    <Pill tone={tone}>
      <span className="flex items-center gap-1">
        {icon}
        {label}
      </span>
    </Pill>
  );
}
