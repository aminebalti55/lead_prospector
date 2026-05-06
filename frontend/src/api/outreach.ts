import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";

export interface OutreachSendBody {
  opportunity_id: string;
  opportunity_type: "direct" | "cold";
  source_file: string;
  raw_lead_id: string;
  current_stage: string;
  template_id?: string;
  custom_subject?: string;
  custom_body?: string;
  to_email: string;
  to_name: string;
  variables?: Record<string, string>;
}

export interface OutreachSendResponse {
  success: boolean;
  message: string;
  sent_at: string | null;
  stage_advanced: boolean;
}

export function useSendOutreach() {
  const qc = useQueryClient();
  return useMutation<OutreachSendResponse, Error, OutreachSendBody>({
    mutationFn: (body) =>
      apiFetch("/outreach/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: (res) => {
      if (res.stage_advanced) {
        qc.invalidateQueries({ queryKey: ["opportunities"] });
      }
    },
  });
}

export interface BulkRecipient {
  opportunity_id: string;
  opportunity_type: "direct" | "cold";
  source_file: string;
  raw_lead_id: string;
  current_stage: string;
  to_email: string;
  to_name: string;
  variables?: Record<string, string>;
}

export interface OutreachBulkSendBody {
  template_id: string;
  recipients: BulkRecipient[];
  delay_seconds?: number;
}

export interface BulkSendResult {
  opportunity_id: string;
  to_email: string;
  success: boolean;
  message: string;
  stage_advanced: boolean;
}

export interface OutreachBulkSendResponse {
  sent: number;
  failed: number;
  results: BulkSendResult[];
}

export function useBulkSendOutreach() {
  const qc = useQueryClient();
  return useMutation<OutreachBulkSendResponse, Error, OutreachBulkSendBody>({
    mutationFn: (body) =>
      apiFetch("/outreach/bulk_send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: (res) => {
      if (res.sent > 0) {
        qc.invalidateQueries({ queryKey: ["opportunities"] });
      }
    },
  });
}
