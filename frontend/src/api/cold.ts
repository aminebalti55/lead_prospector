import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";

export function useColdFiles() {
  return useQuery({ queryKey: ["cold", "files"], queryFn: () => apiFetch<any>("/cold/files") });
}

export function useColdLeads(filename: string) {
  return useQuery({ queryKey: ["cold", "leads", filename], queryFn: () => apiFetch<any>(`/cold/files/${filename}/leads`), enabled: !!filename });
}

export function useUpdateColdLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ leadId, data }: { leadId: string; data: any }) =>
      apiFetch(`/cold/leads/${leadId}`, { method: "PATCH", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cold"] }),
  });
}

export function useCreateColdRun() {
  return useMutation({
    mutationFn: (data: any) => apiFetch("/cold/runs", { method: "POST", body: JSON.stringify(data) }),
  });
}

export function useColdRunStatus(runId: string) {
  return useQuery({ queryKey: ["cold", "run", runId], queryFn: () => apiFetch<any>(`/cold/runs/${runId}`), enabled: !!runId, refetchInterval: 2000 });
}

export function useColdRuns() {
  return useQuery({ queryKey: ["cold", "runs"], queryFn: () => apiFetch<any>("/cold/runs") });
}
