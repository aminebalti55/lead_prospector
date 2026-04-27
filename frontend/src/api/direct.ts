import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";

export function useDirectLeads() {
  return useQuery({ queryKey: ["direct", "leads"], queryFn: () => apiFetch<any>("/direct/leads") });
}

export function useDirectLead(leadId: string) {
  return useQuery({ queryKey: ["direct", "lead", leadId], queryFn: () => apiFetch<any>(`/direct/leads/${leadId}`), enabled: !!leadId });
}

export function useUpdateDirectLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ leadId, data }: { leadId: string; data: any }) =>
      apiFetch(`/direct/leads/${leadId}`, { method: "PATCH", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["direct"] }),
  });
}

export function useDirectScans() {
  return useQuery({ queryKey: ["direct", "scans"], queryFn: () => apiFetch<any>("/direct/scans") });
}

export function useCreateDirectScan() {
  return useMutation({
    mutationFn: (data: any) => apiFetch("/direct/scans", { method: "POST", body: JSON.stringify(data) }),
  });
}

export function useSavedSearches() {
  return useQuery({ queryKey: ["direct", "saved-searches"], queryFn: () => apiFetch<any>("/direct/saved-searches") });
}

export function useCreateSavedSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => apiFetch("/direct/saved-searches", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["direct", "saved-searches"] }),
  });
}

export function useDeleteSavedSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch(`/direct/saved-searches/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["direct", "saved-searches"] }),
  });
}
