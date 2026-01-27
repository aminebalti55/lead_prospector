import { Box, Card, CardContent, Chip, LinearProgress, Stack, Typography, alpha } from "@mui/material";
import {
  CheckCircle as CheckIcon,
  RadioButtonUnchecked as PendingIcon,
  Error as ErrorIcon,
  Sync as RunningIcon,
} from "@mui/icons-material";
import { motion, AnimatePresence } from "framer-motion";
import type { RunProgress, ProgressStep } from "../api/types";
import { chartColors } from "../theme";

type Props = {
  progress: RunProgress | null | undefined;
  isLoading?: boolean;
};

function StepIcon({ status }: { status: ProgressStep["status"] }) {
  switch (status) {
    case "completed":
      return <CheckIcon sx={{ color: chartColors.success, fontSize: 20 }} />;
    case "running":
      return (
        <RunningIcon
          sx={{
            color: chartColors.primary,
            fontSize: 20,
            animation: "spin 1s linear infinite",
            "@keyframes spin": {
              "0%": { transform: "rotate(0deg)" },
              "100%": { transform: "rotate(360deg)" },
            },
          }}
        />
      );
    case "failed":
      return <ErrorIcon sx={{ color: chartColors.error, fontSize: 20 }} />;
    default:
      return <PendingIcon sx={{ color: "#94a3b8", fontSize: 20 }} />;
  }
}

function StepRow({ step, index }: { step: ProgressStep; index: number }) {
  const isActive = step.status === "running";

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <Stack
        direction="row"
        alignItems="center"
        spacing={1.5}
        sx={{
          py: 1,
          px: 1.5,
          borderRadius: 1.5,
          bgcolor: isActive ? alpha(chartColors.primary, 0.08) : "transparent",
          transition: "background-color 0.2s ease",
        }}
      >
        <StepIcon status={step.status} />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            variant="body2"
            sx={{
              fontWeight: isActive ? 600 : 500,
              color: step.status === "pending" ? "text.secondary" : "text.primary",
            }}
          >
            {step.step}
          </Typography>
          {step.message && step.status !== "pending" && (
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {step.message}
            </Typography>
          )}
        </Box>
        {step.count > 0 && (
          <Chip
            size="small"
            label={step.count}
            sx={{
              height: 22,
              fontSize: "0.75rem",
              fontWeight: 600,
              bgcolor: alpha(chartColors.primary, 0.1),
              color: chartColors.primary,
            }}
          />
        )}
      </Stack>
    </motion.div>
  );
}

export default function ProgressPanel({ progress, isLoading }: Props) {
  if (!progress && !isLoading) return null;

  const showLoading = isLoading && !progress;

  return (
    <Card
      component={motion.div}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      sx={{
        overflow: "hidden",
        border: `1px solid ${alpha(chartColors.primary, 0.2)}`,
      }}
    >
      {/* Header with progress bar */}
      <Box
        sx={{
          px: 3,
          py: 2,
          background: `linear-gradient(135deg, ${alpha(chartColors.primary, 0.05)} 0%, ${alpha(chartColors.secondary, 0.05)} 100%)`,
          borderBottom: `1px solid ${alpha(chartColors.primary, 0.1)}`,
        }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
          <Stack direction="row" alignItems="center" spacing={1}>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              {progress?.current_phase || "Starting..."}
            </Typography>
            {progress?.current_step && (
              <Chip
                size="small"
                label={progress.current_step}
                sx={{
                  height: 24,
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  background: `linear-gradient(135deg, ${chartColors.primary} 0%, ${chartColors.secondary} 100%)`,
                  color: "#fff",
                }}
              />
            )}
          </Stack>
          <Typography variant="body2" sx={{ fontWeight: 700, color: chartColors.primary }}>
            {progress?.progress_percent ?? 0}%
          </Typography>
        </Stack>
        <LinearProgress
          variant={showLoading ? "indeterminate" : "determinate"}
          value={progress?.progress_percent ?? 0}
          sx={{ height: 8, borderRadius: 4 }}
        />
      </Box>

      {/* Stats Row */}
      {progress && (
        <Box
          sx={{
            px: 3,
            py: 1.5,
            borderBottom: "1px solid",
            borderColor: "divider",
            bgcolor: alpha(chartColors.success, 0.02),
          }}
        >
          <Stack direction="row" spacing={4}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  bgcolor: chartColors.success,
                }}
              />
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                Leads Found:
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                {progress.leads_found}
              </Typography>
            </Stack>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  bgcolor: chartColors.primary,
                }}
              />
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                Emails Extracted:
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                {progress.emails_extracted}
              </Typography>
            </Stack>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  bgcolor: chartColors.warning,
                }}
              />
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                Sites Audited:
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                {progress.websites_audited}
              </Typography>
            </Stack>
          </Stack>
        </Box>
      )}

      {/* Steps List */}
      <CardContent sx={{ py: 2 }}>
        <Typography variant="body2" sx={{ fontWeight: 600, color: "text.secondary", mb: 1.5 }}>
          Progress Steps
        </Typography>
        <Stack spacing={0.5}>
          <AnimatePresence>
            {progress?.steps.map((step, index) => (
              <StepRow key={step.step} step={step} index={index} />
            ))}
            {!progress?.steps.length && (
              <Typography variant="body2" sx={{ color: "text.secondary", py: 2, textAlign: "center" }}>
                Waiting for scraper to start...
              </Typography>
            )}
          </AnimatePresence>
        </Stack>
      </CardContent>

      {/* Logs Section */}
      {progress?.logs && progress.logs.length > 0 && (
        <Box
          sx={{
            maxHeight: 150,
            overflow: "auto",
            bgcolor: "#0f172a",
            px: 2,
            py: 1.5,
            fontFamily: "monospace",
            fontSize: "0.75rem",
            color: "#94a3b8",
          }}
        >
          {progress.logs.slice(-20).map((log, i) => (
            <Box
              key={i}
              sx={{
                py: 0.25,
                borderLeft: "2px solid",
                borderColor: log.includes("error") ? chartColors.error : alpha(chartColors.primary, 0.5),
                pl: 1,
                color: log.includes("error") ? chartColors.error : "#e2e8f0",
              }}
            >
              {log}
            </Box>
          ))}
        </Box>
      )}
    </Card>
  );
}
