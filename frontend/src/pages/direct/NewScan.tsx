import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { Button } from "../../components/Button";
import { useCreateDirectScan, useCreateSavedSearch } from "../../api/direct";
import { X, Sparkles, Globe, SlidersHorizontal, RotateCw, Zap } from "lucide-react";

// ── Keyword bank — real search terms people use on LinkedIn, Reddit, etc. ──
const KEYWORD_SUGGESTIONS: Record<string, string[]> = {
  // ── How people actually search on LinkedIn/Reddit ──
  "React / Next.js": [
    "hiring react developer",
    "react next.js",
    "nextjs freelancer",
    "react typescript remote",
    "senior react engineer",
    "need react developer ASAP",
    "react frontend contract",
    "[Hiring] react developer",
    "looking for someone who knows react",
    "next.js project help",
    "react native cross platform",
    "remix react",
  ],
  "Node / NestJS / Express": [
    "node.js developer",
    "nestjs backend",
    "express API developer",
    "node typescript backend",
    "hiring node developer remote",
    "need backend engineer node",
    "nestjs microservices",
    "node.js freelancer available",
    "[Hiring] backend node",
    "REST API node express",
  ],
  "PHP / Laravel / Symfony": [
    "PHP developer needed",
    "laravel freelancer",
    "symfony developer",
    "hiring PHP developer",
    "laravel API backend",
    "PHP legacy migration",
    "need laravel developer",
    "PHP e-commerce developer",
    "wordpress plugin developer PHP",
    "[Hiring] PHP laravel",
  ],
  "Python / FastAPI / Django": [
    "python developer remote",
    "fastapi backend",
    "django developer needed",
    "hiring python engineer",
    "python automation script",
    "python web scraping",
    "python API development",
    "flask fastapi",
    "[Hiring] python developer",
    "python data pipeline",
  ],
  "Java / Spring Boot / .NET": [
    "java developer",
    "spring boot developer",
    "hiring java backend",
    "java microservices",
    "spring boot API",
    "J2EE developer",
    "kotlin backend",
    ".NET developer",
    "C# developer needed",
    "asp.net developer",
    "java freelancer remote",
    "[Hiring] java spring boot",
    "need java developer",
    "angular java full stack",
    "hibernate spring developer",
  ],
  "Full Stack / SaaS / MVP": [
    "full stack developer",
    "looking for technical co-founder",
    "need MVP built",
    "SaaS developer",
    "build my app",
    "startup needs developer",
    "web app from scratch",
    "full stack freelancer",
    "MERN stack",
    "T3 stack developer",
    "who can build my startup idea",
    "need someone to build a platform",
    "looking for a dev to build",
  ],
  "Mobile Apps": [
    "react native developer",
    "flutter developer",
    "mobile app developer",
    "iOS android app",
    "need mobile app built",
    "cross platform mobile",
    "expo react native",
    "mobile app freelancer",
    "[Hiring] mobile developer",
  ],
  "AI / ChatGPT / LLM": [
    "AI developer",
    "ChatGPT integration",
    "LLM API developer",
    "need AI chatbot built",
    "OpenAI API integration",
    "AI agent developer",
    "RAG pipeline",
    "LangChain developer",
    "fine-tune model",
    "AI SaaS",
    "build AI tool",
    "GPT wrapper app",
    "vector database embeddings",
    "conversational AI",
    "AI automation",
  ],
  "Automation / Scraping / Bots": [
    "web scraping project",
    "automation developer",
    "build a bot",
    "need web scraper",
    "workflow automation",
    "n8n make zapier developer",
    "RPA developer",
    "data extraction",
    "automate my business process",
    "scraping freelancer",
    "selenium puppeteer playwright",
    "cron job automation",
    "email automation",
  ],
  "E-commerce / Shopify / WooCommerce": [
    "shopify developer",
    "woocommerce developer",
    "e-commerce website",
    "shopify custom theme",
    "online store developer",
    "stripe payment integration",
    "shopify app developer",
    "headless commerce",
    "magento to shopify migration",
    "need e-commerce site built",
  ],
  "API / Integrations": [
    "API integration developer",
    "connect two systems",
    "stripe API developer",
    "third party API integration",
    "webhook developer",
    "GraphQL developer",
    "microservices",
    "headless CMS developer",
    "Zapier alternative custom",
    "CRM integration developer",
  ],
  // ── French — how Tunisians & Francophones actually search ──
  "Développement Web (FR)": [
    "cherche développeur web",
    "développeur react freelance",
    "développeur next.js",
    "besoin développeur site web",
    "développeur full stack Tunisie",
    "développeur PHP Laravel",
    "développeur node.js freelance",
    "développeur NestJS",
    "cherche dev frontend",
    "développeur backend freelance",
    "refonte site web",
    "création site internet",
    "développeur WordPress",
    "développeur e-commerce",
    "développeur Symfony Tunisie",
    "besoin développeur TypeScript",
  ],
  "Applications & Startups (FR)": [
    "développeur application mobile",
    "besoin développeur SaaS",
    "création application sur mesure",
    "cherche développeur pour startup",
    "développeur MVP",
    "développeur React Native Tunisie",
    "développeur Flutter freelance",
    "créer une plateforme web",
    "développement logiciel sur mesure",
    "besoin prestataire développement",
    "qui peut développer mon application",
    "cherche dev pour projet",
  ],
  "IA & Automatisation (FR)": [
    "développeur intelligence artificielle",
    "intégration ChatGPT",
    "développeur chatbot",
    "automatisation processus",
    "développeur IA Tunisie",
    "web scraping automatisation",
    "automatisation tâches",
    "bot automatique",
    "intégration API IA",
    "développeur Python automatisation",
    "outil IA sur mesure",
  ],
  "Java / .NET (FR)": [
    "développeur Java",
    "développeur Spring Boot",
    "développeur Java Tunisie",
    "cherche développeur Java",
    "développeur .NET C#",
    "développeur J2EE",
    "développeur backend Java",
    "recrute développeur Java Spring",
    "développeur Angular Java",
    "développeur Kotlin",
  ],
  "Freelance & Missions (FR)": [
    "offre mission développeur",
    "freelance développeur disponible",
    "mission développement web",
    "projet développement application",
    "cherche prestataire informatique",
    "sous-traitance développement",
    "TJM développeur",
    "développeur disponible immédiatement",
    "besoin renfort équipe dev",
    "recrute développeur web",
    "CDI développeur Tunisie",
    "stage développeur full stack",
  ],
};

