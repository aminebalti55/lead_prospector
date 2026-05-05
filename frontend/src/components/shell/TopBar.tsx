import { Search, ChevronDown } from "lucide-react";
import { KbdHint } from "../../design/primitives";

export function TopBar() {
  return (
    <header className="h-11 shrink-0 border-b border-[var(--color-border)] flex items-center px-4 gap-3 bg-[var(--color-bg)]">
      <button
        type="button"
        className="flex-1 max-w-[520px] h-7 flex items-center gap-2 px-2.5 rounded-[var(--radius-sm)] bg-[var(--color-surface-raised)] border border-[var(--color-border)] text-[var(--color-text-tertiary)] hover:border-[var(--color-border-strong)] transition-colors"
        // ⌘K opens command palette in a later plan; for now this is a no-op visual.
      >
        <Search className="w-3.5 h-3.5" strokeWidth={1.75} />
        <span className="text-[12px]">Search opportunities, sources, commands…</span>
        <span className="ml-auto flex items-center gap-1">
          <KbdHint>⌘</KbdHint>
          <KbdHint>K</KbdHint>
        </span>
      </button>
      <button
        type="button"
        className="ml-auto h-7 px-2 flex items-center gap-1.5 text-[12px] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-raised)] rounded-[var(--radius-sm)] transition-colors"
      >
        <span>Aether Agency</span>
        <ChevronDown className="w-3 h-3" strokeWidth={1.75} />
      </button>
    </header>
  );
}
