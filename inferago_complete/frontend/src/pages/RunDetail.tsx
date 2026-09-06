import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Loader2, AlertCircle, CheckCircle, Clock, Zap } from "lucide-react";
import { useRunTrace } from "../hooks/useRuns";
import PlatformBadge from "../components/PlatformBadge";

export default function RunDetail() {
  const { runId }  = useParams<{ runId: string }>();
  const navigate   = useNavigate();
  const { data: trace, isLoading, isError } = useRunTrace(runId!);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
      </div>
    );
  }

  if (isError || !trace) {
    return (
      <div className="p-6 text-center">
        <p className="text-red-400">Run not found</p>
        <button onClick={() => navigate(-1)} className="btn-secondary mt-4 text-sm">
          Go back
        </button>
      </div>
    );
  }

  const statusColor =
    trace.status === "success" ? "text-green-400"
    : trace.status === "failed" ? "text-red-400"
    : "text-yellow-400";

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white">Run Trace</h1>
            <span className={`text-sm font-semibold ${statusColor}`}>
              {trace.status}
            </span>
            <PlatformBadge platform={trace.platform} />
          </div>
          <p className="text-gray-500 text-xs mt-1 font-mono">{runId}</p>
        </div>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard
          icon={<Zap className="w-4 h-4 text-blue-400" />}
          label="Total tokens"
          value={trace.total_tokens.toLocaleString()}
        />
        <SummaryCard
          icon={<Zap className="w-4 h-4 text-green-400" />}
          label="Total cost"
          value={`$${trace.total_cost_usd.toFixed(8)}`}
        />
        <SummaryCard
          icon={<Clock className="w-4 h-4 text-yellow-400" />}
          label="Duration"
          value={trace.duration_ms ? `${(trace.duration_ms / 1000).toFixed(2)}s` : "—"}
        />
        <SummaryCard
          icon={<Clock className="w-4 h-4 text-purple-400" />}
          label="Triggered by"
          value={trace.triggered_by ?? "unknown"}
        />
      </div>

      {/* Error hint */}
      {trace.error_hint && (
        <div className="flex items-start gap-3 p-4 bg-red-900/20 border border-red-800/50 rounded-xl">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-red-400 font-semibold text-sm mb-1">Error Hint</p>
            <p className="text-red-300 text-sm">{trace.error_hint}</p>
          </div>
        </div>
      )}

      {/* Node trace */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">
          Node Execution Trace
          <span className="text-sm text-gray-500 font-normal ml-2">
            ({trace.node_trace.length} AI nodes)
          </span>
        </h2>

        {trace.node_trace.length === 0 ? (
          <div className="text-center py-8 text-gray-600 text-sm">
            No AI node data recorded for this run
          </div>
        ) : (
          <div className="space-y-3">
            {trace.node_trace.map((node) => (
              <div
                key={node.step}
                className="flex items-start gap-4 p-4 bg-gray-800/50 rounded-xl border border-gray-700/50"
              >
                {/* Step number */}
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600/20 rounded-full flex items-center justify-center">
                  <span className="text-xs font-bold text-blue-400">{node.step}</span>
                </div>

                {/* Node info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <p className="font-semibold text-white truncate">{node.node_name}</p>
                    <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded font-mono flex-shrink-0">
                      {node.model}
                    </span>
                  </div>

                  {/* Token bars */}
                  <div className="grid grid-cols-3 gap-3 text-xs">
                    <div>
                      <p className="text-gray-500 mb-1">Prompt tokens</p>
                      <p className="text-blue-400 font-bold">{node.prompt_tokens.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 mb-1">Completion tokens</p>
                      <p className="text-purple-400 font-bold">{node.completion_tokens.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 mb-1">Total tokens</p>
                      <p className="text-white font-bold">{node.total_tokens.toLocaleString()}</p>
                    </div>
                  </div>
                </div>

                {/* Cost */}
                <div className="flex-shrink-0 text-right">
                  <p className="text-green-400 font-bold text-sm">
                    ${node.cost_usd.toFixed(8)}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {node.cost_pct}% of run
                  </p>
                  {/* Cost bar */}
                  <div className="w-16 h-1.5 bg-gray-700 rounded-full mt-2 ml-auto">
                    <div
                      className="h-1.5 bg-green-500 rounded-full"
                      style={{ width: `${Math.min(node.cost_pct, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Timestamps */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-400 mb-3">Timestamps</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">Started</span>
            <span className="text-gray-300 font-mono text-xs">
              {trace.started_at ? new Date(trace.started_at).toLocaleString() : "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Finished</span>
            <span className="text-gray-300 font-mono text-xs">
              {trace.finished_at ? new Date(trace.finished_at).toLocaleString() : "—"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <p className="text-lg font-bold text-white truncate">{value}</p>
    </div>
  );
}
