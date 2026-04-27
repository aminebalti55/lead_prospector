import { Inbox } from "lucide-react";

export function EmptyState({ message, action }: { message: string; action?: { label: string; href: string } }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-12 h-12 rounded-xl bg-bg border border-border flex items-center justify-center mb-4">
        <Inbox size={20} className="text-text-tertiary" />
      </div>
      <p className="text-text-secondary text-sm font-medium">{message}</p>
      {action && (
        <a
          href={action.href}
          className="mt-3 text-sm font-semibold text-primary hover:text-primary-hover transition-colors"
        >
          {action.label} &rarr;
        </a>
      )}
    </div>
  );
}
