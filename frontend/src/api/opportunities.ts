import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type {
  Opportunity,
  OpportunityFilters,
  OpportunityListResponse,
  Stage,
} from "../types/opportunity";

function toQS(filters: OpportunityFilters): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  });
  const s = params.toString();
  return s ? `?${s}` : "";
}

export function useOpportunities(filters: OpportunityFilters = {}) {
  return useQuery<OpportunityListResponse>({
    queryKey: ["opportunities", filters],
    queryFn: () => apiFetch(`/opportunities${toQS(filters)}`),
    staleTime: 15_000,
  });
}

export function useOpportunity(id: string | null) {
  return useQuery<Opportunity>({
    queryKey: ["opportunity", id],
    queryFn: () => apiFetch(`/opportunities/${id}`),
    enabled: !!id,
  });
}

export function useUpdateStage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, stage }: { id: string; stage: Stage }) =>
      apiFetch(`/opportunities/${id}/stage`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stage }),
      }),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ["opportunities"] });
      qc.invalidateQueries({ queryKey: ["opportunity", id] });
    },
  });
}
