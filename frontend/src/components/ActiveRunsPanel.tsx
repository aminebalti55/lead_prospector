import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  Box,
  Typography,
  IconButton,
  Stack,
  LinearProgress,
  Collapse,
  alpha,
  Button,
  Divider,
} from "@mui/material";
import {
  ExpandLess,
  ExpandMore,
  Close as CloseIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  PlayArrow as PlayIcon,
  Schedule as ScheduleIcon,
  OpenInNew as OpenIcon,
  Business as BusinessIcon,
  Email as EmailIcon,
  Speed as SpeedIcon,
  Map as MapIcon,
  Search as SearchIcon,
} from "@mui/icons-material";
import { motion, AnimatePresence } from "framer-motion";
import { useRuns } from "../context/RunContext";
import { glassEffect, gradients, chartColors } from "../theme";
import type { RunStatusResponse } from "../api/types";

// Scraper icons and labels
const SCRAPER_CONFIG: Record<string, { label: string; color: string }> = {
  google_maps: { label: "Google Maps", color: "#4285F4" },
  yelp: { label: "Yelp", color: "#FF1A1A" },
  yellowpages: { label: "YellowPages", color: "#FFCC00" },
  bbb: { label: "BBB", color: "#005A8B" },
  manta: { label: "Manta", color: "#00A651" },
};

function formatDuration(startedAt: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - startedAt.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const mins = Math.floor(diffSecs / 60);
  const secs = diffSecs % 60;
  
  if (mins > 0) {
    return `${mins}m ${secs}s`;
  }
  return `${secs}s`;
}

