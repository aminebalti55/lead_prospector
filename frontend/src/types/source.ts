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
  keywords: string[];
  sources: string[];
  source_configs?: Record<string, unknown>;
  frequency: string;
  max_results: number;
  enabled: boolean;
  last_run: string | null;
}
