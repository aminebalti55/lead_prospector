export type Stage =
  | "new"
  | "researching"
  | "contacted"
  | "replied"
  | "meeting"
  | "won"
  | "lost";

export type OpportunityType = "direct" | "cold";
export type Priority = "hot" | "warm" | "cold";

export interface Opportunity {
  id: string;
  type: OpportunityType;
  source: string;
  title: string;
  description: string;
  url: string;
  posted_date: string | null;
  company_name: string;
  location: string;
  contact_email: string;
  contact_phone: string;
  score: number;
  priority: Priority;
  stage: Stage;
  estimated_value_usd: number;
  matched_skills: string[];
  budget_signal: string;
  urgency_signal: string;
  pain_tags: string[];
  notes: string;
  source_file: string;
  raw_lead_id: string;
}

export interface OpportunityListResponse {
  opportunities: Opportunity[];
  total: number;
}

export interface OpportunityFilters {
  type?: OpportunityType;
  priority?: Priority;
  stage?: Stage;
  source?: string;
  q?: string;
  sort?: "score" | "value" | "recent";
  limit?: number;
}
