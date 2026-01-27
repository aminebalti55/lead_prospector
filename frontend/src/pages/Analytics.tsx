import { useQuery } from "@tanstack/react-query";
import {
  Box,
  Card,
  CardContent,
  Grid,
  Skeleton,
  Stack,
  Typography,
  alpha,
} from "@mui/material";
import {
  TrendingUp as TrendingIcon,
  People as PeopleIcon,
  Email as EmailIcon,
  Whatshot as HotIcon,
  Star as StarIcon,
  FolderOpen as FolderIcon,
  Analytics as AnalyticsIcon,
} from "@mui/icons-material";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  AreaChart,
  Area,
} from "recharts";
import { motion } from "framer-motion";
import { getDashboardStats } from "../api/client";
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

// Stat Card Component
function StatCard({
  title,
  value,
  subtitle,
  icon,
  color,
  gradient,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: string;
  gradient?: string;
}) {
  return (
    <Card
      component={motion.div}
      variants={itemVariants}
      sx={{ height: "100%" }}
    >
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography
              variant="caption"
              sx={{ color: "grey.500", fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" }}
            >
              {title}
            </Typography>
            <Typography variant="h3" sx={{ fontWeight: 700, color: "grey.100", mt: 0.5 }}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="caption" sx={{ color: "grey.500", mt: 0.5 }}>
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: 3,
              background: gradient || alpha(color, 0.15),
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: gradient ? "#fff" : color,
              boxShadow: gradient ? `0 8px 20px ${alpha(color, 0.4)}` : "none",
            }}
          >
            {icon}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

// Custom tooltip for charts
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <Box
      sx={{
        ...glassEffect,
        p: 1.5,
        borderRadius: 2,
        minWidth: 120,
      }}
    >
      <Typography variant="caption" sx={{ color: "grey.400", display: "block", mb: 0.5 }}>
        {label}
      </Typography>
      {payload.map((entry: any, index: number) => (
        <Stack key={index} direction="row" alignItems="center" spacing={1}>
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              bgcolor: entry.color,
            }}
          />
          <Typography variant="body2" sx={{ color: "grey.200", fontWeight: 600 }}>
            {entry.name}: {entry.value}
          </Typography>
        </Stack>
      ))}
    </Box>
  );
};

