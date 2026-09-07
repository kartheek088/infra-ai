import React, { useState } from "react";
import { TimelineStep } from "../api/executions";
import { Shield, AlertTriangle, CheckCircle2, XCircle, Clock, Zap, Cpu } from "lucide-react";

interface ExecutionTraceProps {
  steps?: TimelineStep[];
  securityFindings?: Array<{
    node_name?: string;
    detector_id: string;
    severity: string;
    risk_score?: number;
    title?: string;
  }>;
}

export default function ExecutionTrace({ steps = [], securityFindings = [] }: ExecutionTraceProps) {
  const [selectedStep, setSelectedStep] = useState<TimelineStep | null>(null);

  if (!steps.length) {
    return (
      <div className="text-gray-500 text-center py-10 font-sans border border-dashed border-white/10 rounded-2xl">
        No pipeline steps recorded for this execution.
      </div>
    );
  }

  const getColor = (durationSeconds: number, status: string) => {
    if (status === "FAILED" || status === "failed" || status === "error") {
      return "border-red-500 bg-red-950/20 text-red-400";
    }
    if (durationSeconds > 3) return "border-red-500/80 bg-red-950/10 text-red-300";
    if (durationSeconds > 1) return "border-yellow-400/80 bg-yellow-950/10 text-yellow-300";
    return "border-emerald-500/70 bg-emerald-950/10 text-emerald-300";
  };

  const maxDuration = Math.max(
    ...steps.map((s) => (s.duration_ms ? s.duration_ms / 1000 : (s.duration_ms ?? 0.1))),
    1
  );

  return (
    <div className="w-full">
      <div className="flex items-center overflow-x-auto gap-4 py-3 px-1 no-scrollbar scroll-smooth">
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1;
          const durSeconds = step.duration_ms
            ? step.duration_ms / 1000
            : (step as any).duration ?? 0;
          const status = (step.status || "SUCCESS").toUpperCase();
          const isFailed = status === "FAILED" || status === "ERROR";
          const colorClass = getColor(durSeconds, step.status);

          // Find if there are security findings for this node
          const stepFindings = securityFindings.filter(
            (f) => f.node_name && f.node_name.toLowerCase() === step.step.toLowerCase()
          );

          return (
            <div key={index} className="flex items-center gap-4 flex-shrink-0">
              {/* NODE CARD */}
              <div
                onClick={() => setSelectedStep(step)}
                className={`min-w-[180px] max-w-[220px] bg-black/60 border ${colorClass} rounded-2xl p-4 shadow-xl backdrop-blur-md cursor-pointer hover:scale-[1.03] hover:border-white/40 transition-all duration-200 relative overflow-hidden group`}
              >
                {/* Top Badge: Node Type / Kind */}
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-400 bg-white/5 px-2 py-0.5 rounded-md flex items-center gap-1">
                    {step.kind === "node" ? <Cpu className="w-3 h-3 text-emerald-400" /> : <Zap className="w-3 h-3 text-blue-400" />}
                    {step.node_type || step.kind}
                  </span>
                  {step.model && (
                    <span className="text-[10px] font-mono text-neutral-400 truncate max-w-[90px]" title={step.model}>
                      {step.model}
                    </span>
                  )}
                </div>

                {/* Node Name */}
                <h3 className="text-sm font-bold text-white tracking-tight truncate mb-1" title={step.step}>
                  {step.step}
                </h3>

                {/* Duration & Tokens */}
                <div className="flex items-baseline justify-between mt-2">
                  <span className="text-lg font-bold font-mono text-white">
                    {durSeconds > 0 ? `${durSeconds.toFixed(2)}s` : "<0.01s"}
                  </span>
                  {step.tokens != null && step.tokens > 0 && (
                    <span className="text-xs font-mono text-neutral-400">
                      {step.tokens.toLocaleString()} tok
                    </span>
                  )}
                </div>

                {/* Status & Cost */}
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5 text-xs font-mono">
                  <span className={isFailed ? "text-red-400 font-semibold" : "text-emerald-400 font-semibold"}>
                    {status}
                  </span>
                  {step.cost_usd != null && step.cost_usd > 0 && (
                    <span className="text-neutral-400">
                      ${Number(step.cost_usd).toFixed(5)}
                    </span>
                  )}
                </div>

                {/* Progress bar */}
                <div className="w-full bg-white/10 h-1 mt-3 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      isFailed ? "bg-red-500" : durSeconds > 3 ? "bg-red-400" : durSeconds > 1 ? "bg-yellow-400" : "bg-emerald-400"
                    }`}
                    style={{
                      width: `${Math.min(Math.max((durSeconds / maxDuration) * 100, 10), 100)}%`,
                    }}
                  />
                </div>

                {/* Attached Security Warning Badge */}
                {stepFindings.length > 0 && (
                  <div className="mt-2 bg-red-500/20 border border-red-500/40 text-red-300 text-[10px] rounded-md px-2 py-1 flex items-center gap-1 font-semibold animate-pulse">
                    <Shield className="w-3 h-3 text-red-400" />
                    <span>{stepFindings.length} Security Risk{stepFindings.length > 1 ? "s" : ""}</span>
                  </div>
                )}
              </div>

              {/* DIRECTIONAL ARROW */}
              {!isLast && (
                <div className="text-neutral-600 text-xl font-bold font-mono animate-pulse flex-shrink-0 select-none">
                  →
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Step Detail Modal / Drawer */}
      {selectedStep && (
        <div className="mt-4 p-5 bg-black/70 border border-white/10 rounded-2xl text-xs font-mono backdrop-blur-md animate-in fade-in">
          <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-3">
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-white">{selectedStep.step}</span>
              <span className="px-2 py-0.5 rounded bg-white/10 text-neutral-300">
                {selectedStep.kind}
              </span>
            </div>
            <button
              onClick={() => setSelectedStep(null)}
              className="text-neutral-400 hover:text-white px-2 py-1 rounded bg-white/5 text-xs"
            >
              ✕ Close
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-neutral-300">
            <div>
              <span className="text-neutral-500 block mb-1">Status</span>
              <span className={selectedStep.status === "failed" ? "text-red-400 font-bold" : "text-emerald-400 font-bold"}>
                {selectedStep.status.toUpperCase()}
              </span>
            </div>
            <div>
              <span className="text-neutral-500 block mb-1">Duration</span>
              <span className="text-white font-bold">
                {selectedStep.duration_ms ? `${(selectedStep.duration_ms / 1000).toFixed(2)}s` : "n/a"}
              </span>
            </div>
            <div>
              <span className="text-neutral-500 block mb-1">Tokens</span>
              <span className="text-white font-bold">
                {selectedStep.tokens != null ? selectedStep.tokens.toLocaleString() : "0"}
              </span>
            </div>
            <div>
              <span className="text-neutral-500 block mb-1">Cost</span>
              <span className="text-white font-bold">
                {selectedStep.cost_usd != null ? `$${Number(selectedStep.cost_usd).toFixed(6)}` : "$0.00"}
              </span>
            </div>
            {selectedStep.model && (
              <div>
                <span className="text-neutral-500 block mb-1">Model</span>
                <span className="text-white font-bold">{selectedStep.model}</span>
              </div>
            )}
            {selectedStep.provider && (
              <div>
                <span className="text-neutral-500 block mb-1">Provider</span>
                <span className="text-white font-bold">{selectedStep.provider}</span>
              </div>
            )}
            {selectedStep.node_type && (
              <div>
                <span className="text-neutral-500 block mb-1">Type</span>
                <span className="text-white font-bold">{selectedStep.node_type}</span>
              </div>
            )}
            {selectedStep.error_message && (
              <div className="col-span-2 md:col-span-4 bg-red-950/40 border border-red-500/30 p-3 rounded-xl text-red-300">
                <span className="text-red-400 font-bold block mb-1">Error Message:</span>
                {selectedStep.error_message}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
