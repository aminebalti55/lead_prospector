import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppLayout } from "./layouts/AppLayout";

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
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/cold/dashboard" replace />} />
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
            {/* Shared */}
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
