import { useMemo, useState } from "react";
import { useParams, Link as RouterLink } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  IconButton,
  Skeleton,
  Snackbar,
  Stack,
  Tooltip,
  Typography,
  alpha,
} from "@mui/material";
import {
  ArrowBack as BackIcon,
  Download as DownloadIcon,
  Email as EmailIcon,
  Whatshot as HotIcon,
  People as PeopleIcon,
  Star as StarIcon,
  FilterList as FilterIcon,
} from "@mui/icons-material";
import { motion } from "framer-motion";
import { downloadUrl, getLeads, updateLead } from "../api/client";
import type { Lead, LeadUpdateRequest } from "../api/types";
import LeadsTable from "../components/LeadsTable";
import EmailComposer from "../components/EmailComposer";
import BatchEmailDialog from "../components/BatchEmailDialog";
import { calculateQualityScore, getQualityTier } from "../components/QualityBadge";
import { chartColors, gradients, glassEffect } from "../theme";

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

function StatCard({
  title,
  value,
  icon,
  color,
  gradient,
}: {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  gradient?: string;
}) {
  return (
    <Box
      component={motion.div}
      variants={itemVariants}
      sx={{
        p: 2.5,
        borderRadius: 3,
        ...glassEffect,
        border: `1px solid ${alpha(color, 0.2)}`,
        background: gradient 
          ? `linear-gradient(135deg, ${alpha(color, 0.15)} 0%, transparent 100%)`
          : alpha(color, 0.08),
      }}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between">
        <Box>
          <Typography variant="caption" sx={{ color: "grey.500", fontWeight: 600 }}>
            {title}
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 700, color: "grey.100", mt: 0.5 }}>
            {value}
          </Typography>
        </Box>
        <Box sx={{ color, opacity: 0.8 }}>{icon}</Box>
      </Stack>
    </Box>
  );
}

