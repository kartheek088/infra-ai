import React, { useState } from "react";
import { getExecutionSummary, analyzeExecution, ExecutionSummaryData } from "../api/executions";
import ExecutionCard from "./ExecutionCard";
import { Search, Play, Loader2, AlertCircle, Code } from "lucide-react";

export default function ExecutionDashboard() {
  const [executionId, setExecutionId] = useState("");
  const [jsonPayload, setJsonPayload] = useState("");
  const [mode, setMode] = useState<"id" | "json">("id");
  const [result, setResult] = useState<ExecutionSummaryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const samplePayload = {
    workflow_id: "Sample AI Agent",
    platform: "custom",
    nodes: [
      {
        node_name: "Trigger Webhook",
        node_type: "trigger",
        latency_ms: 120,
        total_tokens: 0,
        cost_usd: 0.0,
      },
      {
        node_name: "Vector Search Retriever",
        node_type: "rag",
        latency_ms: 450,
        total_tokens: 150,
        cost_usd: 0.00015,
      },
      {
        node_name: "Claude 3.5 Sonnet Synthesizer",
        node_type: "llm",
        model: "claude-3-5-sonnet",
        provider: "anthropic",
        latency_ms: 2800,
        prompt_tokens: 850,
        completion_tokens: 320,
        total_tokens: 1170,
        cost_usd: 0.0078,
      },
      {
        node_name: "Slack Alert Dispatcher",
        node_type: "http_request",
        latency_ms: 220,
        total_tokens: 0,
        cost_usd: 0.0,
      },
    ],
  };

  const handleFetchById = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!executionId.trim()) return;

    setLoading(true);
    setErrorMsg("");
    setResult(null);

    try {
      const data = await getExecutionSummary(executionId.trim());
      setResult(data);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || err.message || "Failed to fetch execution summary");
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzePayload = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg("");
    setResult(null);

    try {
      const parsed = jsonPayload.trim()
        ? JSON.parse(jsonPayload)
        : samplePayload;
      const data = await analyzeExecution(parsed);
      setResult(data);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || err.message || "Invalid JSON payload or analysis error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto font-sans">
      {/* MODE SELECTOR */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => { setMode("id"); setErrorMsg(""); }}
          className={`px-4 py-2 rounded-xl text-xs font-mono font-bold transition-all ${
            mode === "id"
              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
              : "bg-white/5 text-neutral-400 border border-white/5 hover:text-white"
          }`}
        >
          🔍 Inspect by Execution ID
        </button>
        <button
          type="button"
          onClick={() => {
            setMode("json");
            setErrorMsg("");
            if (!jsonPayload) setJsonPayload(JSON.stringify(samplePayload, null, 2));
          }}
          className={`px-4 py-2 rounded-xl text-xs font-mono font-bold transition-all ${
            mode === "json"
              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
              : "bg-white/5 text-neutral-400 border border-white/5 hover:text-white"
          }`}
        >
          ⚡ Live Payload Analyzer
        </button>
      </div>

      {/* INPUT PANEL */}
      <div className="bg-black/40 backdrop-blur-md border border-white/10 rounded-2xl p-6 shadow-2xl">
        {mode === "id" ? (
          <form onSubmit={handleFetchById} className="flex flex-col sm:flex-row gap-3 items-center">
            <div className="relative flex-1 w-full">
              <Search className="w-5 h-5 text-neutral-500 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={executionId}
                onChange={(e) => setExecutionId(e.target.value)}
                placeholder="Enter execution_id or run UUID..."
                className="w-full bg-black/60 border border-white/15 text-white placeholder-neutral-500 pl-12 pr-4 py-3.5 rounded-xl font-mono text-sm focus:outline-none focus:border-emerald-400 transition-colors shadow-inner"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !executionId.trim()}
              className="px-8 py-3.5 rounded-xl font-mono font-bold text-sm bg-gradient-to-r from-emerald-400 to-teal-500 text-black shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/40 hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:pointer-events-none transition-all duration-200 whitespace-nowrap w-full sm:w-auto flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              {loading ? "Analyzing..." : "Inspect Trace"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleAnalyzePayload} className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-neutral-400 flex items-center gap-1.5">
                <Code className="w-4 h-4 text-emerald-400" /> Paste Execution JSON payload
              </span>
              <button
                type="button"
                onClick={() => setJsonPayload(JSON.stringify(samplePayload, null, 2))}
                className="text-xs font-mono text-emerald-400 hover:underline"
              >
                Load Sample Payload
              </button>
            </div>
            <textarea
              rows={7}
              value={jsonPayload}
              onChange={(e) => setJsonPayload(e.target.value)}
              placeholder="Paste raw execution payload here..."
              className="w-full bg-black/60 border border-white/15 text-white placeholder-neutral-500 p-4 rounded-xl font-mono text-xs focus:outline-none focus:border-emerald-400 transition-colors shadow-inner leading-relaxed"
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading}
                className="px-8 py-3 rounded-xl font-mono font-bold text-sm bg-gradient-to-r from-emerald-400 to-teal-500 text-black shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/40 hover:scale-[1.02] active:scale-95 disabled:opacity-50 transition-all duration-200 flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                {loading ? "Analyzing Live..." : "Analyze Execution"}
              </button>
            </div>
          </form>
        )}

        {errorMsg && (
          <div className="mt-4 bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-400 text-xs font-mono flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
      </div>

      {loading && (
        <div className="flex justify-center items-center py-12 gap-3 text-neutral-400 font-mono text-sm">
          <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
          <span>Reconstructing execution pipeline & anomalies...</span>
        </div>
      )}

      {result && !loading && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          <ExecutionCard data={result} />
        </div>
      )}
    </div>
  );
}
