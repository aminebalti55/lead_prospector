import { useNavigate, useLocation } from "react-router-dom";
import { cn } from "../lib/cn";
import { Activity } from "lucide-react";

export function TopNav() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const section = pathname.startsWith("/direct") ? "direct" : "cold";

  return (
    <header className="h-14 bg-surface border-b border-border flex items-center px-6 justify-between shadow-sm">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-primary rounded-lg flex items-center justify-center">
            <Activity size={15} className="text-white" strokeWidth={2.5} />
          </div>
          <span className="font-bold text-text-primary text-[15px] tracking-tight">
            Lead Prospector
          </span>
        </div>
        <div className="flex bg-bg rounded-lg p-1 border border-border">
          <button
            onClick={() => navigate("/cold/dashboard")}
            className={cn(
              "px-3.5 py-1.5 text-[13px] font-semibold rounded-md transition-all duration-200",
              section === "cold"
                ? "bg-surface text-text-primary shadow-sm"
                : "text-text-secondary hover:text-text-primary"
            )}
          >
            Cold Outreach
          </button>
          <button
            onClick={() => navigate("/direct/dashboard")}
            className={cn(
              "px-3.5 py-1.5 text-[13px] font-semibold rounded-md transition-all duration-200",
              section === "direct"
                ? "bg-surface text-text-primary shadow-sm"
                : "text-text-secondary hover:text-text-primary"
            )}
          >
            Direct Leads
          </button>
        </div>
      </div>
    </header>
  );
}