const SOURCES = [
  { id: "reddit", label: "Reddit", icon: "🟠", hasCountry: false },
  { id: "indeed", label: "Indeed", icon: "🔵", hasCountry: true },
  { id: "linkedin", label: "LinkedIn Jobs", icon: "🔷", hasCountry: true },
  { id: "linkedin_posts", label: "LinkedIn Posts", icon: "📣", hasCountry: true },
  { id: "clutch", label: "Clutch", icon: "🟣", hasCountry: false },
  { id: "goodfirms", label: "GoodFirms", icon: "🟢", hasCountry: false },
  { id: "twitter", label: "Twitter/X", icon: "⬛", hasCountry: false },
];

const COUNTRIES = [
  { code: "US", label: "United States" },
  { code: "UK", label: "United Kingdom" },
  { code: "CA", label: "Canada" },
  { code: "AU", label: "Australia" },
  { code: "DE", label: "Germany" },
  { code: "FR", label: "France" },
  { code: "NL", label: "Netherlands" },
  { code: "IN", label: "India" },
  { code: "SG", label: "Singapore" },
  { code: "AE", label: "UAE" },
  { code: "TN", label: "Tunisia" },
  { code: "remote", label: "Remote / Worldwide" },
];

const FREQUENCIES = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "biweekly", label: "Bi-weekly" },
  { value: "monthly", label: "Monthly" },
];

