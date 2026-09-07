import React from "react";
import { Link } from "react-router-dom";
import { ExecutionSummaryData } from "../api/executions";
import { Shield, Sparkles, AlertTriangle, ArrowRight, Zap } from "lucide-react";

interface ExecutionCardProps {
  data?: ExecutionSummaryData;
  execution?: ExecutionSummaryData;
}

export default function ExecutionCard({ data, execution }: ExecutionCardProps) {
  const d = data || execution;
  if (!d) return null;

  const {
    execution_id,
    run_id,
    automation_name,
    health = "SUCCESS",
    anomalies = [],
    total_tokens = 0,
    total_cost = 0,
    total_duration = 0,
    explanation = "",
    timeline,
    security_findings = [],
    governance_decision,
    created_at,
  } = d;

  const parsedTimeline = typeof timeline === "string" ? JSON.parse(timeline) : timeline;
  const steps = parsedTimeline?.steps || [];

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return null;
    const dt = new Date(dateStr);
    return dt.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getHealthBadge = (h: string) => {
    switch (h) {
      case "FAILED":
      case "BLOCKED":
        return "bg-red-500/10 text-red-400 border-red-500/30";
      case "DELAYED":
      case "REQUIRE_REVIEW":
        return "bg-yellow-500/10 text-yellow-400 border-yellow-500/30";
      case "SUCCESS":
      default:
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    }
  };

  const targetId = run_id || execution_id;

  return (
    <div className="bg-black/40 border border-white/10 rounded-2xl overflow-hidden backdrop-blur-md shadow-xl font-sans hover:border-emerald-500/40 hover:shadow-emerald-500/5 transition-all duration-300 group">
      {/* TERMINAL HEADER */}
      <div className="flex items-center justify-between gap-4 px-6 py-4 bg-white/5 border-b border-white/10">
        <div className="flex items-center gap-3">
          {/* macOS traffic light dots */}
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500/80 shadow-sm"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-400/80 shadow-sm"></div>
            <div className="w-3 h-3 rounded-full bg-emerald-500/80 shadow-sm"></div>
          </div>
          <span className="text-xs font-mono text-neutral-400">
            exec_id: <span className="text-emerald-300 font-bold ml-1">{execution_id}</span>
          </span>
          {automation_name && (
            <span className="hidden sm:inline-block bg-white/5 text-neutral-300 text-xs px-2.5 py-0.5 rounded-md font-mono border border-white/5">
              {automation_name}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {created_at && (
            <span className="text-xs font-mono text-neutral-500 hidden md:block">
              {formatDate(created_at)}
            </span>
          )}
          <span className={`text-xs px-3 py-1 font-mono font-bold rounded-full border shadow-inner ${getHealthBadge(health)}`}>
            {health}
          </span>
        </div>
      </div>

      {/* CARD BODY */}
      <div className="p-6">
        {/* SUMMARY METRICS */}
        <div className="mb-6 grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white/5 p-4 rounded-xl border border-white/5">
            <p className="text-emerald-400 text-xs font-mono tracking-wider uppercase mb-1">Status</p>
            <p className={`text-base font-bold font-mono ${health === "SUCCESS" ? "text-emerald-400" : health === "FAILED" || health === "BLOCKED" ? "text-red-400" : "text-yellow-400"}`}>
              {health}
            </p>
          </div>
          <div className="bg-white/5 p-4 rounded-xl border border-white/5">
            <p className="text-emerald-400 text-xs font-mono tracking-wider uppercase mb-1">Duration</p>
            <p className="text-white text-base font-bold font-mono">
              {Number(total_duration || 0).toFixed(2)}s
            </p>
          </div>
          <div className="bg-white/5 p-4 rounded-xl border border-white/5">
            <p className="text-emerald-400 text-xs font-mono tracking-wider uppercase mb-1">Tokens</p>
            <p className="text-white text-base font-bold font-mono">
              {Number(total_tokens || 0).toLocaleString()}
            </p>
          </div>
          <div className="bg-white/5 p-4 rounded-xl border border-white/5">
            <p className="text-emerald-400 text-xs font-mono tracking-wider uppercase mb-1">Cost</p>
            <p className="text-white text-base font-bold font-mono">
              ${Number(total_cost || 0).toFixed(5)}
            </p>
          </div>
        </div>

        {/* PIPELINE SEQUENCE OVERVIEW */}
        {steps.length > 0 && (
          <div className="mb-6">
            <p className="text-emerald-400 text-xs font-mono tracking-wider uppercase mb-3 flex items-center gap-2">
              <Zap className="w-3.5 h-3.5" /> Pipeline Sequence
            </p>
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
              {steps.slice(0, 6).map((s: any, idx: number) => (
                <React.Fragment key={idx}>
                  <span className={`px-3 py-1.5 rounded-lg border flex items-center gap-1.5 ${
                    s.status === "failed" ? "bg-red-950/30 border-red-500/40 text-red-300" : "bg-neutral-900 border-neutral-800 text-neutral-300"
                  }`}>
                    {s.step || s}
                    {s.duration_ms && (
                      <span className="text-[10px] text-neutral-500">
                        {(s.duration_ms / 1000).toFixed(1)}s
                      </span>
                    )}
                  </span>
                  {idx !== Math.min(steps.length, 6) - 1 && (
                    <span className="text-neutral-600 font-bold text-sm select-none">→</span>
                  )}
                </React.Fragment>
              ))}
              {steps.length > 6 && (
                <span className="text-neutral-500 text-xs ml-1">
                  +{steps.length - 6} more steps
                </span>
              )}
            </div>
          </div>
        )}

        {/* ANOMALIES & SECURITY FINDINGS */}
        {(anomalies.length > 0 || security_findings.length > 0) && (
          <div className="mb-6 space-y-2">
            {anomalies.length > 0 && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 text-red-300 text-xs font-mono space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-red-400 mb-1">
                  <AlertTriangle className="w-3.5 h-3.5" /> Anomalies Detected ({anomalies.length})
                </div>
                {anomalies.slice(0, 3).map((a, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-red-500">⚠</span>
                    <span>{a}</span>
                  </div>
                ))}
              </div>
            )}

            {security_findings.length > 0 && (
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 text-amber-300 text-xs font-mono space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-amber-400 mb-1">
                  <Shield className="w-3.5 h-3.5" /> Security Findings ({security_findings.length})
                </div>
                {security_findings.slice(0, 2).map((sf, i) => (
                  <div key={i} className="flex gap-2">
                    <span>🛡</span>
                    <span>{sf.title || sf.detector_id} ({sf.severity})</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* AI EXPLANATION */}
        {explanation && (
          <div className="mt-4 bg-emerald-950/20 border border-emerald-500/20 rounded-xl p-4 text-neutral-300 text-xs font-sans leading-relaxed">
            <div className="flex items-center gap-2 text-emerald-400 font-mono font-bold text-xs uppercase mb-2">
              <Sparkles className="w-3.5 h-3.5" /> Post-Execution Intelligence
            </div>
            <p className="line-clamp-3 whitespace-pre-wrap">{explanation}</p>
          </div>
        )}

        {/* LINK TO FULL TRACE */}
        <div className="mt-6 flex justify-end">
          <Link
            to={`/executions/${targetId}`}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/5 hover:bg-emerald-500/20 hover:text-emerald-300 text-neutral-300 text-xs font-mono font-bold border border-white/10 hover:border-emerald-500/30 transition-all duration-200"
          >
            Inspect Execution Trace <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
