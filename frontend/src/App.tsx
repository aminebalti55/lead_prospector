import { Routes, Route, Link as RouterLink, useLocation } from "react-router-dom";
import { Box, Stack, Typography, alpha, IconButton, Tooltip, Badge } from "@mui/material";
import {
  Dashboard as DashboardIcon,
  RocketLaunch as RocketIcon,
  FolderOpen as FolderIcon,
  Analytics as AnalyticsIcon,
  AutoAwesome as SparkleIcon,
} from "@mui/icons-material";
import { motion, AnimatePresence } from "framer-motion";
import { RunProvider, useRuns } from "./context/RunContext";
import NewRun from "./pages/NewRun";
import Files from "./pages/Files";
import FileLeads from "./pages/FileLeads";
import Analytics from "./pages/Analytics";
import ActiveRunsPanel from "./components/ActiveRunsPanel";
import { glassEffect, gradients } from "./theme";

const SIDEBAR_WIDTH = 72;

const navItems = [
  { path: "/", label: "Dashboard", icon: DashboardIcon },
  { path: "/new-run", label: "New Run", icon: RocketIcon },
  { path: "/files", label: "Files", icon: FolderIcon },
  { path: "/analytics", label: "Analytics", icon: AnalyticsIcon },
];

function NavButton({ item, isActive }: { item: typeof navItems[0]; isActive: boolean }) {
  const Icon = item.icon;
  
  return (
    <Tooltip title={item.label} placement="right" arrow>
      <Box
        component={RouterLink}
        to={item.path}
        sx={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: 48,
          height: 48,
          borderRadius: 3,
          color: isActive ? "#fff" : "grey.500",
          background: isActive ? gradients.primary : "transparent",
          transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
          textDecoration: "none",
          "&:hover": {
            color: isActive ? "#fff" : "grey.300",
            background: isActive ? gradients.primary : alpha("#fff", 0.05),
            transform: "scale(1.05)",
          },
          "&::before": isActive ? {
            content: '""',
            position: "absolute",
            left: -12,
            width: 4,
            height: 24,
            borderRadius: "0 4px 4px 0",
            background: gradients.primary,
          } : {},
        }}
      >
        <Icon sx={{ fontSize: 22 }} />
      </Box>
    </Tooltip>
  );
}

function Sidebar() {
  const location = useLocation();
  const { hasActiveRuns } = useRuns();

  const isActive = (path: string) => {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  };

  return (
    <Box
      component={motion.aside}
      initial={{ x: -80, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      sx={{
        position: "fixed",
        left: 0,
        top: 0,
        bottom: 0,
        width: SIDEBAR_WIDTH,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        py: 3,
        zIndex: 1200,
        ...glassEffect,
        borderRight: "1px solid",
        borderColor: alpha("#fff", 0.06),
        borderRadius: 0,
      }}
    >
      {/* Logo */}
      <Box
        component={motion.div}
        whileHover={{ scale: 1.1, rotate: 5 }}
        whileTap={{ scale: 0.95 }}
        sx={{
          width: 44,
          height: 44,
          borderRadius: 3,
          background: gradients.primary,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          mb: 4,
          cursor: "pointer",
          boxShadow: `0 8px 24px ${alpha("#8b5cf6", 0.4)}`,
        }}
      >
        <SparkleIcon sx={{ color: "#fff", fontSize: 24 }} />
      </Box>

      {/* Nav Items */}
      <Stack spacing={1.5} sx={{ flex: 1 }}>
        {navItems.map((item) => (
          <NavButton 
            key={item.path} 
            item={item} 
            isActive={isActive(item.path)} 
          />
        ))}
      </Stack>

      {/* Active runs indicator */}
      {hasActiveRuns && (
        <Box
          component={motion.div}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          sx={{
            width: 12,
            height: 12,
            borderRadius: "50%",
            background: gradients.accent,
            boxShadow: `0 0 20px ${alpha("#06b6d4", 0.8)}`,
            animation: "pulse 2s infinite",
            "@keyframes pulse": {
              "0%, 100%": { opacity: 1 },
              "50%": { opacity: 0.5 },
            },
          }}
        />
      )}
    </Box>
  );
}

function MainContent() {
  return (
    <Box
      component={motion.main}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      sx={{
        ml: `${SIDEBAR_WIDTH}px`,
        minHeight: "100vh",
        position: "relative",
      }}
    >
      {/* Background glow effect */}
      <Box
        sx={{
          position: "fixed",
          top: 0,
          left: SIDEBAR_WIDTH,
          right: 0,
          height: 400,
          background: `radial-gradient(ellipse 80% 50% at 50% -20%, ${alpha("#8b5cf6", 0.15)} 0%, transparent 70%)`,
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      {/* Content */}
      <Box sx={{ position: "relative", zIndex: 1, px: 5, py: 4 }}>
        <AnimatePresence mode="wait">
          <Routes>
            <Route path="/" element={<Analytics />} />
            <Route path="/new-run" element={<NewRun />} />
            <Route path="/files" element={<Files />} />
            <Route path="/files/:filename" element={<FileLeads />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route
              path="*"
              element={
                <Box sx={{ py: 12, textAlign: "center" }}>
                  <Typography variant="h3" sx={{ fontWeight: 700, mb: 2, color: "grey.300" }}>
                    Page Not Found
                  </Typography>
                  <Typography sx={{ color: "grey.500" }}>
                    The page you're looking for doesn't exist.
                  </Typography>
                </Box>
              }
            />
          </Routes>
        </AnimatePresence>
      </Box>
    </Box>
  );
}

function AppContent() {
  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <Sidebar />
      <MainContent />
      <ActiveRunsPanel />
    </Box>
  );
}

export default function App() {
  return (
    <RunProvider>
      <AppContent />
    </RunProvider>
  );
}
