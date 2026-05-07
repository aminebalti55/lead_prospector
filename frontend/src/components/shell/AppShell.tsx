import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { PulseBar } from "./PulseBar";
import { ScanProgressDock } from "./ScanProgressDock";

export function AppShell() {
  return (
    <div className="flex h-screen bg-[var(--color-bg)] text-[var(--color-text-primary)]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
        <PulseBar />
      </div>
      {/* Floating progress card — only visible while scans are running. */}
      <ScanProgressDock />
    </div>
  );
}
