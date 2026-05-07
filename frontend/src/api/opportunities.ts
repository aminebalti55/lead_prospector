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

/** Partial update: notes, owner, follow_up_date, contact info. */
export function useUpdateOpportunity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<Opportunity> }) =>
      apiFetch(`/opportunities/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      }),
    onSettled: (_data, _err, { id }) => {
      qc.invalidateQueries({ queryKey: ["opportunities"] });
      qc.invalidateQueries({ queryKey: ["opportunity", id] });
    },
  });
}

/** Bulk stage update for direct-lead Apply/Reject. */
export function useBulkUpdateStage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ids, stage }: { ids: string[]; stage: Stage }) =>
      apiFetch<{ updated: number; stage: string }>(`/opportunities/bulk-stage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ opportunity_ids: ids, stage }),
      }),
    // Same optimistic pattern as single update — snapshot every active list,
    // mutate matching ids in place, roll back on error.
    onMutate: async ({ ids, stage }) => {
      await qc.cancelQueries({ queryKey: ["opportunities"] });
      const idSet = new Set(ids);
      const snapshots = qc.getQueriesData<OpportunityListResponse>({ queryKey: ["opportunities"] });
      snapshots.forEach(([key, data]) => {
        if (!data) return;
        const next: OpportunityListResponse = {
          ...data,
          opportunities: data.opportunities.map((o) =>
            idSet.has(o.id) ? { ...o, stage } : o,
          ),
        };
        qc.setQueryData(key, next);
      });
      return { snapshots };
    },
    onError: (_err, _vars, context) => {
      context?.snapshots.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["opportunities"] });
      qc.invalidateQueries({ queryKey: ["hub"] });
    },
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
    // Optimistic: snapshot every active opportunities query, mutate the matching opp's stage in place.
    onMutate: async ({ id, stage }) => {
      await qc.cancelQueries({ queryKey: ["opportunities"] });
      const snapshots = qc.getQueriesData<OpportunityListResponse>({ queryKey: ["opportunities"] });
      snapshots.forEach(([key, data]) => {
        if (!data) return;
        const next: OpportunityListResponse = {
          ...data,
          opportunities: data.opportunities.map((o) =>
            o.id === id ? { ...o, stage } : o,
          ),
        };
        qc.setQueryData(key, next);
      });
      return { snapshots };
    },
    onError: (_err, _vars, context) => {
      // Roll back on failure
      context?.snapshots.forEach(([key, data]) => qc.setQueryData(key, data));
      console.error("Stage update failed; rolled back optimistic change");
    },
    onSettled: (_data, _err, { id }) => {
      qc.invalidateQueries({ queryKey: ["opportunities"] });
      qc.invalidateQueries({ queryKey: ["opportunity", id] });
      qc.invalidateQueries({ queryKey: ["hub"] });
    },
  });
}