// Priority Pie Chart
function PriorityChart({
  hot,
  warm,
  cold,
}: {
  hot: number;
  warm: number;
  cold: number;
}) {
  const data = [
    { name: "Hot", value: hot, color: chartColors.hot },
    { name: "Warm", value: warm, color: chartColors.warning },
    { name: "Cold", value: cold, color: chartColors.cold },
  ];

  return (
    <Card component={motion.div} variants={itemVariants}>
      <CardContent>
        <Typography variant="h6" sx={{ fontWeight: 700, color: "grey.100", mb: 2 }}>
          Lead Priority
        </Typography>
        <Box sx={{ height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={100}
                paddingAngle={4}
                dataKey="value"
                stroke="none"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                verticalAlign="bottom"
                iconType="circle"
                formatter={(value) => (
                  <span style={{ color: "#a1a1aa", fontSize: "0.75rem" }}>{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}

// Niche Bar Chart
function NicheChart({ data }: { data: { niche: string; count: number; hot: number; warm: number; cold: number }[] }) {
  const chartData = data.map((d) => ({
    name: d.niche,
    Hot: d.hot,
    Warm: d.warm,
    Cold: d.cold,
  }));

  return (
    <Card component={motion.div} variants={itemVariants}>
      <CardContent>
        <Typography variant="h6" sx={{ fontWeight: 700, color: "grey.100", mb: 2 }}>
          Leads by Niche
        </Typography>
        <Box sx={{ height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke={alpha("#fff", 0.05)} horizontal={false} />
              <XAxis type="number" stroke="#71717a" fontSize={12} />
              <YAxis dataKey="name" type="category" width={80} stroke="#71717a" fontSize={12} />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                iconType="circle"
                formatter={(value) => (
                  <span style={{ color: "#a1a1aa", fontSize: "0.75rem" }}>{value}</span>
                )}
              />
              <Bar dataKey="Hot" stackId="a" fill={chartColors.hot} radius={[0, 0, 0, 0]} />
              <Bar dataKey="Warm" stackId="a" fill={chartColors.warning} radius={[0, 0, 0, 0]} />
              <Bar dataKey="Cold" stackId="a" fill={chartColors.cold} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}

// Score Distribution Chart
function ScoreChart({ data }: { data: { range: string; count: number }[] }) {
  return (
    <Card component={motion.div} variants={itemVariants}>
      <CardContent>
        <Typography variant="h6" sx={{ fontWeight: 700, color: "grey.100", mb: 2 }}>
          Score Distribution
        </Typography>
        <Box sx={{ height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorScoreGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={chartColors.cyan} stopOpacity={0.4} />
                  <stop offset="100%" stopColor={chartColors.cyan} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={alpha("#fff", 0.05)} />
              <XAxis dataKey="range" stroke="#71717a" fontSize={12} />
              <YAxis stroke="#71717a" fontSize={12} />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="count"
                stroke={chartColors.cyan}
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorScoreGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}

export default function Analytics() {
  const statsQuery = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: getDashboardStats,
    refetchInterval: 30000,
  });

  const stats = statsQuery.data;

  if (statsQuery.isLoading) {
    return (
      <Stack spacing={4}>
        <Skeleton variant="rounded" width={300} height={40} sx={{ borderRadius: 2, bgcolor: alpha("#fff", 0.05) }} />
        <Grid container spacing={3}>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Grid item xs={12} sm={6} md={4} lg={2} key={i}>
              <Skeleton variant="rounded" height={120} sx={{ borderRadius: 3, bgcolor: alpha("#fff", 0.05) }} />
            </Grid>
          ))}
        </Grid>
        <Grid container spacing={3}>
          {[1, 2, 3].map((i) => (
            <Grid item xs={12} md={4} key={i}>
              <Skeleton variant="rounded" height={360} sx={{ borderRadius: 3, bgcolor: alpha("#fff", 0.05) }} />
            </Grid>
          ))}
        </Grid>
      </Stack>
    );
  }

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
        <Stack direction="row" alignItems="center" spacing={2}>
          <Box
            sx={{
              width: 56,
              height: 56,
              borderRadius: 3,
              background: gradients.secondary,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: `0 12px 32px ${alpha("#06b6d4", 0.4)}`,
            }}
          >
            <AnalyticsIcon sx={{ color: "#fff", fontSize: 28 }} />
          </Box>
          <Box>
            <Typography variant="h3" sx={{ fontWeight: 700, color: "grey.100" }}>
              Analytics Dashboard
            </Typography>
            <Typography sx={{ color: "grey.500", mt: 0.5 }}>
              Lead generation performance overview
            </Typography>
          </Box>
        </Stack>
      </Box>

      {/* Stats Grid */}
      <Grid container spacing={2.5}>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <StatCard
            title="Total Leads"
            value={stats?.total_leads ?? 0}
            icon={<PeopleIcon sx={{ fontSize: 22 }} />}
            color={chartColors.purple}
            gradient={gradients.primary}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <StatCard
            title="Hot Leads"
            value={stats?.hot_leads ?? 0}
            icon={<HotIcon sx={{ fontSize: 22 }} />}
            color={chartColors.hot}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <StatCard
            title="With Email"
            value={stats?.total_emails ?? 0}
            icon={<EmailIcon sx={{ fontSize: 22 }} />}
            color={chartColors.success}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <StatCard
            title="Avg Score"
            value={stats?.avg_score ?? 0}
            icon={<StarIcon sx={{ fontSize: 22 }} />}
            color={chartColors.warning}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <StatCard
            title="Conversion"
            value={`${stats?.conversion_rate ?? 0}%`}
            subtitle="Email rate"
            icon={<TrendingIcon sx={{ fontSize: 22 }} />}
            color={chartColors.cyan}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <StatCard
            title="Files"
            value={stats?.total_files ?? 0}
            icon={<FolderIcon sx={{ fontSize: 22 }} />}
            color={chartColors.cold}
          />
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <PriorityChart
            hot={stats?.hot_leads ?? 0}
            warm={stats?.warm_leads ?? 0}
            cold={stats?.cold_leads ?? 0}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <NicheChart data={stats?.leads_by_niche ?? []} />
        </Grid>
        <Grid item xs={12} md={4}>
          <ScoreChart data={stats?.score_distribution ?? []} />
        </Grid>
      </Grid>
    </Stack>
  );
}
