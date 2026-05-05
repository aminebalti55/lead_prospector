import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { Button, Card } from "../../design/primitives";
import { useSettings, useUpdateSettings } from "../../api/settings";
import type { Settings } from "../../types/settings";

const EMPTY_SETTINGS: Settings = {
  profile: { name: "", skills: [], services: [], hourly_rate: 0, min_budget: 0 },
  email: { smtp_host: "smtp.gmail.com", smtp_port: 587, smtp_user: "", smtp_password: "", sender_name: "", from_email: "" },
  scraping: { proxy_url: null, max_concurrent: 5 },
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">{label}</label>
      {children}
    </div>
  );
}

const inputClass =
  "h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)]";

export function SettingsPage() {
  const { data, isLoading } = useSettings();
  const update = useUpdateSettings();
  const [draft, setDraft] = useState<Settings>(EMPTY_SETTINGS);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    if (data) setDraft(data);
  }, [data]);

  async function save() {
    await update.mutateAsync(draft);
    setSavedAt(Date.now());
    setTimeout(() => setSavedAt(null), 2500);
  }

  if (isLoading) {
    return (
      <div className="p-6 text-[12px] text-[var(--color-text-tertiary)]">Loading…</div>
    );
  }

  return (
    <div className="p-6 flex flex-col gap-4 w-full">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Settings</div>
          <div className="text-[11px] text-[var(--color-text-tertiary)]">
            Profile, email, and scraping configuration
          </div>
        </div>
        <div className="flex items-center gap-2">
          {savedAt && (
            <span className="text-[11px] text-[var(--color-accent)]">Saved</span>
          )}
          <Button variant="primary" size="md" onClick={save} disabled={update.isPending}>
            <Save className="w-3.5 h-3.5" />
            {update.isPending ? "Saving…" : "Save settings"}
          </Button>
        </div>
      </div>

      {/* Profile */}
      <Card className="p-5 flex flex-col gap-3">
        <h2 className="text-[13px] font-semibold text-[var(--color-text-primary)]">Profile</h2>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Your name">
            <input className={inputClass} value={draft.profile.name}
              onChange={(e) => setDraft({ ...draft, profile: { ...draft.profile, name: e.target.value } })} />
          </Field>
          <Field label="Hourly rate (USD)">
            <input type="number" className={inputClass} value={draft.profile.hourly_rate}
              onChange={(e) => setDraft({ ...draft, profile: { ...draft.profile, hourly_rate: parseInt(e.target.value) || 0 } })} />
          </Field>
          <Field label="Skills (comma-separated)">
            <input className={inputClass} value={draft.profile.skills.join(", ")}
              onChange={(e) => setDraft({ ...draft, profile: { ...draft.profile, skills: e.target.value.split(",").map(s => s.trim()).filter(Boolean) } })} />
          </Field>
          <Field label="Services (comma-separated)">
            <input className={inputClass} value={draft.profile.services.join(", ")}
              onChange={(e) => setDraft({ ...draft, profile: { ...draft.profile, services: e.target.value.split(",").map(s => s.trim()).filter(Boolean) } })} />
          </Field>
          <Field label="Min budget (USD)">
            <input type="number" className={inputClass} value={draft.profile.min_budget}
              onChange={(e) => setDraft({ ...draft, profile: { ...draft.profile, min_budget: parseInt(e.target.value) || 0 } })} />
          </Field>
        </div>
      </Card>

      {/* Email */}
      <Card className="p-5 flex flex-col gap-3">
        <h2 className="text-[13px] font-semibold text-[var(--color-text-primary)]">Email (SMTP)</h2>
        <div className="grid grid-cols-2 gap-3">
          <Field label="SMTP host">
            <input className={inputClass} value={draft.email.smtp_host}
              onChange={(e) => setDraft({ ...draft, email: { ...draft.email, smtp_host: e.target.value } })} />
          </Field>
          <Field label="SMTP port">
            <input type="number" className={inputClass} value={draft.email.smtp_port}
              onChange={(e) => setDraft({ ...draft, email: { ...draft.email, smtp_port: parseInt(e.target.value) || 587 } })} />
          </Field>
          <Field label="SMTP user / email">
            <input className={inputClass} value={draft.email.smtp_user}
              onChange={(e) => setDraft({ ...draft, email: { ...draft.email, smtp_user: e.target.value } })} />
          </Field>
          <Field label="SMTP password">
            <input type="password" className={inputClass} value={draft.email.smtp_password}
              placeholder={draft.email.smtp_password === "••••••••" ? "(set — leave blank to keep)" : "(not set)"}
              onChange={(e) => setDraft({ ...draft, email: { ...draft.email, smtp_password: e.target.value } })} />
          </Field>
          <Field label="Sender name">
            <input className={inputClass} value={draft.email.sender_name}
              onChange={(e) => setDraft({ ...draft, email: { ...draft.email, sender_name: e.target.value } })} />
          </Field>
          <Field label="From email">
            <input className={inputClass} value={draft.email.from_email}
              onChange={(e) => setDraft({ ...draft, email: { ...draft.email, from_email: e.target.value } })} />
          </Field>
        </div>
        <p className="text-[11px] text-[var(--color-text-tertiary)]">
          Leave password blank to keep the existing one. Mask "••••••••" means a password is set.
        </p>
      </Card>

      {/* Scraping */}
      <Card className="p-5 flex flex-col gap-3">
        <h2 className="text-[13px] font-semibold text-[var(--color-text-primary)]">Scraping</h2>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Proxy URL (optional)">
            <input className={inputClass} value={draft.scraping.proxy_url ?? ""}
              onChange={(e) => setDraft({ ...draft, scraping: { ...draft.scraping, proxy_url: e.target.value || null } })} />
          </Field>
          <Field label="Max concurrent scrapers">
            <input type="number" className={inputClass} value={draft.scraping.max_concurrent}
              onChange={(e) => setDraft({ ...draft, scraping: { ...draft.scraping, max_concurrent: parseInt(e.target.value) || 5 } })} />
          </Field>
        </div>
      </Card>
    </div>
  );
}
