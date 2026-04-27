import { cn } from "../lib/cn";

const STYLES: Record<string, string> = {
  hot: "bg-hot-light text-hot border-hot/20",
  warm: "bg-warning-light text-warning border-warning/20",
  cold: "bg-bg text-text-secondary border-border",
  new: "bg-primary-light text-primary border-primary/20",
  queued: "bg-primary-light text-primary border-primary/20",
  contacted: "bg-blue-50 text-blue-700 border-blue-200",
  replied: "bg-success-light text-success border-success/20",
  meeting: "bg-success-light text-success border-success/20",
  converted: "bg-success-light text-success border-success/20",
  passed: "bg-bg text-text-tertiary border-border",
  running: "bg-primary-light text-primary border-primary/20",
  completed: "bg-success-light text-success border-success/20",
  failed: "bg-hot-light text-hot border-hot/20",
  pending: "bg-warning-light text-warning border-warning/20",
};

export function StatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase();
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold border capitalize",
        STYLES[s] || "bg-bg text-text-secondary border-border"
      )}
    >
      {status}
    </span>
  );
}
