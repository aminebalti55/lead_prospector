import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  IconButton,
  Skeleton,
  Stack,
  Tooltip,
  Typography,
  alpha,
} from "@mui/material";
import {
  FolderOpen as FolderIcon,
  Download as DownloadIcon,
  OpenInNew as OpenIcon,
  Description as FileIcon,
  AccessTime as TimeIcon,
  Storage as SizeIcon,
  RocketLaunch as RocketIcon,
  Refresh as RefreshIcon,
} from "@mui/icons-material";
import { Link as RouterLink } from "react-router-dom";
import { motion } from "framer-motion";
import { downloadUrl, listFiles } from "../api/client";
import { chartColors, gradients, glassEffect } from "../theme";
import { useRuns } from "../context/RunContext";

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours === 0) {
      const diffMins = Math.floor(diffMs / (1000 * 60));
      return `${diffMins}m ago`;
    }
    return `${diffHours}h ago`;
  }
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function FileCard({
  name,
  modifiedAt,
  sizeBytes,
}: {
  name: string;
  modifiedAt: string;
  sizeBytes: number;
}) {
  // Extract info from filename
  const baseName = name.replace(/\.(xlsx|xls|csv)$/i, "");
  const parts = baseName.split("_");
  const location = parts[0] || "";
  const niche = parts[1] || "";

  return (
    <Card
      component={motion.div}
      variants={itemVariants}
      whileHover={{ y: -4, scale: 1.01 }}
      transition={{ duration: 0.2 }}
      sx={{
        cursor: "pointer",
        height: "100%",
      }}
    >
      <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
        {/* Header */}
        <Box
          sx={{
            p: 2.5,
            background: `linear-gradient(135deg, ${alpha(chartColors.purple, 0.1)} 0%, ${alpha(chartColors.cyan, 0.1)} 100%)`,
            borderBottom: `1px solid ${alpha("#fff", 0.04)}`,
          }}
        >
          <Stack direction="row" alignItems="flex-start" justifyContent="space-between">
            <Stack direction="row" alignItems="center" spacing={1.5}>
              <Box
                sx={{
                  width: 44,
                  height: 44,
                  borderRadius: 2.5,
                  background: gradients.primary,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: `0 8px 20px ${alpha(chartColors.purple, 0.4)}`,
                }}
              >
                <FileIcon sx={{ color: "#fff", fontSize: 20 }} />
              </Box>
              <Box sx={{ minWidth: 0 }}>
                <Typography
                  variant="body1"
                  sx={{
                    fontWeight: 700,
                    color: "grey.100",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    maxWidth: 180,
                  }}
                >
                  {baseName}
                </Typography>
                <Typography variant="caption" sx={{ color: "grey.500" }}>
                  .xlsx
                </Typography>
              </Box>
            </Stack>
            <Tooltip title="Download">
              <IconButton
                component="a"
                href={downloadUrl(name)}
                size="small"
                onClick={(e) => e.stopPropagation()}
                sx={{
                  bgcolor: alpha("#fff", 0.05),
                  color: "grey.400",
                  "&:hover": {
                    bgcolor: alpha(chartColors.purple, 0.2),
                    color: "primary.light",
                  },
                }}
              >
                <DownloadIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </Tooltip>
          </Stack>
        </Box>

        {/* Details */}
        <Box sx={{ p: 2.5 }}>
          <Stack spacing={2}>
            {/* Meta info */}
            <Stack direction="row" spacing={3}>
              <Stack direction="row" alignItems="center" spacing={0.75}>
                <TimeIcon sx={{ fontSize: 14, color: "grey.600" }} />
                <Typography variant="caption" sx={{ color: "grey.500" }}>
                  {formatDate(modifiedAt)}
                </Typography>
              </Stack>
              <Stack direction="row" alignItems="center" spacing={0.75}>
                <SizeIcon sx={{ fontSize: 14, color: "grey.600" }} />
                <Typography variant="caption" sx={{ color: "grey.500" }}>
                  {formatFileSize(sizeBytes)}
                </Typography>
              </Stack>
            </Stack>

            {/* Tags */}
            {(location || niche) && (
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {location && (
                  <Box
                    sx={{
                      px: 1.5,
                      py: 0.5,
                      borderRadius: 1.5,
                      bgcolor: alpha(chartColors.success, 0.12),
                      color: chartColors.success,
                      fontSize: "0.7rem",
                      fontWeight: 600,
                    }}
                  >
                    {location}
                  </Box>
                )}
                {niche && (
                  <Box
                    sx={{
                      px: 1.5,
                      py: 0.5,
                      borderRadius: 1.5,
                      bgcolor: alpha(chartColors.warning, 0.12),
                      color: chartColors.warning,
                      fontSize: "0.7rem",
                      fontWeight: 600,
                      textTransform: "capitalize",
                    }}
                  >
                    {niche}
                  </Box>
                )}
              </Stack>
            )}

            {/* Open Button */}
            <Button
              component={RouterLink}
              to={`/files/${encodeURIComponent(name)}`}
              variant="outlined"
              fullWidth
              startIcon={<OpenIcon sx={{ fontSize: 16 }} />}
              onClick={(e) => e.stopPropagation()}
              sx={{
                py: 1,
                fontSize: "0.8rem",
              }}
            >
              View Leads
            </Button>
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
}

export default function Files() {
  const queryClient = useQueryClient();
  const { activeRuns, runStatuses } = useRuns();

  const filesQuery = useQuery({
    queryKey: ["files"],
    queryFn: listFiles,
    refetchOnWindowFocus: true,
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  // Refetch files when any run completes
  useEffect(() => {
    const completedRuns = activeRuns.filter((run) => {
      const status = runStatuses.get(run.runId);
      return status?.status === "completed";
    });

    if (completedRuns.length > 0) {
      // Invalidate files query to refetch
      queryClient.invalidateQueries({ queryKey: ["files"] });
    }
  }, [activeRuns, runStatuses, queryClient]);

  const handleRefresh = () => {
    filesQuery.refetch();
  };

  return (
    <Stack
      component={motion.div}
      variants={containerVariants}
      initial="hidden"
      animate="show"
      spacing={4}
    >
      {/* Header */}
      <Box component={motion.div} variants={itemVariants}>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Stack direction="row" alignItems="center" spacing={2}>
            <Box
              sx={{
                width: 56,
                height: 56,
                borderRadius: 3,
                background: gradients.accent,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: `0 12px 32px ${alpha(chartColors.purple, 0.4)}`,
              }}
            >
              <FolderIcon sx={{ color: "#fff", fontSize: 28 }} />
            </Box>
            <Box>
              <Typography variant="h3" sx={{ fontWeight: 700, color: "grey.100" }}>
                Lead Files
              </Typography>
              <Typography sx={{ color: "grey.500", mt: 0.5 }}>
                {filesQuery.data?.files.length || 0} files in output folder
              </Typography>
            </Box>
          </Stack>
          <Tooltip title="Refresh files">
            <IconButton
              onClick={handleRefresh}
              disabled={filesQuery.isFetching}
              sx={{
                bgcolor: alpha("#fff", 0.05),
                color: "grey.400",
                "&:hover": {
                  bgcolor: alpha(chartColors.purple, 0.15),
                  color: "primary.light",
                },
              }}
            >
              <RefreshIcon 
                sx={{ 
                  animation: filesQuery.isFetching ? "spin 1s linear infinite" : "none",
                  "@keyframes spin": {
                    "0%": { transform: "rotate(0deg)" },
                    "100%": { transform: "rotate(360deg)" },
                  },
                }} 
              />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {/* Error */}
      {filesQuery.isError && (
        <Alert severity="error">
          {(filesQuery.error as Error)?.message || "Failed to load files"}
        </Alert>
      )}

      {/* Loading State */}
      {filesQuery.isLoading && (
        <Grid container spacing={3}>
          {[1, 2, 3, 4].map((i) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={i}>
              <Skeleton 
                variant="rounded" 
                height={240} 
                sx={{ borderRadius: 3, bgcolor: alpha("#fff", 0.05) }} 
              />
            </Grid>
          ))}
        </Grid>
      )}

      {/* Files Grid */}
      {!filesQuery.isLoading && filesQuery.data?.files.length ? (
        <Grid container spacing={3}>
          {filesQuery.data.files.map((f) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={f.name}>
              <FileCard
                name={f.name}
                modifiedAt={f.modified_at}
                sizeBytes={f.size_bytes}
              />
            </Grid>
          ))}
        </Grid>
      ) : (
        !filesQuery.isLoading && (
          <Card component={motion.div} variants={itemVariants}>
            <CardContent sx={{ py: 8, textAlign: "center" }}>
              <Box
                sx={{
                  width: 80,
                  height: 80,
                  borderRadius: 4,
                  bgcolor: alpha("#fff", 0.03),
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  mx: "auto",
                  mb: 3,
                }}
              >
                <FolderIcon sx={{ fontSize: 40, color: "grey.700" }} />
              </Box>
              <Typography variant="h5" sx={{ fontWeight: 700, color: "grey.300", mb: 1 }}>
                No files yet
              </Typography>
              <Typography variant="body2" sx={{ color: "grey.500", mb: 4 }}>
                Start a new prospecting run to generate lead files
              </Typography>
              <Button 
                component={RouterLink} 
                to="/new-run" 
                variant="contained"
                startIcon={<RocketIcon />}
                sx={{ px: 4 }}
              >
                Start New Run
              </Button>
            </CardContent>
          </Card>
        )
      )}
    </Stack>
  );
}
