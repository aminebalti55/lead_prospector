import axios from "axios";
import type {
  DashboardStats,
  EmailPreviewRequest,
  EmailSendRequest,
  EmailSendResponse,
  EmailTemplatesResponse,
  BatchEmailRequest,
  BatchEmailResponse,
  LeadsResponse,
  LeadUpdateRequest,
  OutputFilesResponse,
  RunCreateRequest,
  RunCreateResponse,
  RunStatusResponse,
} from "./types";

export const api = axios.create({
  baseURL: "/api",
});

// Files
export async function listFiles(): Promise<OutputFilesResponse> {
  const { data } = await api.get<OutputFilesResponse>("/files");
  return data;
}

export async function getLeads(filename: string): Promise<LeadsResponse> {
  const { data } = await api.get<LeadsResponse>(
    `/files/${encodeURIComponent(filename)}/leads`
  );
  return data;
}

export function downloadUrl(filename: string): string {
  return `/api/files/${encodeURIComponent(filename)}/download`;
}

// Runs
export async function createRun(body: RunCreateRequest): Promise<RunCreateResponse> {
  const { data } = await api.post<RunCreateResponse>("/runs", body);
  return data;
}

export async function getRun(runId: string): Promise<RunStatusResponse> {
  const { data } = await api.get<RunStatusResponse>(`/runs/${runId}`);
  return data;
}

// Leads
export async function updateLead(
  filename: string,
  leadId: string,
  patch: LeadUpdateRequest
): Promise<void> {
  await api.patch(
    `/files/${encodeURIComponent(filename)}/leads/${encodeURIComponent(leadId)}`,
    patch
  );
}

// Stats
export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>("/stats");
  return data;
}

// Email
export async function getEmailTemplates(): Promise<EmailTemplatesResponse> {
  const { data } = await api.get<EmailTemplatesResponse>("/email/templates");
  return data;
}

export async function sendEmail(body: EmailSendRequest): Promise<EmailSendResponse> {
  const { data } = await api.post<EmailSendResponse>("/email/send", body);
  return data;
}

export async function previewEmail(body: EmailPreviewRequest): Promise<{ subject: string; body: string }> {
  const { data } = await api.post<{ subject: string; body: string }>("/email/preview", body);
  return data;
}

export async function sendBatchEmails(body: BatchEmailRequest): Promise<BatchEmailResponse> {
  const { data } = await api.post<BatchEmailResponse>("/email/batch", body);
  return data;
}
