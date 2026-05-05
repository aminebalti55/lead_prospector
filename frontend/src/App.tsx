import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "./components/shell/AppShell";
import { InboxPage } from "./pages/inbox/InboxPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { HubPage } from "./pages/hub/HubPage";
import { PipelinePage } from "./pages/pipeline/PipelinePage";
import { SourcesPage } from "./pages/sources/SourcesPage";
import { SettingsPage } from "./pages/settings/SettingsPage";
import { TemplatesPage } from "./pages/templates/TemplatesPage";
import { OutreachPage } from "./pages/outreach/OutreachPage";

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
            <Route path="/hub" element={<HubPage />} />
            <Route path="/pipeline" element={<PipelinePage />} />
            <Route path="/sources" element={<SourcesPage />} />
            <Route path="/outreach" element={<OutreachPage />} />
            <Route path="/templates" element={<TemplatesPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
