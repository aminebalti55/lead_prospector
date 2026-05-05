import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { SourcesResponse } from "../types/source";

export function useSources() {
  return useQuery<SourcesResponse>({
    queryKey: ["sources", "list"],
    queryFn: () => apiFetch("/sources"),
    staleTime: 10_000,
    refetchInterval: 10_000,
  });
}

export function useToggleSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<{ source: string; enabled: boolean }>(`/sources/${name}/toggle`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sources"] });
    },
  });
}

export function useRunSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<{ source: string; scan_id: string }>(`/sources/${name}/run`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sources"] });
      qc.invalidateQueries({ queryKey: ["pulse", "status"] });
    },
  });
}
