import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { NicheOption } from "../types/source";

interface NichesResponse {
  niches: NicheOption[];
}

/** Predefined niches the cold pipeline knows how to scrape. The cold-scan
 * picker uses this so users don't type free-text niche names. */
export function useNiches() {
  return useQuery<NichesResponse>({
    queryKey: ["cold", "niches"],
    queryFn: () => apiFetch("/cold/niches"),
    staleTime: 60 * 60 * 1000,
  });
}

interface CreateColdScanBody {
  locations: string[];
  niches: string[];
  max_results?: number;
  skip_scrapers?: string[];
  skip_audit?: boolean;
  fetch_emails?: boolean;
  fetch_details?: boolean;
}

/** Trigger an immediate cold-outreach scan (one-off, not saved). */
export function useCreateColdScan() {
  return useMutation({
    mutationFn: (body: CreateColdScanBody) =>
      apiFetch<{ scan_id: string; status: string }>("/cold/scans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
  });
}

/** Cold lead CRUD endpoints (Supabase-backed) — kept here so other pages can
 * still display cold leads without a separate hook file. */
export function useColdLeads() {
  return useQuery({
    queryKey: ["cold", "leads"],
    queryFn: () => apiFetch<any>("/cold/leads"),
  });
}

export function useColdScans() {
  return useQuery({
    queryKey: ["cold", "scans"],
    queryFn: () => apiFetch<any>("/cold/scans"),
  });
}

export function useUpdateColdLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ leadId, data }: { leadId: string; data: any }) =>
      apiFetch(`/cold/leads/${leadId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cold"] }),
  });
}
