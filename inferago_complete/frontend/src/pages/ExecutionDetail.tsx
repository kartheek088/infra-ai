import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  Clock,
  Zap,
  GitBranch,
  AlertTriangle,
  Shield,
  Brain,
  BarChart2,
  CheckCircle2,
  XCircle,
  Timer,
  Coins,
  Hash,
  Activity,
  ChevronRight,
} from "lucide-react";
import { useExecutionTrace, useExecutionTimeline, useExecutionAnomalies, useAiExplanation } from "../hooks/useExecutions";
import { useSecurityFindingsForRun } from "../hooks/useSecurityFindings";
import PlatformBadge from "../components/PlatformBadge";
import type { ExecutionTimeline, ExecutionAnomaly, AiExplanation } from "../api/executions";
import type { SecurityFinding } from "../api/findings";

// ─── Severity config ────────────────────────────────────────────────────────────

const SEVERITY_STYLE: Record<string, { color: string; bg: string; dot: string; label: string }> = {
  critical: { color: "text-red-400",    bg: "bg-red-900/30",    dot: "bg-red-400",    label: "Critical" },
  high:     { color: "text-orange-400", bg: "bg-orange-900/30", dot: "bg-orange-400", label: "High" },
  medium:   { color: "text-yellow-400", bg: "bg-yellow-900/30", dot: "bg-yellow-400", label: "Medium" },
  low:      { color: "text-blue-400",   bg: "bg-blue-900/30",  dot: "bg-blue-400",   label: "Low" },
  info:     { color: "text-gray-400",   bg: "bg-gray-800/50",  dot: "bg-gray-400",   label: "Info" },
};

const ANOMALY_ICON: Record<string, typeof Timer> = {
  latency_spike: Timer,
  token_spike:   Coins,
  node_failure:  XCircle,
  idle_gap:      Clock,
  cost_spike:    BarChart2,
};

// ─── Sub-components ─────────────────────────────────────────────────────────────

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

function SectionHeader({
  icon,
  title,
  badge,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  badge?: string | number | null;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        {icon}
        <h2 className="text-base font-semibold text-white">{title}</h2>
        {badge != null && (
          <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full font-mono">
            {badge}
          </span>
        )}
      </div>
      {action}
    </div>
  );
}

