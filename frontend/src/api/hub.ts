import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type {
  HubStats,
  PulseStatusResponse,
  ActivityResponse,
} from "../types/hub";

export function useHubStats() {
  return useQuery<HubStats>({
    queryKey: ["hub", "stats"],
    queryFn: () => apiFetch("/hub/stats"),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}

export function useHubActivity(limit = 30) {
  return useQuery<ActivityResponse>({
    queryKey: ["hub", "activity", limit],
    queryFn: () => apiFetch(`/hub/activity?limit=${limit}`),
    staleTime: 15_000,
    refetchInterval: 15_000,
  });
}

export function usePulseStatus() {
  return useQuery<PulseStatusResponse>({
    queryKey: ["pulse", "status"],
    queryFn: () => apiFetch("/pulse/status"),
    staleTime: 5_000,
    refetchInterval: 5_000,
  });
}
