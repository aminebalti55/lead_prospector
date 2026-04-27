import { type ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: string | number;
  trend?: string;
  color?: string;
  icon?: ReactNode;
}

export function StatCard({ label, value, trend, color, icon }: StatCardProps) {
  return (
    <div className="bg-surface rounded-xl border border-border p-5 shadow-[--shadow-card] hover:shadow-[--shadow-md] transition-shadow duration-200">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[13px] text-text-secondary font-medium">{label}</p>
          <p className={`text-2xl font-bold mt-1.5 tracking-tight ${color || "text-text-primary"}`}>
            {value}
          </p>
          {trend && (
            <p className="text-xs text-text-tertiary mt-1 font-medium">{trend}</p>
          )}
        </div>
        {icon && (
          <div className="w-9 h-9 rounded-lg bg-bg flex items-center justify-center text-text-tertiary">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
