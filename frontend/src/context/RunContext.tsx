import { createContext, useContext, useState, useCallback, useEffect, useRef, ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getRun, createRun } from "../api/client";
import type { RunCreateRequest, RunStatusResponse } from "../api/types";

interface ActiveRun {
  runId: string;
  params: RunCreateRequest;
  startedAt: Date;
}

interface RunContextValue {
  activeRuns: ActiveRun[];
  runStatuses: Map<string, RunStatusResponse>;
  startRun: (params: RunCreateRequest) => Promise<string>;
  removeRun: (runId: string) => void;
  getRunStatus: (runId: string) => RunStatusResponse | undefined;
  hasActiveRuns: boolean;
}

const RunContext = createContext<RunContextValue | null>(null);

export function RunProvider({ children }: { children: ReactNode }) {
  const [activeRuns, setActiveRuns] = useState<ActiveRun[]>([]);
  const [runStatuses, setRunStatuses] = useState<Map<string, RunStatusResponse>>(new Map());
  const queryClient = useQueryClient();
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const completedRunsRef = useRef<Set<string>>(new Set());

  // Poll all active runs
  useEffect(() => {
    if (activeRuns.length === 0) {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      return;
    }

    const pollRuns = async () => {
      const updates = new Map(runStatuses);
      let hasChanges = false;
      
      for (const run of activeRuns) {
        // Skip polling for runs we've already marked as done
        if (completedRunsRef.current.has(run.runId)) {
          continue;
        }

        try {
          const status = await getRun(run.runId);
          const prevStatus = updates.get(run.runId);
          
          // Check if status changed
          if (!prevStatus || prevStatus.status !== status.status || 
              prevStatus.progress?.progress_percent !== status.progress?.progress_percent) {
            hasChanges = true;
          }
          
          updates.set(run.runId, status);
          
          // When a run completes, invalidate files query and mark as done
          if (status.status === "completed" || status.status === "failed") {
            if (!completedRunsRef.current.has(run.runId)) {
              completedRunsRef.current.add(run.runId);
              
              // Invalidate files query so Files page refreshes
              queryClient.invalidateQueries({ queryKey: ["files"] });
              queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
              
              // Auto-remove completed runs after 60 seconds
              setTimeout(() => {
                setActiveRuns(prev => prev.filter(r => r.runId !== run.runId));
                completedRunsRef.current.delete(run.runId);
              }, 60000);
            }
          }
        } catch (error) {
          console.error(`Failed to poll run ${run.runId}:`, error);
        }
      }
      
      if (hasChanges) {
        setRunStatuses(updates);
      }
    };

    // Initial poll immediately
    pollRuns();
    
    // Then poll every 2 seconds
    pollIntervalRef.current = setInterval(pollRuns, 2000);
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [activeRuns, queryClient]);

  const startRun = useCallback(async (params: RunCreateRequest): Promise<string> => {
    const response = await createRun(params);
    const newRun: ActiveRun = {
      runId: response.run_id,
      params,
      startedAt: new Date(),
    };
    setActiveRuns(prev => [...prev, newRun]);
    
    // Set initial status
    setRunStatuses(prev => {
      const next = new Map(prev);
      next.set(response.run_id, {
        run_id: response.run_id,
        status: "queued",
        created_at: response.created_at,
        params,
        output_files: [],
        progress: {
          current_phase: "Starting",
          current_step: "Initializing...",
          progress_percent: 0,
          leads_found: 0,
          emails_extracted: 0,
          websites_audited: 0,
          steps: [],
          logs: [],
        },
      });
      return next;
    });
    
    return response.run_id;
  }, []);

  const removeRun = useCallback((runId: string) => {
    setActiveRuns(prev => prev.filter(r => r.runId !== runId));
    setRunStatuses(prev => {
      const next = new Map(prev);
      next.delete(runId);
      return next;
    });
    completedRunsRef.current.delete(runId);
  }, []);

  const getRunStatus = useCallback((runId: string) => {
    return runStatuses.get(runId);
  }, [runStatuses]);

  const hasActiveRuns = activeRuns.some(run => {
    const status = runStatuses.get(run.runId);
    return !status || status.status === "running" || status.status === "queued";
  });

  return (
    <RunContext.Provider value={{
      activeRuns,
      runStatuses,
      startRun,
      removeRun,
      getRunStatus,
      hasActiveRuns,
    }}>
      {children}
    </RunContext.Provider>
  );
}

export function useRuns() {
  const context = useContext(RunContext);
  if (!context) {
    throw new Error("useRuns must be used within RunProvider");
  }
  return context;
}