function RunCard({ 
  run, 
  status, 
  onRemove, 
  onViewLeads 
}: { 
  run: { runId: string; params: any; startedAt: Date };
  status?: RunStatusResponse;
  onRemove: () => void;
  onViewLeads: (file: string) => void;
}) {
  const [elapsed, setElapsed] = useState("0s");
  const progress = status?.progress;
  const isActive = status?.status === "running" || status?.status === "queued";
  const isCompleted = status?.status === "completed";
  const isFailed = status?.status === "failed";
  const outputFile = status?.output_files?.[0];

  // Update elapsed time
  useEffect(() => {
    if (!isActive) return;
    
    const interval = setInterval(() => {
      setElapsed(formatDuration(run.startedAt));
    }, 1000);
    
    return () => clearInterval(interval);
  }, [isActive, run.startedAt]);

  // Parse current step to identify active scraper
  const currentStep = progress?.current_step || "";
  const currentStepLower = currentStep.toLowerCase();
  const activeScraper = Object.keys(SCRAPER_CONFIG).find(
    s => currentStepLower.includes(s.replace("_", " ")) || currentStepLower.includes(s)
  );

  return (
    <Box
      component={motion.div}
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      sx={{
        borderRadius: 3,
        overflow: "hidden",
        bgcolor: alpha("#fff", 0.02),
        border: `1px solid ${alpha("#fff", 0.05)}`,
      }}
    >
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: `1px solid ${alpha("#fff", 0.04)}` }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Stack direction="row" alignItems="center" spacing={1.5}>
            <Box
              sx={{
                width: 36,
                height: 36,
                borderRadius: 2,
                background: isCompleted 
                  ? alpha(chartColors.success, 0.15)
                  : isFailed 
                    ? alpha(chartColors.error, 0.15)
                    : gradients.primary,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {isCompleted ? (
                <CheckIcon sx={{ fontSize: 18, color: chartColors.success }} />
              ) : isFailed ? (
                <ErrorIcon sx={{ fontSize: 18, color: chartColors.error }} />
              ) : isActive ? (
                <SearchIcon sx={{ fontSize: 18, color: "#fff" }} />
              ) : (
                <ScheduleIcon sx={{ fontSize: 18, color: "#fff" }} />
              )}
            </Box>
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 700, color: "grey.100" }}>
                {run.params.locations.join(", ")}
              </Typography>
              <Typography variant="caption" sx={{ color: "grey.500" }}>
                {run.params.niches.map((n: string) => n.replace("_", " ")).join(", ")}
              </Typography>
            </Box>
          </Stack>
          <Stack direction="row" alignItems="center" spacing={1}>
            {isActive && (
              <Typography variant="caption" sx={{ color: "grey.500", fontFamily: "monospace" }}>
                {elapsed}
              </Typography>
            )}
            <IconButton
              size="small"
              onClick={onRemove}
              sx={{ 
                color: "grey.600",
                "&:hover": { color: "grey.400", bgcolor: alpha("#fff", 0.05) },
              }}
            >
              <CloseIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Stack>
        </Stack>
      </Box>

      {/* Progress Content */}
      {isActive && (
        <Box sx={{ p: 2 }}>
          {/* Phase indicator */}
          <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1.5 }}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  bgcolor: chartColors.cyan,
                  animation: "pulse 1.5s infinite",
                  "@keyframes pulse": {
                    "0%, 100%": { opacity: 1, transform: "scale(1)" },
                    "50%": { opacity: 0.5, transform: "scale(0.8)" },
                  },
                }}
              />
              <Typography variant="body2" sx={{ color: "grey.300", fontWeight: 600 }}>
                {progress?.current_phase || "Starting"}
              </Typography>
            </Stack>
            <Typography 
              variant="caption" 
              sx={{ 
                color: chartColors.cyan, 
                fontWeight: 700,
                bgcolor: alpha(chartColors.cyan, 0.1),
                px: 1,
                py: 0.25,
                borderRadius: 1,
              }}
            >
              {progress?.progress_percent || 0}%
            </Typography>
          </Stack>

          {/* Progress bar */}
          <LinearProgress
            variant="determinate"
            value={progress?.progress_percent || 0}
            sx={{ 
              height: 6, 
              borderRadius: 3,
              mb: 2,
              bgcolor: alpha("#fff", 0.05),
            }}
          />

          {/* Current activity */}
          <Box
            sx={{
              p: 1.5,
              borderRadius: 2,
              bgcolor: alpha("#fff", 0.02),
              border: `1px solid ${alpha("#fff", 0.04)}`,
              mb: 2,
            }}
          >
            <Typography 
              variant="caption" 
              sx={{ 
                color: "grey.400", 
                display: "block",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {progress?.current_step || "Initializing..."}
            </Typography>
          </Box>

          {/* Scrapers status */}
          <Typography variant="caption" sx={{ color: "grey.500", fontWeight: 600, mb: 1, display: "block" }}>
            DATA SOURCES
          </Typography>
          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            {Object.entries(SCRAPER_CONFIG).map(([key, config]) => {
              const isSkipped = run.params.skip_scrapers?.includes(key);
              const isCurrentScraper = activeScraper === key;
              const stepInfo = progress?.steps?.find(s => s.step.toLowerCase().includes(key.replace("_", " ")) || s.step.toLowerCase().includes(key));
              const isCompletedScraper = stepInfo?.status === "completed";
              
              if (isSkipped) return null;
              
              return (
                <Box
                  key={key}
                  sx={{
                    px: 1.25,
                    py: 0.5,
                    borderRadius: 1.5,
                    fontSize: "0.7rem",
                    fontWeight: 600,
                    bgcolor: isCurrentScraper 
                      ? alpha(config.color, 0.2)
                      : isCompletedScraper
                        ? alpha(chartColors.success, 0.1)
                        : alpha("#fff", 0.03),
                    color: isCurrentScraper 
                      ? config.color
                      : isCompletedScraper
                        ? chartColors.success
                        : "grey.500",
                    border: `1px solid ${
                      isCurrentScraper 
                        ? alpha(config.color, 0.4)
                        : isCompletedScraper
                          ? alpha(chartColors.success, 0.3)
                          : alpha("#fff", 0.05)
                    }`,
                    display: "flex",
                    alignItems: "center",
                    gap: 0.5,
                  }}
                >
                  {isCompletedScraper && <CheckIcon sx={{ fontSize: 12 }} />}
                  {isCurrentScraper && (
                    <Box
                      sx={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        bgcolor: config.color,
                        animation: "pulse 1s infinite",
                      }}
                    />
                  )}
                  {config.label}
                  {stepInfo?.count ? ` (${stepInfo.count})` : ""}
                </Box>
              );
            })}
          </Stack>

          {/* Stats */}
          <Stack direction="row" spacing={2}>
            <Stack direction="row" alignItems="center" spacing={0.75}>
              <BusinessIcon sx={{ fontSize: 14, color: chartColors.purple }} />
              <Typography variant="caption" sx={{ color: "grey.400" }}>
                <Box component="span" sx={{ color: "grey.200", fontWeight: 700 }}>
                  {progress?.leads_found || 0}
                </Box>{" "}
                leads
              </Typography>
            </Stack>
            {(progress?.emails_extracted || 0) > 0 && (
              <Stack direction="row" alignItems="center" spacing={0.75}>
                <EmailIcon sx={{ fontSize: 14, color: chartColors.success }} />
                <Typography variant="caption" sx={{ color: "grey.400" }}>
                  <Box component="span" sx={{ color: chartColors.success, fontWeight: 700 }}>
                    {progress?.emails_extracted || 0}
                  </Box>{" "}
                  emails
                </Typography>
              </Stack>
            )}
          </Stack>
        </Box>
      )}

      {/* Completed state */}
      {isCompleted && (
        <Box sx={{ p: 2 }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <Stack direction="row" alignItems="center" spacing={2}>
              <Stack direction="row" alignItems="center" spacing={0.75}>
                <BusinessIcon sx={{ fontSize: 14, color: chartColors.success }} />
                <Typography variant="body2" sx={{ color: "grey.300", fontWeight: 600 }}>
                  {progress?.leads_found || 0} leads
                </Typography>
              </Stack>
              {(progress?.emails_extracted || 0) > 0 && (
                <Stack direction="row" alignItems="center" spacing={0.75}>
                  <EmailIcon sx={{ fontSize: 14, color: chartColors.cyan }} />
                  <Typography variant="body2" sx={{ color: "grey.300" }}>
                    {progress?.emails_extracted} emails
                  </Typography>
                </Stack>
              )}
            </Stack>
            {outputFile && (
              <Button
                onClick={() => onViewLeads(outputFile)}
                size="small"
                startIcon={<OpenIcon sx={{ fontSize: 14 }} />}
                sx={{
                  fontSize: "0.75rem",
                  py: 0.75,
                  px: 2,
                  bgcolor: alpha(chartColors.success, 0.15),
                  color: chartColors.success,
                  "&:hover": {
                    bgcolor: alpha(chartColors.success, 0.25),
                  },
                }}
              >
                View Results
              </Button>
            )}
          </Stack>
        </Box>
      )}

      {/* Failed state */}
      {isFailed && (
        <Box sx={{ p: 2 }}>
          <Typography variant="body2" sx={{ color: chartColors.error }}>
            {status?.error || "An error occurred during scraping"}
          </Typography>
        </Box>
      )}
    </Box>
  );
}

