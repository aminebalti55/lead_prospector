import { useState } from "react";
import { Outlet } from "react-router-dom";
import { useHotkeys } from "react-hotkeys-hook";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { PulseBar } from "./PulseBar";
import { ScanProgressDock } from "./ScanProgressDock";
import { CommandPalette } from "../CommandPalette";

export function AppShell() {
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Global Cmd/Ctrl+K toggle. Wired here (not inside the palette) so the
  // shortcut works from any page even when the palette isn't mounted yet.
  useHotkeys(
    "mod+k",
    () => setPaletteOpen((v) => !v),
    { preventDefault: true, enableOnFormTags: true },
  );

  return (
    <div className="flex h-screen bg-[var(--color-bg)] text-[var(--color-text-primary)]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar onSearchClick={() => setPaletteOpen(true)} />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
        <PulseBar />
      </div>
      <ScanProgressDock />
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  );
}
