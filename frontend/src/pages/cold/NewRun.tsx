import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { Button } from "../../components/Button";
import { useCreateColdRun } from "../../api/cold";

const NICHES = [
  { id: "plumbing", label: "Plumbing" },
  { id: "dental", label: "Dental" },
  { id: "pest_control", label: "Pest Control" },
  { id: "hvac", label: "HVAC" },
  { id: "roofing", label: "Roofing" },
  { id: "landscaping", label: "Landscaping" },
];

const SCRAPERS = [
  { id: "google_maps", label: "Google Maps" },
  { id: "yelp", label: "Yelp" },
  { id: "bbb", label: "BBB" },
  { id: "yellowpages", label: "YellowPages" },
  { id: "manta", label: "Manta" },
];

export function NewColdRun() {
  const navigate = useNavigate();
  const createRun = useCreateColdRun();

  const [locations, setLocations] = useState("");
  const [selectedNiches, setSelectedNiches] = useState<string[]>([]);
  const [selectedScrapers, setSelectedScrapers] = useState<string[]>(["google_maps"]);
  const [maxResults, setMaxResults] = useState(50);
  const [fetchEmails, setFetchEmails] = useState(true);

  function toggleItem(list: string[], item: string): string[] {
    return list.includes(item) ? list.filter((i) => i !== item) : [...list, item];
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload = {
      locations: locations.split(",").map((l) => l.trim()).filter(Boolean),
      niches: selectedNiches,
      scrapers: selectedScrapers,
      max_results: maxResults,
      fetch_emails: fetchEmails,
    };
    await createRun.mutateAsync(payload);
    navigate("/cold/runs");
  }

  return (
    <div>
      <PageHeader title="New Scraping Run" subtitle="Configure and launch a cold outreach scraping run" />

      <form
        onSubmit={handleSubmit}
        className="max-w-2xl bg-surface rounded-xl border border-border p-7 space-y-7 shadow-[--shadow-sm]"
      >
        <div>
          <label className="block text-sm font-semibold text-text-primary mb-2">
            Locations
          </label>
          <input
            type="text"
            placeholder="e.g. Austin TX, Miami FL, Denver CO"
            value={locations}
            onChange={(e) => setLocations(e.target.value)}
            className="w-full text-sm border border-border rounded-lg px-3.5 py-2.5 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
            required
          />
          <p className="text-xs text-text-tertiary mt-1.5 font-medium">
            Comma-separated list of cities/regions
          </p>
        </div>

        <div>
          <label className="block text-sm font-semibold text-text-primary mb-2.5">
            Niches
          </label>
          <div className="flex flex-wrap gap-2">
            {NICHES.map((n) => (
              <label
                key={n.id}
                className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border text-sm font-medium cursor-pointer transition-all duration-150 ${
                  selectedNiches.includes(n.id)
                    ? "border-primary bg-primary-light text-primary"
                    : "border-border bg-surface text-text-secondary hover:border-border-strong hover:text-text-primary"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedNiches.includes(n.id)}
                  onChange={() => setSelectedNiches(toggleItem(selectedNiches, n.id))}
                  className="sr-only"
                />
                {n.label}
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-semibold text-text-primary mb-2.5">
            Scrapers
          </label>
          <div className="flex flex-wrap gap-2">
            {SCRAPERS.map((s) => (
              <label
                key={s.id}
                className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border text-sm font-medium cursor-pointer transition-all duration-150 ${
                  selectedScrapers.includes(s.id)
                    ? "border-primary bg-primary-light text-primary"
                    : "border-border bg-surface text-text-secondary hover:border-border-strong hover:text-text-primary"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedScrapers.includes(s.id)}
                  onChange={() => setSelectedScrapers(toggleItem(selectedScrapers, s.id))}
                  className="sr-only"
                />
                {s.label}
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-semibold text-text-primary mb-2">
            Max Results: <span className="text-primary">{maxResults}</span>
          </label>
          <input
            type="range"
            min={10}
            max={500}
            step={10}
            value={maxResults}
            onChange={(e) => setMaxResults(Number(e.target.value))}
            className="w-full accent-primary"
          />
          <div className="flex justify-between text-xs text-text-tertiary mt-1 font-medium">
            <span>10</span>
            <span>500</span>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <input
            type="checkbox"
            id="fetchEmails"
            checked={fetchEmails}
            onChange={(e) => setFetchEmails(e.target.checked)}
            className="accent-primary w-4 h-4 rounded"
          />
          <label htmlFor="fetchEmails" className="text-sm text-text-primary font-medium">
            Fetch email addresses (slower but recommended)
          </label>
        </div>

        <div className="flex gap-3 pt-3 border-t border-border">
          <Button type="submit" disabled={createRun.isPending}>
            {createRun.isPending ? "Starting..." : "Start Run"}
          </Button>
          <Button type="button" variant="secondary" onClick={() => navigate("/cold/runs")}>
            Cancel
          </Button>
        </div>

        {createRun.isError && (
          <p className="text-sm text-hot font-medium">
            Failed to start run. Please try again.
          </p>
        )}
      </form>
    </div>
  );
}
