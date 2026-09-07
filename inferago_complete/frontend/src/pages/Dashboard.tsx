import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getGlobalMetrics, getRecentExecutions, GlobalMetrics, ExecutionSummaryData } from "../api/executions";
import { getWorkflows, Workflow } from "../api/workflows";
import ExecutionDashboard from "../components/ExecutionDashboard";
import ExecutionCard from "../components/ExecutionCard";
import { Zap, Bug, Clock, Server, Activity, ArrowRight, RefreshCw, Layers } from "lucide-react";

export default function Dashboard() {
  const [metrics, setMetrics] = useState<GlobalMetrics>({
    executions: 0,
    failures: 0,
    avg_latency: 0,
    automations: 0,
  });
  const [recentExecutions, setRecentExecutions] = useState<ExecutionSummaryData[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadAllData = async () => {
    try {
      const [m, recents, wfs] = await Promise.all([
        getGlobalMetrics().catch(() => ({ executions: 0, failures: 0, avg_latency: 0, automations: 0 })),
        getRecentExecutions(10).catch(() => []),
        getWorkflows().catch(() => []),
      ]);
      setMetrics(m);
      setRecentExecutions(recents);
      setWorkflows(wfs);
    } catch (e) {
      console.error("Failed to load dashboard data", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    loadAllData();
  };

  return (
    <div className="space-y-12 max-w-7xl mx-auto font-sans animate-in fade-in duration-300 pb-20">
      {/* HEADER BAR */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <span className="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></span>
            AI Runtime Observability & Trace Intelligence
          </h1>
          <p className="text-sm text-neutral-400 mt-1">
            Real-time execution traces, pipeline anomaly detection, and automated AI runtime governance.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-neutral-300 text-xs font-mono font-bold border border-white/10 transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin text-emerald-400" : ""}`} />
            Refresh
          </button>
          <Link
            to="/test-playground"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/20 text-emerald-300 text-xs font-mono font-bold border border-emerald-500/30 hover:bg-emerald-500/30 transition-all"
          >
            ⚡ Test Playground
          </Link>
        </div>
      </div>

      {/* 4 TOP STAT CARDS */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-black/40 backdrop-blur-md border border-white/10 p-6 rounded-2xl shadow-xl hover:border-emerald-500/30 transition-all group">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 text-emerald-400 font-mono font-bold text-xs uppercase tracking-wider">
              <Zap className="w-4 h-4" />
              <span>Total Executions</span>
            </div>
          </div>
          <h2 className="text-3xl sm:text-4xl mt-4 font-mono font-bold text-white tracking-tight">
            {metrics.executions.toLocaleString()}
          </h2>
          <p className="text-[11px] font-mono text-neutral-500 mt-2">Recorded workflow runs</p>
        </div>

        <div className="bg-black/40 backdrop-blur-md border border-white/10 p-6 rounded-2xl shadow-xl hover:border-red-500/30 transition-all group">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 text-red-400 font-mono font-bold text-xs uppercase tracking-wider">
              <Bug className="w-4 h-4" />
              <span>Failures</span>
            </div>
          </div>
          <h2 className="text-3xl sm:text-4xl mt-4 font-mono font-bold text-white tracking-tight">
            {metrics.failures.toLocaleString()}
          </h2>
          <p className="text-[11px] font-mono text-neutral-500 mt-2">
            {metrics.executions > 0
              ? `${((metrics.failures / metrics.executions) * 100).toFixed(1)}% failure rate`
              : "0% failure rate"}
          </p>
        </div>

        <div className="bg-black/40 backdrop-blur-md border border-white/10 p-6 rounded-2xl shadow-xl hover:border-yellow-400/30 transition-all group">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 text-yellow-400 font-mono font-bold text-xs uppercase tracking-wider">
              <Clock className="w-4 h-4" />
              <span>Avg Latency</span>
            </div>
          </div>
          <h2 className="text-3xl sm:text-4xl mt-4 font-mono font-bold text-white tracking-tight">
            {metrics.avg_latency.toFixed(2)}s
          </h2>
          <p className="text-[11px] font-mono text-neutral-500 mt-2">Per execution duration</p>
        </div>

        <div className="bg-black/40 backdrop-blur-md border border-white/10 p-6 rounded-2xl shadow-xl hover:border-blue-400/30 transition-all group">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 text-blue-400 font-mono font-bold text-xs uppercase tracking-wider">
              <Server className="w-4 h-4" />
              <span>Automations</span>
            </div>
          </div>
          <h2 className="text-3xl sm:text-4xl mt-4 font-mono font-bold text-white tracking-tight">
            {metrics.automations.toLocaleString()}
          </h2>
          <p className="text-[11px] font-mono text-neutral-500 mt-2">Connected pipelines</p>
        </div>
      </div>

      {/* INTERACTIVE EXECUTION ANALYZER */}
      <section className="bg-black/30 border border-white/10 rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden backdrop-blur-md">
        <div className="absolute top-0 right-0 w-80 h-80 bg-emerald-500/10 blur-[120px] pointer-events-none"></div>

        <div className="flex items-center gap-3 mb-6">
          <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded-lg text-xs font-mono font-bold">
            POST /analyze
          </span>
          <h2 className="text-xl font-bold text-white tracking-tight">
            Live Execution Analyzer & Trace Inspector
          </h2>
        </div>

        <ExecutionDashboard />
      </section>

      {/* RECENT EXECUTIONS FLOW */}
      <section className="space-y-6">
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-emerald-400" />
            Recent Executions Flow
          </h2>
          <span className="text-xs font-mono text-neutral-500">
            {recentExecutions.length} most recent runs
          </span>
        </div>

        {loading ? (
          <div className="space-y-4 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-44 bg-white/5 rounded-2xl border border-white/5"></div>
            ))}
          </div>
        ) : recentExecutions.length === 0 ? (
          <div className="text-center py-16 bg-black/20 rounded-3xl border border-dashed border-white/15 text-neutral-400 font-mono">
            <p className="text-lg font-bold text-white mb-2">No executions recorded yet.</p>
            <p className="text-xs text-neutral-500 mb-6">
              Fire a webhook from n8n, Make, Zapier, or use the Test Playground to trigger mock runs.
            </p>
            <Link
              to="/test-playground"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-emerald-500/20 text-emerald-300 text-xs font-mono font-bold border border-emerald-500/30 hover:bg-emerald-500/30 transition-all"
            >
              Go to Test Playground <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        ) : (
          <div className="space-y-6">
            {recentExecutions.map((exec) => (
              <ExecutionCard key={exec.execution_id || exec.run_id} data={exec} />
            ))}
          </div>
        )}
      </section>

      {/* AUTOMATIONS / WORKFLOWS REGISTRY */}
      <section className="space-y-6 pt-6">
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Layers className="w-5 h-5 text-blue-400" />
            Connected Automations & Pipelines
          </h2>
          <Link
            to="/workflows"
            className="text-xs font-mono text-neutral-400 hover:text-white flex items-center gap-1"
          >
            View All Workflows <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {workflows.length === 0 ? (
          <div className="text-center py-10 border border-dashed border-white/10 rounded-2xl text-neutral-500 font-mono text-xs">
            Automations are auto-discovered seamlessly as executions flow in.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {workflows.slice(0, 6).map((wf) => (
              <Link
                key={wf.id}
                to={`/workflows/${wf.id}`}
                className="bg-black/30 border border-white/10 rounded-2xl p-5 hover:border-blue-500/40 hover:shadow-lg transition-all group block"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono uppercase text-blue-400 bg-blue-500/10 px-2.5 py-0.5 rounded-md border border-blue-500/20">
                    {wf.platform || "n8n"}
                  </span>
                  <span className="text-xs font-mono text-neutral-500">
                    {new Date(wf.created_at).toLocaleDateString()}
                  </span>
                </div>
                <h3 className="text-base font-bold text-white group-hover:text-blue-300 transition-colors truncate">
                  {wf.name}
                </h3>
                {wf.description && (
                  <p className="text-xs text-neutral-400 mt-2 line-clamp-2">
                    {wf.description}
                  </p>
                )}
                <div className="mt-4 pt-3 border-t border-white/5 flex justify-between items-center text-xs font-mono text-neutral-500">
                  <span>ID: {wf.id.slice(0, 8)}...</span>
                  <span className="text-blue-400 group-hover:translate-x-1 transition-transform">Inspect →</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