export function NewDirectScan() {
  const navigate = useNavigate();
  const createScan = useCreateDirectScan();
  const createSavedSearch = useCreateSavedSearch();

  const [selectedSources, setSelectedSources] = useState<string[]>(["reddit"]);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestionFilter, setSuggestionFilter] = useState("");
  const [maxResults, setMaxResults] = useState(50);
  const [saveAsRecurring, setSaveAsRecurring] = useState(false);
  const [searchName, setSearchName] = useState("");
  const [frequency, setFrequency] = useState("daily");
  const [linkedinCountry, setLinkedinCountry] = useState("US");
  const [indeedCountry, setIndeedCountry] = useState("US");

  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (suggestionsRef.current && !suggestionsRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function addKeyword(kw: string) {
    const trimmed = kw.trim();
    if (trimmed && !keywords.includes(trimmed)) {
      setKeywords([...keywords, trimmed]);
    }
    setKeywordInput("");
    inputRef.current?.focus();
  }

  function removeKeyword(kw: string) {
    setKeywords(keywords.filter((k) => k !== kw));
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      if (keywordInput.trim()) addKeyword(keywordInput);
    } else if (e.key === "Backspace" && !keywordInput && keywords.length > 0) {
      removeKeyword(keywords[keywords.length - 1]);
    }
  }

  function toggleSource(id: string) {
    setSelectedSources((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  }

  const filteredSuggestions: Record<string, string[]> = {};
  const filterLower = (suggestionFilter || keywordInput).toLowerCase();
  for (const [category, kws] of Object.entries(KEYWORD_SUGGESTIONS)) {
    const filtered = kws.filter(
      (kw) => kw.toLowerCase().includes(filterLower) && !keywords.includes(kw)
    );
    if (filtered.length > 0) filteredSuggestions[category] = filtered;
  }

  const hasCountrySources = selectedSources.some(
    (s) => SOURCES.find((src) => src.id === s)?.hasCountry
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (keywords.length === 0) return;

    const sourceConfigs: Record<string, { country?: string }> = {};
    if (selectedSources.includes("linkedin")) sourceConfigs.linkedin = { country: linkedinCountry };
    if (selectedSources.includes("indeed")) sourceConfigs.indeed = { country: indeedCountry };

    const payload = {
      sources: selectedSources,
      source_configs: sourceConfigs,
      keywords,
      max_results: maxResults,
    };

    await createScan.mutateAsync(payload);

    if (saveAsRecurring && searchName.trim()) {
      await createSavedSearch.mutateAsync({
        name: searchName.trim(),
        sources: selectedSources,
        source_configs: sourceConfigs,
        keywords,
        frequency,
        max_results: maxResults,
        enabled: true,
      });
    }

    navigate("/direct/scans");
  }

  return (
    <div>
      <PageHeader title="New Direct Scan" subtitle="Configure sources, keywords, and filters to find leads" />

      <form onSubmit={handleSubmit} className="space-y-6">

        {/* ═══ Row 1: Sources + Filters side by side ═══ */}
        <div className="grid grid-cols-5 gap-5">

          {/* Left: Sources — takes 3 cols */}
          <div className="col-span-3 bg-surface rounded-xl border border-border p-5 shadow-[--shadow-sm]">
            <div className="flex items-center gap-2 mb-3">
              <Zap size={14} className="text-primary" />
              <span className="text-sm font-semibold text-text-primary">Sources</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {SOURCES.map((s) => (
                <label
                  key={s.id}
                  className={`inline-flex items-center gap-2 px-3 py-2.5 rounded-lg border text-[13px] font-medium cursor-pointer transition-all duration-150 ${
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
                  <span className="text-base leading-none">{s.icon}</span>
                  {s.label}
                </label>
              ))}
            </div>
          </div>

          {/* Right: Filters + Settings — takes 2 cols */}
          <div className="col-span-2 space-y-5">

            {/* Country filters */}
            <div className="bg-surface rounded-xl border border-border p-5 shadow-[--shadow-sm]">
              <div className="flex items-center gap-2 mb-3">
                <Globe size={14} className="text-primary" />
                <span className="text-sm font-semibold text-text-primary">Location</span>
              </div>
              {hasCountrySources ? (
                <div className="space-y-3">
                  {selectedSources.includes("linkedin") && (
                    <div>
                      <label className="block text-[12px] font-semibold text-text-tertiary uppercase tracking-wider mb-1">LinkedIn</label>
                      <select
                        value={linkedinCountry}
                        onChange={(e) => setLinkedinCountry(e.target.value)}
                        className="w-full text-sm font-medium border border-border rounded-lg px-3 py-2 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors"
                      >
                        {COUNTRIES.map((c) => (
                          <option key={c.code} value={c.code}>{c.label}</option>
                        ))}
                      </select>
                    </div>
                  )}
                  {selectedSources.includes("indeed") && (
                    <div>
                      <label className="block text-[12px] font-semibold text-text-tertiary uppercase tracking-wider mb-1">Indeed</label>
                      <select
                        value={indeedCountry}
                        onChange={(e) => setIndeedCountry(e.target.value)}
                        className="w-full text-sm font-medium border border-border rounded-lg px-3 py-2 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors"
                      >
                        {COUNTRIES.map((c) => (
                          <option key={c.code} value={c.code}>{c.label}</option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-text-tertiary font-medium">
                  Select LinkedIn or Indeed to enable country filtering.
                </p>
              )}
            </div>

            {/* Max results + recurring compact */}
            <div className="bg-surface rounded-xl border border-border p-5 shadow-[--shadow-sm]">
              <div className="flex items-center gap-2 mb-3">
                <SlidersHorizontal size={14} className="text-primary" />
                <span className="text-sm font-semibold text-text-primary">Settings</span>
              </div>
              <div>
                <label className="block text-[12px] font-semibold text-text-tertiary uppercase tracking-wider mb-1">
                  Max results: <span className="text-primary normal-case">{maxResults}</span>
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
                <div className="flex justify-between text-[11px] text-text-muted mt-0.5 font-medium">
                  <span>10</span>
                  <span>500</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ═══ Row 2: Keywords — full width with inline suggestions ═══ */}
        <div className="grid grid-cols-5 gap-5" ref={suggestionsRef}>

          {/* Left: Tag input — 3 cols */}
          <div className="col-span-3 bg-surface rounded-xl border border-border p-5 shadow-[--shadow-sm]">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Sparkles size={14} className="text-primary" />
                <span className="text-sm font-semibold text-text-primary">Keywords</span>
                {keywords.length > 0 && (
                  <span className="text-[11px] font-semibold text-primary bg-primary-light px-1.5 py-0.5 rounded">
                    {keywords.length}
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => { setShowSuggestions(!showSuggestions); setSuggestionFilter(""); }}
                className="text-[12px] font-semibold text-primary hover:text-primary-hover transition-colors cursor-pointer"
              >
                {showSuggestions ? "Hide bank" : "Keyword bank →"}
              </button>
            </div>

            <div
              className="min-h-[120px] max-h-[200px] overflow-auto flex flex-wrap gap-1.5 items-start content-start border border-border rounded-lg px-3 py-2.5 bg-bg/50 focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all cursor-text"
              onClick={() => inputRef.current?.focus()}
            >
              {keywords.map((kw) => (
                <span
                  key={kw}
                  className="inline-flex items-center gap-1 pl-2.5 pr-1.5 py-1 rounded-md text-[13px] font-medium bg-primary-light text-primary border border-primary/20 shrink-0"
                >
                  {kw}
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); removeKeyword(kw); }}
                    className="ml-0.5 p-0.5 rounded hover:bg-primary/10 transition-colors cursor-pointer"
                  >
                    <X size={11} />
                  </button>
                </span>
              ))}
              <input
                ref={inputRef}
                type="text"
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => { if (keywords.length === 0) setShowSuggestions(true); }}
                placeholder={keywords.length === 0 ? "Type and press Enter..." : "Add more..."}
                className="flex-1 min-w-[140px] text-sm bg-transparent text-text-primary placeholder:text-text-muted focus:outline-none py-0.5"
              />
            </div>
            <p className="text-[11px] text-text-tertiary mt-1.5 font-medium">
              Press Enter to add custom keywords. Backspace to remove last.
            </p>
          </div>

          {/* Right: Suggestions panel — 2 cols, always visible when toggled */}
          <div className="col-span-2">
            {showSuggestions ? (
              <div className="bg-surface rounded-xl border border-border shadow-[--shadow-sm] overflow-hidden flex flex-col" style={{ maxHeight: "calc(120px + 90px + 2.5rem)" }}>
                <div className="bg-bg/50 border-b border-border p-3 shrink-0">
                  <input
                    type="text"
                    value={suggestionFilter}
                    onChange={(e) => setSuggestionFilter(e.target.value)}
                    placeholder="Filter suggestions..."
                    className="w-full text-sm border border-border rounded-lg px-3 py-1.5 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                  />
                </div>

                <div className="flex-1 overflow-auto p-3 space-y-3">
                  {Object.keys(filteredSuggestions).length === 0 ? (
                    <p className="text-xs text-text-tertiary text-center py-4">No matching suggestions.</p>
                  ) : (
                    Object.entries(filteredSuggestions).map(([category, kws]) => (
                      <div key={category}>
                        <p className="text-[10px] font-bold uppercase tracking-wider text-text-tertiary mb-1.5">
                          {category}
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {kws.map((kw) => (
                            <button
                              key={kw}
                              type="button"
                              onClick={() => addKeyword(kw)}
                              className="inline-flex items-center px-2 py-1 rounded-md border border-border bg-bg text-[12px] font-medium text-text-secondary hover:border-primary hover:text-primary hover:bg-primary-light transition-all duration-100 cursor-pointer"
                            >
                              + {kw}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </div>

                <div className="bg-bg/80 border-t border-border px-3 py-2 flex justify-between items-center shrink-0">
                  <span className="text-[11px] text-text-tertiary font-medium">
                    {keywords.length} selected
                  </span>
                  <button
                    type="button"
                    onClick={() => setShowSuggestions(false)}
                    className="text-[11px] font-semibold text-primary hover:text-primary-hover transition-colors cursor-pointer"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <div
                onClick={() => { setShowSuggestions(true); setSuggestionFilter(""); }}
                className="bg-surface rounded-xl border border-dashed border-border-strong p-5 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-bg/50 transition-colors h-full min-h-[120px]"
              >
                <Sparkles size={20} className="text-text-muted mb-2" />
                <p className="text-sm font-semibold text-text-secondary">Keyword Bank</p>
                <p className="text-[11px] text-text-tertiary mt-0.5">Click to browse 50+ suggested keywords</p>
              </div>
            )}
          </div>
        </div>

        {/* ═══ Row 3: Recurring + Submit — compact bottom bar ═══ */}
        <div className="bg-surface rounded-xl border border-border p-5 shadow-[--shadow-sm]">
          <div className="flex items-start justify-between gap-6">

            {/* Left: Recurring toggle */}
            <div className="flex-1">
              <div className="flex items-center gap-2.5">
                <input
                  type="checkbox"
                  id="saveRecurring"
                  checked={saveAsRecurring}
                  onChange={(e) => setSaveAsRecurring(e.target.checked)}
                  className="accent-primary w-4 h-4 rounded"
                />
                <label htmlFor="saveRecurring" className="text-sm text-text-primary font-semibold cursor-pointer flex items-center gap-1.5">
                  <RotateCw size={13} className="text-text-tertiary" />
                  Save as recurring search
                </label>
              </div>

              {saveAsRecurring && (
                <div className="mt-3 flex gap-3 pl-6">
                  <div className="flex-1">
                    <label className="block text-[12px] font-semibold text-text-tertiary uppercase tracking-wider mb-1">Name</label>
                    <input
                      type="text"
                      placeholder="e.g. React freelance gigs"
                      value={searchName}
                      onChange={(e) => setSearchName(e.target.value)}
                      className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                      required={saveAsRecurring}
                    />
                  </div>
                  <div className="w-36">
                    <label className="block text-[12px] font-semibold text-text-tertiary uppercase tracking-wider mb-1">Frequency</label>
                    <select
                      value={frequency}
                      onChange={(e) => setFrequency(e.target.value)}
                      className="w-full text-sm font-medium border border-border rounded-lg px-3 py-2 bg-surface text-text-primary cursor-pointer hover:border-border-strong transition-colors"
                    >
                      {FREQUENCIES.map((f) => (
                        <option key={f.value} value={f.value}>{f.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              )}
            </div>

            {/* Right: Action buttons */}
            <div className="flex gap-2.5 items-start pt-0.5 shrink-0">
              <Button type="button" variant="secondary" onClick={() => navigate("/direct/scans")}>
                Cancel
              </Button>
              <Button type="submit" disabled={createScan.isPending || keywords.length === 0}>
                {createScan.isPending ? "Starting..." : `Start Scan${keywords.length > 0 ? ` (${keywords.length})` : ""}`}
              </Button>
            </div>
          </div>

          {createScan.isError && (
            <p className="text-sm text-hot font-medium mt-3">Failed to start scan. Please try again.</p>
          )}
        </div>
      </form>
    </div>
  );
}
