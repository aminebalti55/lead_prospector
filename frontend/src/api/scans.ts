import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";

export interface ScanRecord {
  id: string;
  type: "direct" | "cold";
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  sources: string[];
  keywords: string[];
  locations: string[];
  niches: string[];
  max_results: number;
  progress: number;
  leads_found: number;
  emails_extracted: number;
  logs: string[];
  error: string | null;
  output_files: string[];
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  phase: string | null;
  current_source: string | null;
  current_keyword: string | null;
}

export interface ScanListResponse {
  scans: ScanRecord[];
}

/** Poll every 2s while any scan is running; back off to 30s when idle. */
export function useActiveScans() {
  return useQuery<ScanListResponse>({
    queryKey: ["scans", "list"],
    queryFn: () => apiFetch<ScanListResponse>("/direct/scans"),
    refetchInterval: (query) => {
      const data = query.state.data;
      const anyRunning = data?.scans.some(
        (s) => s.status === "running" || s.status === "queued",
      );
      return anyRunning ? 2_000 : 30_000;
    },
    staleTime: 1_000,
  });
}
