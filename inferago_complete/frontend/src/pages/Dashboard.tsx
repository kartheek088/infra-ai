import { useNavigate } from "react-router-dom";
import { Activity, GitBranch, Zap, TrendingUp, AlertCircle, Loader2 } from "lucide-react";
import { useWorkflows } from "../hooks/useWorkflows";
import { usePlatforms } from "../hooks/useDashboard";
import PlatformBadge from "../components/PlatformBadge";

export default function Dashboard() {
  const navigate = useNavigate();
  const {
    data: workflows,
    isLoading: workflowsLoading,
    isError: workflowsError,
  } = useWorkflows();
  const {
    data: platforms,
    isLoading: platformsLoading,
    isError: platformsError,
  } = usePlatforms();

  const totalWorkflows = workflows?.length ?? 0;
  const totalCost      = platforms?.total_cost_usd ?? 0;

  if (workflowsError) {
    return (
      <div className="p-6 flex items-center gap-3 text-red-400">
        <AlertCircle className="w-5 h-5" />
        <span>Failed to load dashboard. Check your connection and try refreshing.</span>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">
          AI Runtime Intelligence: security, governance & observability
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<GitBranch className="w-5 h-5 text-blue-400" />}
          label="Workflows"
          value={workflowsLoading ? "—" : String(totalWorkflows)}
          sub="registered"
          color="blue"
        />
        <StatCard
          icon={<Zap className="w-5 h-5 text-yellow-400" />}
          label="Platforms"
          value={platformsLoading ? "—" : String(platforms?.platforms?.length ?? 0)}
          sub="connected"
          color="yellow"
        />
        <StatCard
          icon={<Activity className="w-5 h-5 text-green-400" />}
          label="Total Cost"
          value={platformsLoading ? "—" : `$${totalCost.toFixed(4)}`}
          sub="all time"
          color="green"
        />
        <StatCard
          icon={<TrendingUp className="w-5 h-5 text-purple-400" />}
          label="Top Platform"
          value={platformsLoading ? "—" : (platforms?.platforms?.[0]?.name ?? "—")}
          sub="by spend"
          color="purple"
        />
      </div>

      {/* Platform breakdown */}
      {!platformsLoading && !platformsError && (platforms?.platforms?.length ?? 0) > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">Spend by Platform</h2>
          <div className="space-y-3">
            {platforms!.platforms.map((p: any) => (
              <div key={p.name} className="flex items-center gap-3">
                <PlatformBadge platform={p.name} />
                <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-2 bg-blue-500 rounded-full transition-all"
                    style={{ width: `${Math.min(p.pct, 100)}%` }}
                  />
                </div>
                <span className="text-sm text-gray-400 w-20 text-right">
                  ${p.cost_usd.toFixed(4)}
                </span>
                <span className="text-xs text-gray-600 w-10 text-right">
                  {p.pct}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Workflows list */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Registered Workflows</h2>
          <button
            onClick={() => navigate("/workflows")}
            className="btn-secondary text-sm py-1.5"
          >
            View all
          </button>
        </div>

        {workflowsLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
          </div>
        ) : totalWorkflows === 0 ? (
          <div className="text-center py-10">
            <GitBranch className="w-10 h-10 text-gray-700 mx-auto mb-3" />
            <p className="text-gray-400 font-medium">No workflows yet</p>
            <p className="text-gray-600 text-sm mt-1">
              Register your first workflow to start monitoring
            </p>
            <button
              onClick={() => navigate("/workflows")}
              className="btn-primary mt-4 text-sm"
            >
              Add Workflow
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {workflows?.slice(0, 5).map((wf) => (
              <div
                key={wf.id}
                onClick={() => navigate(`/workflows/${wf.id}`)}
                className="flex items-center justify-between p-3 rounded-lg
                           bg-gray-800/50 hover:bg-gray-800 cursor-pointer
                           border border-gray-700/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-white">{wf.name}</p>
                    <p className="text-xs text-gray-500 font-mono">
                      ID: {wf.n8n_workflow_id}
                    </p>
                  </div>
                </div>
                <span className="text-xs text-gray-500">
                  {new Date(wf.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  sub,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
  color: "blue" | "yellow" | "green" | "purple";
}) {
  const ring: Record<string, string> = {
    blue:   "ring-blue-500/30",
    yellow: "ring-yellow-500/30",
    green:  "ring-green-500/30",
    purple: "ring-purple-500/30",
  };
  return (
    <div className={`card ring-1 ${ring[color]}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-400">{label}</span>
        {icon}
      </div>
      <p className="text-3xl font-bold text-white truncate">{value}</p>
      <p className="text-xs text-gray-500 mt-1">{sub}</p>
    </div>
  );
}
