export interface SourceSummary {
  source: string;
  enabled: boolean;
  status: "live" | "idle" | "error";
  label: string;
  last_fetch: string | null;
  last_error: string | null;
  today_count: number;
  today_value_usd: number;
  seven_day_series: number[];
}

export interface SourcesResponse {
  sources: SourceSummary[];
}

export interface SavedSearch {
  id: string;
  name: string;
  /** "direct" = job-board scrape (keywords-driven).
   *  "cold"   = SMB-prospect scrape (location + niche-driven). */
  type: "direct" | "cold";
  keywords: string[];
  sources: string[];
  /** Cold-only: list of "City, ST" entries. */
  locations: string[];
  /** Cold-only: niche keys from /api/cold/niches. */
  niches: string[];
  source_configs?: Record<string, unknown>;
  frequency: string;
  max_results: number;
  is_paused: boolean;
  last_run_at: string | null;
}

export interface NicheOption {
  key: string;
  label: string;
  tier: number;
  category: string;
  keywords: string[];
}