function AnomalyRow({ anomaly }: { anomaly: ExecutionAnomaly }) {
  const style = SEVERITY_STYLE[anomaly.severity] ?? SEVERITY_STYLE.info;
  const Icon  = ANOMALY_ICON[anomaly.kind] ?? AlertTriangle;
  return (
    <div className={`flex items-start gap-3 p-3 rounded-xl border ${style.bg} border-white/5`}>
      <Icon className={`w-4 h-4 flex-shrink-0 mt-0.5 ${style.color}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-sm font-semibold text-white">{anomaly.kind.replace(/_/g, " ")}</span>
          <span className={`text-xs font-medium ${style.color}`}>{style.label}</span>
          <span className="text-xs text-gray-500 font-mono ml-auto truncate max-w-[160px]">{anomaly.step}</span>
        </div>
        <p className="text-xs text-gray-400">{anomaly.detail}</p>
        {(anomaly.value != null || anomaly.threshold != null) && (
          <div className="flex gap-3 mt-1 text-xs text-gray-500 font-mono">
            {anomaly.value != null      && <span>value: <span className="text-gray-400">{anomaly.value.toLocaleString()}</span></span>}
            {anomaly.threshold != null   && <span>threshold: <span className="text-gray-400">{anomaly.threshold.toLocaleString()}</span></span>}
            {anomaly.multiplier != null  && <span>{anomaly.multiplier.toFixed(1)}× baseline</span>}
            {anomaly.idle_seconds != null && <span>{anomaly.idle_seconds.toFixed(1)}s idle</span>}
          </div>
        )}
      </div>
    </div>
  );
}

function SecurityFindingRow({ f }: { f: SecurityFinding }) {
  const style = SEVERITY_STYLE[f.severity] ?? SEVERITY_STYLE.info;
  return (
    <div className={`flex items-start gap-3 p-3 rounded-xl border ${style.bg} border-white/5`}>
      <Shield className={`w-4 h-4 flex-shrink-0 mt-0.5 ${style.color}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5 flex-wrap">
          <span className="text-sm font-semibold text-white truncate">{f.title || f.detector_id}</span>
          <span className={`text-xs font-medium ${style.color}`}>{style.label}</span>
          {f.risk_score != null && (
            <span className="text-xs text-gray-500 font-mono">risk: {f.risk_score}</span>
          )}
        </div>
        {f.description && (
          <p className="text-xs text-gray-400 mb-1">{f.description}</p>
        )}
        {f.evidence && (f.evidence as any).node_name && (
          <span className="text-xs text-gray-600 font-mono">
            node: {(f.evidence as any).node_name}
          </span>
        )}
        {f.governance_action && (
          <div className="mt-1">
            <span className="text-xs text-gray-500">action: </span>
            <span className={`text-xs font-semibold ${
              f.governance_action === "BLOCK"           ? "text-red-400"
            : f.governance_action === "REQUIRE_REVIEW"  ? "text-yellow-400"
            : f.governance_action === "ALERT"           ? "text-blue-400"
            : "text-gray-400"
            }`}>
              {f.governance_action.replace(/_/g, " ")}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Timeline tab ──────────────────────────────────────────────────────────────

function TimelineTab({ timeline }: { timeline: ExecutionTimeline }) {
  if (!timeline.steps.length) {
    return (
      <div className="text-center py-12 text-gray-600 text-sm">
        No timeline steps recorded for this execution.
      </div>
    );
  }

  const maxDuration = Math.max(
    ...timeline.steps.map((s) => s.duration_ms ?? 0),
    1,
  );

  return (
    <div className="space-y-1">
      {timeline.steps.map((step, i) => {
        const isNode = step.kind === "node";
        const isError = step.status === "failed" || step.status === "error";
        const stepTime = step.timestamp
          ? new Date(step.timestamp).toLocaleTimeString()
          : null;

        return (
          <div key={i} className="flex items-stretch gap-0 group">
            {/* Timeline line */}
            <div className="flex flex-col items-center flex-shrink-0 w-8">
              {i > 0 && (
                <div className="w-px h-3 bg-gray-700" />
              )}
              <div
                className={`w-3 h-3 rounded-full border-2 flex-shrink-0 ${
                  isError
                    ? "bg-red-900/50 border-red-500"
                    : "bg-blue-900/50 border-blue-500"
                }`}
              />
              {i < timeline.steps.length - 1 && (
                <div className="w-px flex-1 bg-gray-700" />
              )}
            </div>

            {/* Step card */}
            <div className="flex-1 pb-4 min-w-0">
              <div className={`flex items-start gap-3 p-3 rounded-xl border border-white/5 hover:border-white/10 transition-colors ${
                isError ? "bg-red-900/10" : "bg-gray-800/40"
              }`}>
                {/* Node icon or event icon */}
                <div className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center ${
                  isNode ? "bg-blue-600/20" : "bg-purple-600/20"
                }`}>
                  {isNode ? (
                    <Zap className="w-3.5 h-3.5 text-blue-400" />
                  ) : (
                    <Activity className="w-3.5 h-3.5 text-purple-400" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  {/* Step name + metadata */}
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="text-sm font-semibold text-white truncate">
                      {step.step}
                    </span>
                    <span className={`text-xs px-1.5 py-0.5 rounded font-mono flex-shrink-0 ${
                      isError ? "bg-red-900/40 text-red-400" : "bg-gray-700 text-gray-400"
                    }`}>
                      {step.kind}
                    </span>
                    {step.model && (
                      <span className="text-xs text-gray-500 font-mono flex-shrink-0">
                        {step.model}
                      </span>
                    )}
                    {step.provider && (
                      <span className="text-xs text-gray-600 font-mono flex-shrink-0">
                        {step.provider}
                      </span>
                    )}
                    <span className="text-xs text-gray-600 ml-auto flex-shrink-0">
                      {stepTime}
                    </span>
                  </div>

                  {/* Node metrics bar */}
                  {isNode && step.duration_ms != null && (
                    <div className="mb-2">
                      <div className="flex gap-4 text-xs text-gray-500 mb-1">
                        {step.tokens != null && (
                          <span>tokens: <span className="text-gray-400">{step.tokens.toLocaleString()}</span></span>
                        )}
                        {step.cost_usd != null && (
                          <span>cost: <span className="text-green-400">${step.cost_usd.toFixed(6)}</span></span>
                        )}
                        <span>latency: <span className="text-yellow-400">{step.duration_ms.toLocaleString()}ms</span></span>
                      </div>
                      {/* Latency bar */}
                      <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${isError ? "bg-red-500" : "bg-blue-500"}`}
                          style={{ width: `${Math.min((step.duration_ms / maxDuration) * 100, 100)}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Event message */}
                  {!isNode && (step as any).message && (
                    <p className="text-xs text-gray-400 mb-1">{(step as any).message}</p>
                  )}

                  {/* Error */}
                  {step.error_message && (
                    <p className="text-xs text-red-400 mt-1 font-mono">
                      {step.error_message}
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Anomalies tab ─────────────────────────────────────────────────────────────

function AnomaliesTab({ anomalies }: { anomalies: ExecutionAnomaly[] }) {
  if (!anomalies.length) {
    return (
      <div className="text-center py-12">
        <CheckCircle2 className="w-8 h-8 text-green-500 mx-auto mb-3" />
        <p className="text-gray-400 text-sm">No anomalies detected in this execution.</p>
        <p className="text-gray-600 text-xs mt-1">Latency, token usage, and cost all look normal.</p>
      </div>
    );
  }
  return (
    <div className="space-y-3">
      <p className="text-xs text-gray-500 mb-2">
        {anomalies.length} issue{anomalies.length !== 1 ? "s" : ""} found — severity ordered below.
      </p>
      {anomalies.map((a, i) => (
        <AnomalyRow key={i} anomaly={a} />
      ))}
    </div>
  );
}

// ─── Security tab ───────────────────────────────────────────────────────────────

function SecurityTab({ findings }: { findings: SecurityFinding[] }) {
  if (!findings.length) {
    return (
      <div className="text-center py-12">
        <Shield className="w-8 h-8 text-blue-500 mx-auto mb-3" />
        <p className="text-gray-400 text-sm">No security findings for this execution.</p>
        <p className="text-gray-600 text-xs mt-1">All security detectors passed.</p>
      </div>
    );
  }
  return (
    <div className="space-y-3">
      <p className="text-xs text-gray-500 mb-2">
        {findings.length} finding{findings.length !== 1 ? "s" : ""} detected.
      </p>
      {findings.map((f) => (
        <SecurityFindingRow key={f.id} f={f} />
      ))}
    </div>
  );
}

// ─── AI Summary tab ────────────────────────────────────────────────────────────

function AiSummaryTab({ explanation, isLoading }: { explanation: AiExplanation | undefined; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32 gap-3">
        <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
        <span className="text-gray-400 text-sm">Loading AI summary…</span>
      </div>
    );
  }

  if (!explanation) {
    return (
      <div className="text-center py-12 text-gray-600 text-sm">No AI summary data available.</div>
    );
  }

  if (explanation.status === "unavailable") {
    return (
      <div className="text-center py-12">
        <Brain className="w-8 h-8 text-gray-600 mx-auto mb-3" />
        <p className="text-gray-400 text-sm font-medium">AI explanation unavailable</p>
        <p className="text-gray-600 text-xs mt-1">
          {explanation.reason ?? "OPENROUTER_API_KEY is not configured on this server."}
        </p>
      </div>
    );
  }

  if (explanation.status === "pending") {
    return (
      <div className="text-center py-12">
        <Loader2 className="w-8 h-8 text-blue-400 mx-auto mb-3 animate-spin" />
        <p className="text-blue-400 text-sm font-medium">Generating AI summary…</p>
        <p className="text-gray-600 text-xs mt-1">
          The summary is being generated in the background. This page will update automatically.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {explanation.explained_at && (
        <div className="flex items-center gap-2 text-xs text-gray-600">
          <Brain className="w-3.5 h-3.5" />
          <span>
            Generated {new Date(explanation.explained_at).toLocaleString()}
            {explanation.cached && " · cached"}
          </span>
        </div>
      )}
      <div className="bg-blue-900/10 border border-blue-800/30 rounded-xl p-4">
        <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
          {explanation.text}
        </p>
      </div>
    </div>
  );
}

// ─── Nodes tab (existing trace table, slightly polished) ────────────────────────

function NodesTab({ trace }: {
  trace: {
    node_trace: Array<{
      step: number; node_name: string; model: string; prompt_tokens: number;
      completion_tokens: number; total_tokens: number; cost_usd: number;
      cost_pct: number; latency_ms?: number | null; node_type?: string | null;
      provider?: string | null; error_message?: string | null;
    }>;
  };
}) {
  if (!trace.node_trace.length) {
    return (
      <div className="text-center py-12 text-gray-600 text-sm">
        No AI node data recorded for this execution.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {trace.node_trace.map((node) => (
        <div
          key={node.step}
          className="flex items-start gap-4 p-4 bg-gray-800/50 rounded-xl border border-gray-700/50 hover:border-gray-600/50 transition-colors"
        >
          <div className="flex-shrink-0 w-8 h-8 bg-blue-600/20 rounded-full flex items-center justify-center">
            <span className="text-xs font-bold text-blue-400">{node.step}</span>
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <p className="font-semibold text-white truncate">{node.node_name}</p>
              <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded font-mono flex-shrink-0">
                {node.model}
              </span>
              {node.provider && (
                <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded flex-shrink-0">
                  {node.provider}
                </span>
              )}
              {node.node_type && (
                <span className="text-xs text-gray-600 bg-gray-800 px-2 py-0.5 rounded flex-shrink-0">
                  {node.node_type}
                </span>
              )}
            </div>

            <div className="grid grid-cols-3 gap-3 text-xs">
              <div>
                <p className="text-gray-500 mb-0.5">Prompt</p>
                <p className="text-blue-400 font-bold">{node.prompt_tokens.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-gray-500 mb-0.5">Completion</p>
                <p className="text-purple-400 font-bold">{node.completion_tokens.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-gray-500 mb-0.5">Total</p>
                <p className="text-white font-bold">{node.total_tokens.toLocaleString()}</p>
              </div>
            </div>

            {node.latency_ms && (
              <p className="text-xs text-gray-600 mt-1">latency: {node.latency_ms.toLocaleString()}ms</p>
            )}

            {node.error_message && (
              <p className="text-xs text-red-400 mt-2 font-mono">{node.error_message}</p>
            )}
          </div>

          <div className="flex-shrink-0 text-right">
            <p className="text-green-400 font-bold text-sm">${node.cost_usd.toFixed(8)}</p>
            <p className="text-xs text-gray-500 mt-0.5">{node.cost_pct}% of run</p>
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
  );
}

// ─── Events tab ────────────────────────────────────────────────────────────────

function EventsTab({ events }: { events: Array<{
  event_type: string; timestamp: string | null;
  node_name: string | null; message: string;
}> }) {
  if (!events.length) {
    return (
      <div className="text-center py-12 text-gray-600 text-sm">
        No events recorded for this execution.
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {events.map((ev, i) => (
        <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-gray-800/40 border border-white/5">
          <div className="flex-shrink-0 w-2 h-2 mt-1.5 rounded-full bg-blue-500" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-gray-500 text-xs">{ev.event_type}</span>
              {ev.node_name && (
                <span className="text-gray-400 text-xs">{ev.node_name}</span>
              )}
              <span className="text-gray-600 text-xs ml-auto">
                {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : ""}
              </span>
            </div>
            {ev.message && <p className="text-gray-500 text-xs mt-0.5">{ev.message}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Main page ─────────────────────────────────────────────────────────────────

type TabId = "timeline" | "nodes" | "events" | "anomalies" | "security" | "ai";

const TABS: { id: TabId; label: string; icon: typeof GitBranch }[] = [
  { id: "timeline", label: "Timeline",    icon: GitBranch },
  { id: "nodes",    label: "Nodes",       icon: Zap },
  { id: "events",   label: "Events",     icon: Activity },
  { id: "anomalies",label: "Anomalies",  icon: AlertTriangle },
  { id: "security", label: "Security",   icon: Shield },
  { id: "ai",       label: "AI Summary", icon: Brain },
];

export default function ExecutionDetail() {
  const { executionId } = useParams<{ executionId: string }>();
  const navigate         = useNavigate();

  const { data: trace,       isLoading: traceLoading,       isError: traceError }       = useExecutionTrace(executionId!);
  const { data: timeline,    isLoading: timelineLoading }                                    = useExecutionTimeline(executionId!);
  const { data: anomalies }                                                             = useExecutionAnomalies(executionId!);
  const { data: explanation, isLoading: explanationLoading }                              = useAiExplanation(executionId!);
  const { data: findings }                                                              = useSecurityFindingsForRun(executionId);

  const [activeTab, setActiveTab] = useState<TabId>("timeline");

  // ── Loading ────────────────────────────────────────────────────────────────
  if (traceLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
      </div>
    );
  }

  if (traceError || !trace) {
    return (
      <div className="p-6 text-center">
        <p className="text-red-400">Execution not found</p>
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

  // Compute per-tab badge counts
  const anomalyCount    = anomalies?.anomaly_count ?? 0;
  const findingCount    = findings?.length ?? 0;
  const aiStatus        = explanation?.status;
  const aiBadge         = aiStatus === "ready" ? "✓" : aiStatus === "pending" ? "…" : null;

  const tabBadges: Record<TabId, string | number | undefined> = {
    timeline:  timeline?.step_count,
    nodes:     trace.node_trace.length,
    events:    trace.events.length,
    anomalies: anomalyCount  || undefined,
    security:  findingCount   || undefined,
    ai:        aiBadge ?? undefined,
  };

  return (
    <div className="p-6 space-y-5">
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
            <h1 className="text-2xl font-bold text-white">Execution Trace</h1>
            <span className={`text-sm font-semibold ${statusColor}`}>{trace.status}</span>
            <PlatformBadge platform={trace.platform} />
          </div>
          <p className="text-gray-500 text-xs mt-1 font-mono">{executionId}</p>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard
          icon={<Zap      className="w-4 h-4 text-blue-400" />}
          label="Total tokens"
          value={trace.total_tokens.toLocaleString()}
        />
        <SummaryCard
          icon={<Coins    className="w-4 h-4 text-green-400" />}
          label="Total cost"
          value={`$${trace.total_cost_usd.toFixed(8)}`}
        />
        <SummaryCard
          icon={<Clock     className="w-4 h-4 text-yellow-400" />}
          label="Duration"
          value={trace.duration_ms ? `${(trace.duration_ms / 1000).toFixed(2)}s` : "—"}
        />
        <SummaryCard
          icon={<Hash     className="w-4 h-4 text-purple-400" />}
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

      {/* Tab bar */}
      <div className="border-b border-gray-800">
        <nav className="flex gap-0.5 overflow-x-auto scrollbar-none">
          {TABS.map(({ id, label, icon: Icon }) => {
            const badge = tabBadges[id];
            const isActive = activeTab === id;
            // Red highlight for tabs with findings
            const hasAlert = (id === "anomalies" && anomalyCount > 0) || (id === "security" && findingCount > 0);
            return (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  isActive
                    ? "border-blue-500 text-white"
                    : "border-transparent text-gray-500 hover:text-gray-300 hover:border-gray-600"
                }`}
              >
                <Icon className={`w-4 h-4 ${hasAlert && !isActive ? "text-red-400" : ""}`} />
                {label}
                {badge != null && (
                  <span className={`text-xs px-1.5 py-0.5 rounded-full font-mono ${
                    isActive ? "bg-blue-900/50 text-blue-300"
                    : hasAlert  ? "bg-red-900/50  text-red-300"
                    : "bg-gray-800 text-gray-500"
                  }`}>
                    {badge}
                  </span>
                )}
                {hasAlert && !isActive && (
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "timeline"  && (
          <div className="card">
            <SectionHeader
              icon={<GitBranch className="w-4 h-4 text-blue-400" />}
              title="Chronological Timeline"
              badge={timeline?.step_count}
            />
            {timelineLoading ? (
              <div className="flex items-center justify-center h-32">
                <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
              </div>
            ) : timeline ? (
              <TimelineTab timeline={timeline} />
            ) : (
              <div className="text-center py-12 text-gray-600 text-sm">
                Timeline data unavailable.
              </div>
            )}
          </div>
        )}

        {activeTab === "nodes" && (
          <div className="card">
            <SectionHeader
              icon={<Zap className="w-4 h-4 text-blue-400" />}
              title="AI Node Trace"
              badge={trace.node_trace.length}
            />
            <NodesTab trace={trace} />
          </div>
        )}

        {activeTab === "events" && (
          <div className="card">
            <SectionHeader
              icon={<Activity className="w-4 h-4 text-purple-400" />}
              title="Execution Events"
              badge={trace.events.length}
            />
            <EventsTab events={trace.events} />
          </div>
        )}

        {activeTab === "anomalies" && (
          <div className="card">
            <SectionHeader
              icon={<AlertTriangle className="w-4 h-4 text-yellow-400" />}
              title="Anomalies"
              badge={anomalies?.anomaly_count}
            />
            <AnomaliesTab anomalies={anomalies?.anomalies ?? []} />
          </div>
        )}

        {activeTab === "security" && (
          <div className="card">
            <SectionHeader
              icon={<Shield className="w-4 h-4 text-blue-400" />}
              title="Security Findings"
              badge={findings?.length}
            />
            <SecurityTab findings={findings ?? []} />
          </div>
        )}

        {activeTab === "ai" && (
          <div className="card">
            <SectionHeader
              icon={<Brain className="w-4 h-4 text-blue-400" />}
              title="AI Summary"
              badge={aiBadge}
            />
            <AiSummaryTab explanation={explanation} isLoading={explanationLoading} />
          </div>
        )}
      </div>

      {/* Timestamps footer */}
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
