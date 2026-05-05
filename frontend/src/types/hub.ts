export interface HubStats {
  pipeline_total_usd: number;
  won_total_usd: number;
  this_week_usd: number;
  response_rate: number;
  count_total: number;
  count_pipeline: number;
  count_won: number;
}

export interface PulseSource {
  source: string;
  status: "live" | "idle" | "error";
  label: string;
  last_fetch: string | null;
  today_count: number;
}

export interface PulseStatusResponse {
  sources: PulseSource[];
}

export type ActivityEventKind =
  | "scan_running"
  | "scan_completed"
  | "scan_failed"
  | "lead_added";

export interface ActivityEvent {
  id: string;
  kind: ActivityEventKind;
  ts: string;
  // scan_* fields
  sources?: string[];
  keywords?: string[];
  leads_found?: number;
  error?: string | null;
  // lead_added fields
  title?: string;
  source?: string;
  value_usd?: number;
  priority?: "hot" | "warm" | "cold";
}

export interface ActivityResponse {
  events: ActivityEvent[];
}
