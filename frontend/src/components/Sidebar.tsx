import { NavLink } from "react-router-dom";
import { cn } from "../lib/cn";
import { LayoutDashboard, Users, Play, Mail, Settings, Bookmark } from "lucide-react";

const coldLinks = [
  { to: "/cold/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/cold/leads", label: "Leads", icon: Users },
  { to: "/cold/runs", label: "Runs", icon: Play },
  { to: "/cold/email", label: "Email", icon: Mail },
];

const directLinks = [
  { to: "/direct/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/direct/leads", label: "Leads", icon: Users },
  { to: "/direct/scans", label: "Scans", icon: Play },
  { to: "/direct/saved-searches", label: "Saved Searches", icon: Bookmark },
];

export function Sidebar({ section }: { section: "cold" | "direct" }) {
  const links = section === "cold" ? coldLinks : directLinks;
  return (
    <aside className="w-56 bg-sidebar border-r border-border min-h-[calc(100vh-3.5rem)] p-3 pt-4">
      <p className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">
        {section === "cold" ? "Cold Outreach" : "Direct Leads"}
      </p>
      <nav className="space-y-0.5">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150",
                isActive
                  ? "bg-primary-light text-primary font-semibold"
                  : "text-text-secondary hover:text-text-primary hover:bg-bg"
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-6 pt-4 border-t border-border">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150",
              isActive
                ? "bg-primary-light text-primary font-semibold"
                : "text-text-secondary hover:text-text-primary hover:bg-bg"
            )
          }
        >
          <Settings size={16} />
          Settings
        </NavLink>
      </div>
    </aside>
  );
}
