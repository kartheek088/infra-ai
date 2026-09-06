import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";
import { useDashboard } from "../hooks/useDashboard";
import HealthScoreGauge from "../components/HealthScoreGauge";
import SuggestionCard from "../components/SuggestionCard";
import CostTrendChart from "../components/CostTrendChart";
import TokenTrendChart from "../components/TokenTrendChart";
import CostBreakdownCard from "../components/CostBreakdownCard";
import InefficiencyScore from "../components/InefficiencyScore";
import RunHistoryTable from "../components/RunHistoryTable";
import PlatformBadge from "../components/PlatformBadge";

export default function WorkflowDetail() {
  const { workflowId } = useParams<{ workflowId: string }>();
  const navigate        = useNavigate();
  const { data, isLoading, isError } = useDashboard(workflowId!);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
      </div>
    );
  }

  if (isError || !data || data.error) {
    return (
      <div className="p-6 text-center">
        <p className="text-red-400">Workflow not found</p>
        <button onClick={() => navigate("/workflows")} className="btn-secondary mt-4 text-sm">
          Back to Workflows
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">

      {/* ── Header ──────────────────────────────────────── */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate("/workflows")}
          className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white">{data.workflow.name}</h1>
          {data.workflow.description && (
            <p className="text-gray-400 text-sm mt-0.5">{data.workflow.description}</p>
          )}
        </div>
        {data.token_summary?.last_run_platform && (
          <PlatformBadge platform={data.token_summary.last_run_platform} />
        )}
      </div>

      {/* ── Row 1: Health + Token Summary ───────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {data.health && data.health.score > 0 && (
          <HealthScoreGauge health={data.health} />
        )}
        <div className="card lg:col-span-2">
          <h2 className="text-sm font-semibold text-gray-400 mb-4">Token Summary</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Total Tokens"   value={data.token_summary?.total_tokens?.toLocaleString() ?? "0"} />
            <Stat label="Total Cost"     value={`$${data.token_summary?.total_cost_usd?.toFixed(6) ?? "0"}`} />
            <Stat label="Total Runs"     value={String(data.token_summary?.total_runs ?? 0)} />
            <Stat label="Last Status"    value={data.token_summary?.last_run_status ?? "—"} />
          </div>
          {data.token_summary?.last_run_at && (
            <p className="text-xs text-gray-600 mt-3">
              Last run: {new Date(data.token_summary.last_run_at).toLocaleString()}
            </p>
          )}
        </div>
      </div>

      {/* ── Row 2: Inefficiency + Cost Breakdown ────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <InefficiencyScore workflowId={workflowId!} />
        <CostBreakdownCard workflowId={workflowId!} />
      </div>

      {/* ── Row 3: Token Trend (7d/30d/90d) ─────────────── */}
      <TokenTrendChart workflowId={workflowId!} />

      {/* ── Row 4: Cost per run trend ────────────────────── */}
      {data.cost_trend?.length > 0 && (
        <CostTrendChart data={data.cost_trend} />
      )}

      {/* ── Row 5: RAG Summary ───────────────────────────── */}
      {data.rag_summary && Object.keys(data.rag_summary).length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">RAG Analytics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Avg Retrieved"  value={String(data.rag_summary.avg_chunks_retrieved)} />
            <Stat label="Avg Used"       value={String(data.rag_summary.avg_chunks_used)} />
            <Stat label="Efficiency"     value={`${(data.rag_summary.efficiency_ratio * 100).toFixed(0)}%`} />
            <Stat label="Avg Relevance"  value={data.rag_summary.avg_relevance_score?.toFixed(2)} />
          </div>
          {data.rag_summary.duplicate_rate > 0 && (
            <p className="text-xs text-yellow-500 mt-3">
              ⚠ Duplicate chunk rate: {(data.rag_summary.duplicate_rate * 100).toFixed(0)}%
            </p>
          )}
        </div>
      )}

      {/* ── Row 6: Suggestions ───────────────────────────── */}
      {data.suggestions?.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-3">
            💡 Optimization Suggestions
          </h2>
          <div className="space-y-3">
            {data.suggestions.map((s: any, i: number) => (
              <SuggestionCard key={i} suggestion={s} />
            ))}
          </div>
        </div>
      )}

      {/* ── Row 7: Active Alerts ─────────────────────────── */}
      {data.alerts?.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-3">Active Alerts</h2>
          <div className="space-y-2">
            {data.alerts.map((a: any) => (
              <div
                key={a.id}
                className="flex items-center justify-between p-3 bg-gray-800 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-yellow-400" />
                  <span className="text-sm text-gray-300 capitalize">
                    {a.type.replace("_", " ")}
                  </span>
                </div>
                <span className="text-sm text-gray-500">
                  Threshold: {a.threshold}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Row 8: Run History ───────────────────────────── */}
      <RunHistoryTable workflowId={workflowId!} />

    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-lg font-bold text-white truncate">{value}</p>
    </div>
  );
}