export default function FileLeads() {
  const params = useParams();
  const filename = useMemo(() => decodeURIComponent(params.filename ?? ""), [params]);
  const [toast, setToast] = useState<string | null>(null);
  const [emailLead, setEmailLead] = useState<Lead | null>(null);
  const [batchEmailOpen, setBatchEmailOpen] = useState(false);
  const [priorityFilter, setPriorityFilter] = useState<string | null>(null);

  const leadsQuery = useQuery({
    queryKey: ["leads", filename],
    queryFn: () => getLeads(filename),
    enabled: !!filename,
  });

  const updateMutation = useMutation({
    mutationFn: async (args: { leadId: string; patch: LeadUpdateRequest }) => {
      await updateLead(filename, args.leadId, args.patch);
    },
    onSuccess: () => setToast("Saved to Excel"),
  });

  // Compute quality scores for all leads
  const leadsWithQuality = useMemo(() => {
    if (!leadsQuery.data?.rows) return [];
    return leadsQuery.data.rows.map((lead) => {
      const score = calculateQualityScore(lead);
      return {
        ...lead,
        quality_score: score,
        quality_tier: getQualityTier(score),
      } as Lead;
    });
  }, [leadsQuery.data]);

  // Filter leads by priority
  const filteredLeads = useMemo(() => {
    if (!priorityFilter) return leadsWithQuality;
    return leadsWithQuality.filter(
      (l) => (l.Priority as string)?.toLowerCase() === priorityFilter.toLowerCase()
    );
  }, [leadsWithQuality, priorityFilter]);

  // Stats
  const stats = useMemo(() => {
    if (!leadsWithQuality.length) return null;
    const total = leadsWithQuality.length;
    const withEmail = leadsWithQuality.filter((l) => l.Email && (l.Email as string).includes("@")).length;
    const hot = leadsWithQuality.filter((l) => (l.Priority as string)?.toLowerCase() === "hot").length;
    const warm = leadsWithQuality.filter((l) => (l.Priority as string)?.toLowerCase() === "warm").length;
    const cold = leadsWithQuality.filter((l) => (l.Priority as string)?.toLowerCase() === "cold").length;
    const avgScore = Math.round(
      leadsWithQuality.reduce((sum, l) => sum + (l.quality_score || 0), 0) / total
    );
    return { total, withEmail, hot, warm, cold, avgScore };
  }, [leadsWithQuality]);

  if (!filename) {
    return <Alert severity="error">Missing filename</Alert>;
  }

  const baseName = filename.replace(/\.(xlsx|xls|csv)$/i, "");

  const filterButtons = [
    { label: "All", value: null, count: stats?.total ?? 0 },
    { label: "Hot", value: "hot", count: stats?.hot ?? 0, color: chartColors.hot },
    { label: "Warm", value: "warm", count: stats?.warm ?? 0, color: chartColors.warning },
    { label: "Cold", value: "cold", count: stats?.cold ?? 0, color: chartColors.cold },
  ];

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
        <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={2}>
          <Stack direction="row" alignItems="center" spacing={2}>
            <Tooltip title="Back to Files">
              <IconButton
                component={RouterLink}
                to="/files"
                sx={{
                  bgcolor: alpha("#fff", 0.05),
                  color: "grey.400",
                  "&:hover": { 
                    bgcolor: alpha(chartColors.purple, 0.15),
                    color: "primary.light",
                  },
                }}
              >
                <BackIcon />
              </IconButton>
            </Tooltip>
            <Box>
              <Typography variant="h3" sx={{ fontWeight: 700, color: "grey.100" }}>
                {baseName}
              </Typography>
              <Typography variant="body2" sx={{ color: "grey.500" }}>
                Lead data from prospecting run
              </Typography>
            </Box>
          </Stack>
          <Stack direction="row" spacing={2}>
            <Button
              variant="contained"
              startIcon={<EmailIcon />}
              onClick={() => setBatchEmailOpen(true)}
              disabled={!stats || stats.withEmail === 0}
            >
              Email All ({stats?.withEmail || 0})
            </Button>
            <Button
              component="a"
              href={downloadUrl(filename)}
              variant="outlined"
              startIcon={<DownloadIcon />}
            >
              Download Excel
            </Button>
          </Stack>
        </Stack>
      </Box>

      {/* Error */}
      {leadsQuery.isError && (
        <Alert severity="error">
          {(leadsQuery.error as Error)?.message || "Failed to load leads"}
        </Alert>
      )}

      {/* Stats Row */}
      {leadsQuery.isLoading ? (
        <Grid container spacing={2}>
          {[1, 2, 3, 4].map((i) => (
            <Grid item xs={6} sm={3} key={i}>
              <Skeleton 
                variant="rounded" 
                height={90} 
                sx={{ borderRadius: 3, bgcolor: alpha("#fff", 0.05) }} 
              />
            </Grid>
          ))}
        </Grid>
      ) : stats && (
        <Grid container spacing={2}>
          <Grid item xs={6} sm={3}>
            <StatCard
              title="Total Leads"
              value={stats.total}
              icon={<PeopleIcon sx={{ fontSize: 28 }} />}
              color={chartColors.purple}
              gradient
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <StatCard
              title="Hot Leads"
              value={stats.hot}
              icon={<HotIcon sx={{ fontSize: 28 }} />}
              color={chartColors.hot}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <StatCard
              title="With Email"
              value={stats.withEmail}
              icon={<EmailIcon sx={{ fontSize: 28 }} />}
              color={chartColors.success}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <StatCard
              title="Avg Quality"
              value={stats.avgScore}
              icon={<StarIcon sx={{ fontSize: 28 }} />}
              color={chartColors.warning}
            />
          </Grid>
        </Grid>
      )}

      {/* Priority Filter */}
      {leadsWithQuality.length > 0 && (
        <Stack 
          component={motion.div} 
          variants={itemVariants}
          direction="row" 
          alignItems="center" 
          spacing={2}
        >
          <FilterIcon sx={{ color: "grey.500", fontSize: 18 }} />
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {filterButtons.map((btn) => (
              <Chip
                key={btn.label}
                label={`${btn.label} (${btn.count})`}
                onClick={() => setPriorityFilter(btn.value)}
                sx={{
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  bgcolor: priorityFilter === btn.value 
                    ? alpha(btn.color || chartColors.purple, 0.2)
                    : alpha("#fff", 0.03),
                  color: priorityFilter === btn.value 
                    ? btn.color || chartColors.purple 
                    : "grey.400",
                  border: `1px solid ${
                    priorityFilter === btn.value 
                      ? alpha(btn.color || chartColors.purple, 0.4)
                      : alpha("#fff", 0.05)
                  }`,
                  "&:hover": {
                    bgcolor: alpha(btn.color || chartColors.purple, 0.15),
                    borderColor: alpha(btn.color || chartColors.purple, 0.3),
                  },
                }}
              />
            ))}
          </Stack>
        </Stack>
      )}

      {/* Leads Table */}
      <Card component={motion.div} variants={itemVariants}>
        <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
          {leadsQuery.isLoading ? (
            <Box sx={{ p: 4 }}>
              <Skeleton 
                variant="rounded" 
                height={400} 
                sx={{ borderRadius: 2, bgcolor: alpha("#fff", 0.05) }} 
              />
            </Box>
          ) : filteredLeads.length ? (
            <LeadsTable
              rows={filteredLeads}
              onUpdate={async (leadId, patch) => {
                await updateMutation.mutateAsync({ leadId, patch });
              }}
              saving={updateMutation.isPending}
              onSendEmail={(lead) => setEmailLead(lead)}
            />
          ) : (
            <Box sx={{ p: 6, textAlign: "center" }}>
              <Typography sx={{ color: "grey.500" }}>
                {priorityFilter 
                  ? `No ${priorityFilter} leads found` 
                  : "No leads found in this file"
                }
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Email Composer Modal (single lead) */}
      <EmailComposer
        open={!!emailLead}
        onClose={() => setEmailLead(null)}
        lead={emailLead}
        filename={filename}
      />

      {/* Batch Email Dialog (multiple leads) */}
      <BatchEmailDialog
        open={batchEmailOpen}
        onClose={() => setBatchEmailOpen(false)}
        leads={filteredLeads}
        filename={filename}
      />

      {/* Toast */}
      <Snackbar
        open={!!toast}
        autoHideDuration={2000}
        onClose={() => setToast(null)}
        message={toast ?? ""}
      />
    </Stack>
  );
}
