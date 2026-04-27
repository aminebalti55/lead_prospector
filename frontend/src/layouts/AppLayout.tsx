import { Outlet, useLocation } from "react-router-dom";
import { TopNav } from "../components/TopNav";
import { Sidebar } from "../components/Sidebar";

export function AppLayout() {
  const { pathname } = useLocation();
  const section = pathname.startsWith("/direct") ? "direct" : "cold";

  return (
    <div className="min-h-screen bg-bg">
      <TopNav />
      <div className="flex">
        <Sidebar section={section} />
        <main className="flex-1 p-8 max-w-[1400px]">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
