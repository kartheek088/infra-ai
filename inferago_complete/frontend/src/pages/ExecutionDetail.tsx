import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getExecutionSummary, ExecutionSummaryData } from "../api/executions";
import ExecutionTrace from "../components/ExecutionTrace";
import PlatformBadge from "../components/PlatformBadge";
import {
  ArrowLeft,
  Loader2,
  AlertTriangle,
  Shield,
  Sparkles,
  Clock,
  Zap,
  Coins,
  CheckCircle2,
  XCircle,
  Activity,
  AlertCircle,
} from "lucide-react";

export default function ExecutionDetail() {
  const { executionId } = useParams<{ executionId: string }>();
  const navigate = useNavigate();
  const [execution, setExecution] = useState<ExecutionSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      if (!executionId) return;
      setLoading(true);
      setError(null);
      try {
        const data = await getExecutionSummary(executionId);
        setExecution(data);
      } catch (err: any) {
        console.error("Failed to load execution detail", err);
        setError(err?.response?.data?.detail || err.message || "Failed to load execution trace.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [executionId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4 text-neutral-400 font-mono">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
        <p className="text-sm">Reconstructing pipeline trace and anomaly analysis...</p>
      </div>
    );
  }

  if (error || !execution) {
    return (
      <div className="p-10 max-w-4xl mx-auto text-center font-mono">
        <button
          onClick={() => navigate(-1)}
          className="text-emerald-400 hover:text-emerald-300 mb-6 inline-flex items-center gap-2 text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Go Back
        </button>
        <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-8 text-red-400">
          <AlertCircle className="w-8 h-8 mx-auto mb-3" />
          <h2 className="text-lg font-bold mb-2">Execution Not Found</h2>
          <p className="text-xs text-red-300">{error || "The execution detail could not be loaded."}</p>
        </div>
      </div>
    );
  }

  const {
    health = "SUCCESS",
    total_duration = 0,
    total_tokens = 0,
    total_cost = 0,
    automation_name,
    platform = "n8n",
    timeline,
    anomalies = [],
    explanation,
    security_findings = [],
    governance_decision,
    max_risk_score,
    created_at,
  } = execution;

  const steps = timeline?.steps || [];

  const getGlowColor = (h: string) => {
    if (h === "FAILED" || h === "BLOCKED") return "bg-red-500/15";
    if (h === "DELAYED" || h === "REQUIRE_REVIEW") return "bg-yellow-500/15";
    return "bg-emerald-500/15";
  };

  const getStatusBadge = (h: string) => {
    switch (h) {
      case "FAILED":
      case "BLOCKED":
        return "bg-red-500/10 text-red-400 border-red-500/40";
      case "DELAYED":
      case "REQUIRE_REVIEW":
        return "bg-yellow-500/10 text-yellow-400 border-yellow-500/40";
      case "SUCCESS":
      default:
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/40";
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto font-sans animate-in fade-in duration-300 pb-24">
      {/* BACK BUTTON */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 bg-white/5 px-4 py-2 rounded-xl border border-white/10 text-neutral-400 hover:text-white mb-6 w-fit cursor-pointer transition-all duration-200 font-mono text-xs font-bold"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
      </button>

      {/* HEADER LOG WITH GLOWING BACKDROP */}
      <div className="bg-black/50 border border-white/10 rounded-3xl p-6 md:p-8 mb-8 backdrop-blur-md shadow-2xl relative overflow-hidden">
        <div className={`absolute top-0 right-0 w-96 h-96 blur-[140px] pointer-events-none ${getGlowColor(health)}`}></div>

        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <div className="flex items-center flex-wrap gap-3 mb-2">
              <h1 className="text-white text-2xl md:text-3xl font-bold tracking-tight">
                Execution Trace
              </h1>
              <span className={`text-xs px-3.5 py-1 font-mono font-bold rounded-full border shadow-inner ${getStatusBadge(health)}`}>
                {health}
              </span>
              {governance_decision && (
                <span className="text-xs px-3 py-1 font-mono font-bold rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/30">
                  Governance: {governance_decision}
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-neutral-400 mt-2">
              <span className="text-emerald-300 font-bold">{execution.execution_id}</span>
              {automation_name && (
                <span className="bg-white/5 border border-white/10 text-neutral-300 px-2.5 py-0.5 rounded-md">
                  {automation_name}
                </span>
              )}
              <PlatformBadge platform={platform} />
              {created_at && (
                <span className="text-neutral-500">
                  {new Date(created_at).toLocaleString()}
                </span>
              )}
            </div>
          </div>

          {/* TOP METRIC PILLS */}
          <div className="flex flex-wrap gap-3">
            <div className="bg-black/60 px-4 py-3 rounded-2xl border border-white/10 shadow-inner min-w-24">
              <p className="text-neutral-400 text-[10px] font-mono uppercase tracking-widest mb-0.5">Duration</p>
              <p className="text-white text-lg font-bold font-mono">
                {Number(total_duration || 0).toFixed(2)}s
              </p>
            </div>
            <div className="bg-black/60 px-4 py-3 rounded-2xl border border-white/10 shadow-inner min-w-24">
              <p className="text-neutral-400 text-[10px] font-mono uppercase tracking-widest mb-0.5">Tokens</p>
              <p className="text-white text-lg font-bold font-mono">
                {Number(total_tokens || 0).toLocaleString()}
              </p>
            </div>
            <div className="bg-black/60 px-4 py-3 rounded-2xl border border-white/10 shadow-inner min-w-24">
              <p className="text-neutral-400 text-[10px] font-mono uppercase tracking-widest mb-0.5">Cost</p>
              <p className="text-white text-lg font-bold font-mono">
                ${Number(total_cost || 0).toFixed(5)}
              </p>
            </div>
            {max_risk_score != null && (
              <div className="bg-black/60 px-4 py-3 rounded-2xl border border-white/10 shadow-inner min-w-24">
                <p className="text-neutral-400 text-[10px] font-mono uppercase tracking-widest mb-0.5">Risk Score</p>
                <p className={`text-lg font-bold font-mono ${max_risk_score > 70 ? "text-red-400" : max_risk_score > 30 ? "text-yellow-400" : "text-emerald-400"}`}>
                  {max_risk_score}/100
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* HORIZONTAL PIPELINE SEQUENCE COMPONENT */}
      <div className="bg-black/30 border border-white/10 rounded-3xl p-6 md:p-8 mb-8 shadow-xl">
        <h2 className="text-sm font-mono font-bold text-emerald-400 uppercase tracking-wider mb-6 flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"></div>
          Pipeline Sequence Trace
        </h2>
        <ExecutionTrace steps={steps} securityFindings={security_findings} />
      </div>

      {/* TWO COLUMN SECTION: HEALTH ANOMALIES & AI INTELLIGENCE */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* HEALTH ANOMALIES */}
        <div className="bg-black/30 border border-white/10 rounded-3xl p-6 md:p-8 shadow-xl">
          <h2 className="text-sm font-mono font-bold text-red-400 uppercase tracking-wider mb-6 flex items-center gap-2.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]"></div>
            Health & Execution Anomalies ({anomalies.length})
          </h2>

          {anomalies && anomalies.length > 0 ? (
            <div className="space-y-3">
              {anomalies.map((a, i) => (
                <div
                  key={i}
                  className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-3 text-red-300 font-mono text-xs leading-relaxed"
                >
                  <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                  <span>{a}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-2xl p-6 text-emerald-400 font-mono text-xs text-center flex flex-col items-center justify-center gap-2">
              <CheckCircle2 className="w-6 h-6 text-emerald-400" />
              <span>No execution anomalies or latency spikes detected.</span>
            </div>
          )}
        </div>

        {/* POST-EXECUTION AI INTELLIGENCE */}
        <div className="bg-black/30 border border-emerald-500/20 rounded-3xl p-6 md:p-8 shadow-xl relative overflow-hidden group hover:border-emerald-500/40 transition-colors">
          <div className="absolute top-0 right-0 bg-emerald-500 text-black px-3 py-1 font-mono font-bold text-[10px] rounded-bl-xl tracking-widest uppercase">
            AI Intelligence
          </div>

          <h2 className="text-sm font-mono font-bold text-white uppercase tracking-wider mb-6 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            Post-Execution Intelligence
          </h2>

          <div className="text-neutral-300 font-sans text-xs leading-relaxed whitespace-pre-wrap">
            {explanation || (
              <div className="text-neutral-500 font-mono text-xs py-4 text-center">
                AI explanation is either generating or server key not configured.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* SECURITY & GOVERNANCE FINDINGS LAYER */}
      {security_findings.length > 0 && (
        <div className="bg-black/30 border border-purple-500/20 rounded-3xl p-6 md:p-8 shadow-xl">
          <h2 className="text-sm font-mono font-bold text-purple-400 uppercase tracking-wider mb-6 flex items-center gap-2.5">
            <Shield className="w-4 h-4 text-purple-400" />
            Runtime Security & Governance Findings ({security_findings.length})
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {security_findings.map((f) => (
              <div
                key={f.id}
                className="bg-black/40 border border-purple-500/30 rounded-2xl p-5 font-mono text-xs space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white text-sm">
                    {f.title || f.detector_id}
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 text-[10px] font-bold uppercase">
                    {f.severity}
                  </span>
                </div>
                {f.description && (
                  <p className="text-neutral-400 text-xs font-sans">{f.description}</p>
                )}
                <div className="pt-2 border-t border-white/5 flex flex-wrap gap-4 text-[11px] text-neutral-400">
                  {f.node_name && <span>Node: <strong className="text-white">{f.node_name}</strong></span>}
                  {f.risk_score != null && <span>Risk: <strong className="text-purple-300">{f.risk_score}</strong></span>}
                  {f.governance_action && (
                    <span>Action: <strong className="text-amber-300">{f.governance_action}</strong></span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* If review required, show quick review button */}
          {governance_decision === "REQUIRE_REVIEW" && (
            <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-between">
              <span className="text-xs font-mono text-yellow-400">
                ⚠ Human review required before downstream execution.
              </span>
              <Link
                to="/review-queue"
                className="px-5 py-2 rounded-xl bg-yellow-500/20 text-yellow-300 border border-yellow-500/40 text-xs font-mono font-bold hover:bg-yellow-500/30 transition-all"
              >
                Open Review Queue →
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
