export interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  body: string;
  created_at?: string;
  updated_at?: string;
}

export interface TemplatesResponse {
  templates: EmailTemplate[];
}
