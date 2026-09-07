import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { Activity, LayoutDashboard, GitBranch, Key, LogOut, ChevronRight, Shield, FileText, Settings, Zap, ClipboardCheck } from "lucide-react";
import { useAuthStore } from "../store/authStore";

const navItems = [
  { to: "/dashboard",        label: "Dashboard",        icon: LayoutDashboard },
  { to: "/workflows",       label: "Workflows",         icon: GitBranch },
  { to: "/security-findings", label: "Security",          icon: Shield },
  { to: "/policies",         label: "Policies",          icon: FileText },
  { to: "/audit-log",       label: "Audit",            icon: FileText },
  { to: "/review-queue",    label: "Review Queue",     icon: ClipboardCheck },
  { to: "/api-keys",         label: "API Keys",          icon: Key },
  { to: "/test-playground",  label: "Test Playground",   icon: Zap },
  { to: "/settings",        label: "Settings",          icon: Settings },
];

export default function Layout() {
  const navigate = useNavigate();
  const { logout } = useAuthStore();

  return (
    <div className="flex h-screen bg-gray-950 overflow-hidden">
      <aside className="w-60 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">

        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-gray-800">
          <div className="bg-blue-600 p-1.5 rounded-lg">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="text-lg font-bold text-white tracking-tight">ARI</span>
            <p className="text-xs text-gray-500">AI Runtime Intelligence</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive ? "bg-blue-600/20 text-blue-400" : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`
            }>
              {({ isActive }) => (
                <>
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span className="flex-1">{label}</span>
                  {isActive && <ChevronRight className="w-3 h-3 text-blue-400" />}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Platform badges */}
        <div className="px-4 py-3 mx-3 mb-2 bg-gray-800/50 rounded-lg border border-gray-700/50">
          <p className="text-xs text-gray-500 font-medium mb-2 uppercase tracking-wide">Platforms</p>
          {["n8n", "Make", "Zapier", "Custom"].map((p) => (
            <p key={p} className="text-xs text-gray-500 py-0.5">· {p}</p>
          ))}
        </div>

        {/* Logout */}
        <div className="px-3 pb-4 border-t border-gray-800 pt-3">
          <button onClick={() => { logout(); navigate("/login"); }}
            className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm text-gray-400 hover:text-red-400 hover:bg-red-900/20 transition-colors">
            <LogOut className="w-4 h-4" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
