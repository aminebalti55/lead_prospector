import { useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import {
  useSavedSearches,
  useCreateSavedSearch,
  useDeleteSavedSearch,
} from "../../api/direct";
import { Trash2 } from "lucide-react";

interface SavedSearch {
  id: string;
  name: string;
  keywords: string[];
  sources: string[];
  frequency: string;
  last_run: string;
  enabled: boolean;
}

const SOURCES = [
  { id: "reddit", label: "Reddit" },
  { id: "indeed", label: "Indeed" },
  { id: "linkedin", label: "LinkedIn" },
  { id: "clutch", label: "Clutch" },
  { id: "goodfirms", label: "GoodFirms" },
  { id: "twitter", label: "Twitter" },
];

const FREQUENCIES = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "biweekly", label: "Bi-weekly" },
  { value: "monthly", label: "Monthly" },
];

export function SavedSearches() {
  const { data, isLoading } = useSavedSearches();
  const createSearch = useCreateSavedSearch();
  const deleteSearch = useDeleteSavedSearch();

  const searches: SavedSearch[] = data?.searches || [];

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [keywords, setKeywords] = useState("");
  const [selectedSources, setSelectedSources] = useState<string[]>(["reddit"]);
  const [frequency, setFrequency] = useState("daily");

  function toggleSource(id: string) {
    setSelectedSources((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  }

  function resetForm() {
    setName("");
    setKeywords("");
    setSelectedSources(["reddit"]);
    setFrequency("daily");
    setShowForm(false);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const keywordList = keywords.split("\n").map((k) => k.trim()).filter(Boolean);
    await createSearch.mutateAsync({
      name: name.trim(),
      keywords: keywordList,
      sources: selectedSources,
      frequency,
      enabled: true,
    });
    resetForm();
  }

  if (isLoading) {
    return <div className="text-text-secondary text-sm p-8 font-medium">Loading...</div>;
  }

  return (
    <div>
      <PageHeader title="Saved Searches" subtitle="Manage your recurring search configurations">
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "New Search"}
        </Button>
      </PageHeader>

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="max-w-2xl bg-surface rounded-xl border border-border p-7 space-y-6 mb-6 shadow-[--shadow-sm]"
        >
          <div>
            <label className="block text-sm font-semibold text-text-primary mb-1.5">Search Name</label>
            <input
              type="text"
              placeholder="e.g. React freelance gigs"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full text-sm border border-border rounded-lg px-3.5 py-2.5 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-text-primary mb-1.5">Keywords</label>
            <textarea
              placeholder={"web development\nreact developer\nfreelance designer"}
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              rows={4}
              className="w-full text-sm border border-border rounded-lg px-3.5 py-2.5 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none transition-all leading-relaxed"
              required
            />
            <p className="text-xs text-text-tertiary mt-1 font-medium">One keyword per line</p>
          </div>

          <div>
            <label className="block text-sm font-semibold text-text-primary mb-2.5">Sources</label>
            <div className="flex flex-wrap gap-2">
              {SOURCES.map((s) => (
                <label
                  key={s.id}
                  className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border text-sm font-medium cursor-pointer transition-all duration-150 ${
                    selectedSources.includes(s.id)
                      ? "border-primary bg-primary-light text-primary"
                      : "border-border bg-surface text-text-secondary hover:border-border-strong hover:text-text-primary"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedSources.includes(s.id)}
                    onChange={() => toggleSource(s.id)}
                    className="sr-only"
                  />
                  {s.label}
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-text-primary mb-1.5">Frequency</label>
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              className="text-sm font-medium border border-border rounded-lg px-3 py-2.5 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors"
            >
              {FREQUENCIES.map((f) => (
                <option key={f.value} value={f.value}>{f.label}</option>
              ))}
            </select>
          </div>

          <div className="flex gap-3 pt-3 border-t border-border">
            <Button type="submit" disabled={createSearch.isPending}>
              {createSearch.isPending ? "Saving..." : "Save Search"}
            </Button>
            <Button type="button" variant="secondary" onClick={resetForm}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {searches.length === 0 && !showForm ? (
        <EmptyState
          message="No saved searches yet."
          action={{ label: "Create your first saved search", href: "/direct/scans/new" }}
        />
      ) : searches.length > 0 ? (
        <div className="bg-surface rounded-xl border border-border overflow-auto shadow-[--shadow-sm]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-bg/50">
                <th className="px-4 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Name</th>
                <th className="px-4 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Keywords</th>
                <th className="px-4 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Sources</th>
                <th className="px-4 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Frequency</th>
                <th className="px-4 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Last Run</th>
                <th className="px-4 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {searches.map((search) => (
                <tr
                  key={search.id}
                  className="border-b border-border last:border-0 hover:bg-bg/50 transition-colors"
                >
                  <td className="px-4 py-3 text-[13px] font-semibold text-text-primary">
                    {search.name}
                  </td>
                  <td className="px-4 py-3 text-[13px] text-text-secondary max-w-[200px] truncate">
                    {search.keywords?.join(", ")}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 flex-wrap">
                      {search.sources?.map((s) => (
                        <span
                          key={s}
                          className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-primary-light text-primary"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-[13px] text-text-secondary capitalize font-medium">
                    {search.frequency}
                  </td>
                  <td className="px-4 py-3 text-[13px] text-text-secondary">
                    {search.last_run ? new Date(search.last_run).toLocaleDateString() : "\u2014"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold border ${
                        search.enabled
                          ? "bg-success-light text-success border-success/20"
                          : "bg-bg text-text-tertiary border-border"
                      }`}
                    >
                      {search.enabled ? "Active" : "Paused"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => deleteSearch.mutate(search.id)}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-hot hover:text-red-700 transition-colors cursor-pointer"
                    >
                      <Trash2 size={13} />
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
