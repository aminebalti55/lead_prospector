import { Search } from "lucide-react";
import { KbdHint } from "../../design/primitives";

export function TopBar() {
  return (
    <header className="h-11 shrink-0 border-b border-[--color-border] flex items-center px-4 gap-3 bg-[--color-bg]">
      <button
        type="button"
        className="flex-1 max-w-[480px] h-7 flex items-center gap-2 px-2.5 rounded-[--radius-sm] bg-[--color-surface-raised] border border-[--color-border] text-[--color-text-tertiary] hover:border-[--color-border-strong] transition-colors"
        // ⌘K opens command palette in a later plan; for now this is a no-op visual.
      >
        <Search className="w-3.5 h-3.5" strokeWidth={1.75} />
        <span className="text-[12px]">Search opportunities, sources, commands…</span>
        <span className="ml-auto flex items-center gap-1">
          <KbdHint>⌘</KbdHint>
          <KbdHint>K</KbdHint>
        </span>
      </button>
      <div className="ml-auto text-[12px] text-[--color-text-tertiary]">
        Aether Agency
      </div>
    </header>
  );
}