export default function ActiveRunsPanel() {
  const { activeRuns, runStatuses, removeRun, hasActiveRuns } = useRuns();
  const [minimized, setMinimized] = useState(false);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  if (activeRuns.length === 0) return null;

  const handleViewLeads = (outputFile: string) => {
    queryClient.invalidateQueries({ queryKey: ["files"] });
    navigate(`/files/${encodeURIComponent(outputFile)}`);
  };

  const activeCount = activeRuns.filter(r => {
    const status = runStatuses.get(r.runId);
    return status?.status === "running" || status?.status === "queued";
  }).length;

  return (
    <AnimatePresence>
      <Box
        component={motion.div}
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 100, opacity: 0 }}
        transition={{ type: "spring", damping: 25, stiffness: 300 }}
        sx={{
          position: "fixed",
          bottom: 24,
          right: 24,
          width: minimized ? 280 : 420,
          maxHeight: minimized ? "auto" : "calc(100vh - 100px)",
          zIndex: 1300,
          ...glassEffect,
          borderRadius: 4,
          overflow: "hidden",
          boxShadow: `0 20px 60px ${alpha("#000", 0.5)}`,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            px: 2.5,
            py: 2,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: minimized ? "none" : `1px solid ${alpha("#fff", 0.06)}`,
            cursor: "pointer",
            flexShrink: 0,
          }}
          onClick={() => setMinimized(!minimized)}
        >
          <Stack direction="row" alignItems="center" spacing={1.5}>
            {hasActiveRuns ? (
              <Box
                sx={{
                  width: 32,
                  height: 32,
                  borderRadius: 2,
                  background: gradients.accent,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: `0 0 20px ${alpha(chartColors.cyan, 0.5)}`,
                }}
              >
                <SpeedIcon sx={{ fontSize: 16, color: "#fff" }} />
              </Box>
            ) : (
              <Box
                sx={{
                  width: 32,
                  height: 32,
                  borderRadius: 2,
                  bgcolor: alpha(chartColors.success, 0.15),
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <CheckIcon sx={{ fontSize: 16, color: chartColors.success }} />
              </Box>
            )}
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 700, color: "grey.100" }}>
                {hasActiveRuns ? "Scraping in Progress" : "Scraping Complete"}
              </Typography>
              <Typography variant="caption" sx={{ color: "grey.500" }}>
                {activeCount > 0 ? `${activeCount} active` : ""}{" "}
                {activeCount > 0 && activeRuns.length > activeCount ? "• " : ""}
                {activeRuns.length} total
              </Typography>
            </Box>
          </Stack>
          <IconButton 
            size="small" 
            sx={{ color: "grey.500" }}
            onClick={(e) => {
              e.stopPropagation();
              setMinimized(!minimized);
            }}
          >
            {minimized ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
        </Box>

        {/* Content */}
        <Collapse in={!minimized}>
          <Box 
            sx={{ 
              p: 1.5, 
              overflowY: "auto",
              maxHeight: "calc(100vh - 200px)",
              "&::-webkit-scrollbar": {
                width: 6,
              },
              "&::-webkit-scrollbar-thumb": {
                bgcolor: alpha("#fff", 0.1),
                borderRadius: 3,
              },
            }}
          >
            <Stack spacing={1.5}>
              {activeRuns.map((run) => (
                <RunCard
                  key={run.runId}
                  run={run}
                  status={runStatuses.get(run.runId)}
                  onRemove={() => removeRun(run.runId)}
                  onViewLeads={handleViewLeads}
                />
              ))}
            </Stack>
          </Box>
        </Collapse>
      </Box>
    </AnimatePresence>
  );
}
