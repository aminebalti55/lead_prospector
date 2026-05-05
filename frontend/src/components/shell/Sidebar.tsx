import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Inbox,
  Columns3,
  Radio,
  Send,
  FileText,
  Settings,
} from "lucide-react";
import clsx from "clsx";

const NAV = [
  { to: "/hub", label: "Hub", icon: LayoutDashboard },
  { to: "/inbox", label: "Inbox", icon: Inbox },
  { to: "/pipeline", label: "Pipeline", icon: Columns3 },
  { to: "/sources", label: "Sources", icon: Radio },
  { to: "/outreach", label: "Outreach", icon: Send },
  { to: "/templates", label: "Templates", icon: FileText },
];

export function Sidebar() {
  return (
    <aside className="w-[200px] shrink-0 bg-[--color-surface] border-r border-[--color-border] flex flex-col">
      <div className="px-4 py-4 flex items-center gap-2">
        <div className="w-6 h-6 rounded-md bg-[--color-accent] flex items-center justify-center">
          <span className="text-[10px] font-bold text-[#0A0A0B]">P</span>
        </div>
        <span className="font-semibold tracking-tight text-[--color-text-primary]">
          PULSE
        </span>
      </div>

      <nav className="flex-1 px-2 py-2 flex flex-col gap-0.5">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-2.5 px-2.5 h-8 text-[13px] rounded-[--radius-sm] transition-colors",
                isActive
                  ? "bg-[--color-accent-soft] text-[--color-accent]"
                  : "text-[--color-text-secondary] hover:bg-[--color-surface-raised] hover:text-[--color-text-primary]",
              )
            }
          >
            <Icon className="w-3.5 h-3.5" strokeWidth={1.75} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="px-2 py-2 border-t border-[--color-border]">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            clsx(
              "flex items-center gap-2.5 px-2.5 h-8 text-[13px] rounded-[--radius-sm] transition-colors",
              isActive
                ? "bg-[--color-accent-soft] text-[--color-accent]"
                : "text-[--color-text-secondary] hover:bg-[--color-surface-raised] hover:text-[--color-text-primary]",
            )
          }
        >
          <Settings className="w-3.5 h-3.5" strokeWidth={1.75} />
          <span>Settings</span>
        </NavLink>
      </div>
    </aside>
  );
}
