export type RunCreateRequest = {
  locations: string[];
  niches: Array<"plumbing" | "dental" | "pest_control">;
  skip_audit: boolean;
  fetch_details: boolean;
  fetch_emails: boolean;
  skip_scrapers: string[];
  output_format: "xlsx" | "csv" | "both";
  max_results: number;
};

export type RunCreateResponse = {
  run_id: string;
  status: "queued" | "running" | "completed" | "failed";
  created_at: string;
};

export type ProgressStep = {
  step: string;
  status: "pending" | "running" | "completed" | "failed";
  message: string;
  count: number;
  started_at?: string | null;
  completed_at?: string | null;
};

export type RunProgress = {
  current_phase: string;
  current_step: string;
  progress_percent: number;
  leads_found: number;
  emails_extracted: number;
  websites_audited: number;
  steps: ProgressStep[];
  logs: string[];
};

export type RunStatusResponse = {
  run_id: string;
  status: "queued" | "running" | "completed" | "failed";
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  params: RunCreateRequest;
  output_files: string[];
  error?: string | null;
  progress?: RunProgress | null;
};

export type OutputFileInfo = {
  name: string;
  modified_at: string;
  size_bytes: number;
};

export type OutputFilesResponse = {
  files: OutputFileInfo[];
};

export type LeadsResponse = {
  file: string;
  columns: string[];
  rows: Array<Record<string, unknown>>;
};

export type LeadUpdateRequest = Partial<{
  Outreach_Status: string;
  Notes: string;
  Owner: string;
  Last_Contacted: string;
  Follow_Up_Date: string;
}>;

// Dashboard Stats
export type NicheBreakdown = {
  niche: string;
  count: number;
  hot: number;
  warm: number;
  cold: number;
};

export type SourceBreakdown = {
  source: string;
  count: number;
};

export type ScoreDistribution = {
  range: string;
  count: number;
};

export type DashboardStats = {
  total_files: number;
  total_leads: number;
  total_emails: number;
  hot_leads: number;
  warm_leads: number;
  cold_leads: number;
  avg_score: number;
  leads_by_niche: NicheBreakdown[];
  leads_by_source: SourceBreakdown[];
  score_distribution: ScoreDistribution[];
  recent_runs: number;
  conversion_rate: number;
};

// Email
export type EmailTemplate = {
  id: string;
  name: string;
  subject: string;
  body: string;
};

export type EmailTemplatesResponse = {
  templates: EmailTemplate[];
};

export type EmailSendRequest = {
  to_email: string;
  to_name: string;
  subject: string;
  body: string;
  lead_id?: string;
  filename?: string;  // Excel file to update
};

export type EmailSendResponse = {
  success: boolean;
  message: string;
  sent_at?: string | null;
};

export type EmailPreviewRequest = {
  template_id: string;
  variables: Record<string, string>;
};

// Batch Email
export type BatchEmailRecipient = {
  to_email: string;
  to_name: string;
  lead_id?: string;
  variables: Record<string, string>;
};

export type BatchEmailRequest = {
  template_id: string;
  recipients: BatchEmailRecipient[];
  custom_subject?: string;
  custom_body?: string;
  delay_seconds?: number;
  filename?: string;  // Excel file to update after sending
};

export type BatchEmailResult = {
  to_email: string;
  to_name: string;
  success: boolean;
  message: string;
  sent_at?: string | null;
};

export type BatchEmailResponse = {
  total: number;
  sent: number;
  failed: number;
  results: BatchEmailResult[];
};

// Lead with computed quality score
export type Lead = Record<string, unknown> & {
  Lead_ID?: string;
  Business_Name?: string;
  Email?: string;
  Phone?: string;
  Website?: string;
  City?: string;
  State?: string;
  Niche?: string;
  Priority?: string;
  Score?: number;
  Recommended_Offer?: string;
  Pain_Tags?: string;
  Outreach_Status?: string;
  quality_score?: number;
  quality_tier?: "excellent" | "good" | "fair" | "poor";
};
