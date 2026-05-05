import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppLayout } from "./layouts/AppLayout";
import { AppShell } from "./components/shell/AppShell";
import { InboxPage } from "./pages/inbox/InboxPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";

import { ColdDashboard } from "./pages/cold/Dashboard";
import { ColdLeads } from "./pages/cold/Leads";
import { ColdRuns } from "./pages/cold/Runs";
import { NewColdRun } from "./pages/cold/NewRun";
import { ColdEmail } from "./pages/cold/Email";
import { DirectDashboard } from "./pages/direct/Dashboard";
import { DirectLeads } from "./pages/direct/Leads";
import { DirectScans } from "./pages/direct/Scans";
import { NewDirectScan } from "./pages/direct/NewScan";
import { SavedSearches } from "./pages/direct/SavedSearches";
import { DirectLeadDetail } from "./pages/direct/LeadDetail";
import { SettingsPage } from "./pages/Settings";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30000, refetchOnWindowFocus: false } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/inbox" replace />} />
          <Route element={<AppShell />}>
            <Route path="/inbox" element={<InboxPage />} />
            <Route path="/hub" element={<PlaceholderPage title="Hub" shipping="Plan 2 — Hub & Pulse Bar" />} />
            <Route path="/pipeline" element={<PlaceholderPage title="Pipeline" shipping="Plan 3 — Pipeline Kanban" />} />
            <Route path="/sources" element={<PlaceholderPage title="Sources" shipping="Plan 4 — Sources page" />} />
            <Route path="/outreach" element={<PlaceholderPage title="Outreach" shipping="Plan 5 — Outreach revamp" />} />
            <Route path="/templates" element={<PlaceholderPage title="Templates" shipping="Plan 5 — Templates" />} />
            <Route path="/settings" element={<PlaceholderPage title="Settings" shipping="Plan 5 — Settings round-trip" />} />
          </Route>
          <Route element={<AppLayout />}>
            {/* Cold Outreach */}
            <Route path="/cold/dashboard" element={<ColdDashboard />} />
            <Route path="/cold/leads" element={<ColdLeads />} />
            <Route path="/cold/runs" element={<ColdRuns />} />
            <Route path="/cold/runs/new" element={<NewColdRun />} />
            <Route path="/cold/email" element={<ColdEmail />} />
            {/* Direct Leads */}
            <Route path="/direct/dashboard" element={<DirectDashboard />} />
            <Route path="/direct/leads" element={<DirectLeads />} />
            <Route path="/direct/leads/:leadId" element={<DirectLeadDetail />} />
            <Route path="/direct/scans" element={<DirectScans />} />
            <Route path="/direct/scans/new" element={<NewDirectScan />} />
            <Route path="/direct/saved-searches" element={<SavedSearches />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
