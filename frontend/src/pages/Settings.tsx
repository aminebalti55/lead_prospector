import { useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { Button } from "../components/Button";
import { apiFetch } from "../api/client";
import { CheckCircle } from "lucide-react";

export function SettingsPage() {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [skills, setSkills] = useState("");
  const [services, setServices] = useState("");
  const [rate, setRate] = useState("");
  const [budget, setBudget] = useState("");

  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPass, setSmtpPass] = useState("");
  const [fromEmail, setFromEmail] = useState("");

  const [proxyUrl, setProxyUrl] = useState("");
  const [concurrency, setConcurrency] = useState("3");

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await apiFetch("/settings", {
        method: "PUT",
        body: JSON.stringify({
          profile: { skills, services, rate, budget },
          email: {
            smtp_host: smtpHost,
            smtp_port: Number(smtpPort),
            smtp_user: smtpUser,
            smtp_pass: smtpPass,
            from_email: fromEmail,
          },
          scraping: {
            proxy_url: proxyUrl,
            concurrency: Number(concurrency),
          },
        }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      // error handled silently
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <PageHeader title="Settings" subtitle="Configure your profile, email, and scraping preferences" />

      <form onSubmit={handleSave} className="max-w-2xl space-y-6">
        <section className="bg-surface rounded-xl border border-border p-7 shadow-[--shadow-sm]">
          <h2 className="text-sm font-bold text-text-primary mb-5">Profile</h2>
          <div className="space-y-4">
            <Field label="Skills" value={skills} onChange={setSkills} placeholder="e.g. Web development, SEO, Marketing" />
            <Field label="Services offered" value={services} onChange={setServices} placeholder="e.g. Website redesign, Lead generation" />
            <div className="grid grid-cols-2 gap-4">
              <Field label="Hourly rate ($)" value={rate} onChange={setRate} placeholder="75" type="number" />
              <Field label="Min budget ($)" value={budget} onChange={setBudget} placeholder="500" type="number" />
            </div>
          </div>
        </section>

        <section className="bg-surface rounded-xl border border-border p-7 shadow-[--shadow-sm]">
          <h2 className="text-sm font-bold text-text-primary mb-5">Email (SMTP)</h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Field label="SMTP Host" value={smtpHost} onChange={setSmtpHost} placeholder="smtp.gmail.com" />
              <Field label="SMTP Port" value={smtpPort} onChange={setSmtpPort} placeholder="587" type="number" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Username" value={smtpUser} onChange={setSmtpUser} placeholder="you@example.com" />
              <Field label="Password" value={smtpPass} onChange={setSmtpPass} placeholder="App password" type="password" />
            </div>
            <Field label="From Email" value={fromEmail} onChange={setFromEmail} placeholder="you@example.com" type="email" />
          </div>
        </section>

        <section className="bg-surface rounded-xl border border-border p-7 shadow-[--shadow-sm]">
          <h2 className="text-sm font-bold text-text-primary mb-5">Scraping</h2>
          <div className="space-y-4">
            <Field label="Proxy URL" value={proxyUrl} onChange={setProxyUrl} placeholder="http://proxy:port (optional)" />
            <Field label="Max Concurrent Scrapers" value={concurrency} onChange={setConcurrency} placeholder="3" type="number" />
          </div>
        </section>

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save Settings"}
          </Button>
          {saved && (
            <span className="inline-flex items-center gap-1.5 text-sm text-success font-semibold">
              <CheckCircle size={14} /> Settings saved!
            </span>
          )}
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div>
      <label className="block text-[13px] font-semibold text-text-secondary mb-1.5">
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full text-sm border border-border rounded-lg px-3.5 py-2.5 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
      />
    </div>
  );
}
