import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Zap, Plus, Trash2, Send, CheckCircle, AlertCircle, Loader2, Copy, ChevronDown } from "lucide-react";
import { useWorkflows } from "../hooks/useWorkflows";

// ── Template definitions ─────────────────────────────────────────────────────

type NodeTemplate = {
  node_name: string;
  node_type: string;
  model: string;
  provider: string;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  latency_ms: number;
};

type Template = {
  label: string;
  description: string;
  workflow_id: string;
  nodes: NodeTemplate[];
};

const TEMPLATES: Template[] = [
  {
    label: "LLM Agent",
    description: "Single GPT-4o completion call",
    workflow_id: "wf-llm-demo-001",
    nodes: [
      { node_name: "GPT-4o Completion", node_type: "llm", model: "gpt-4o", provider: "openai",
        prompt_tokens: 1500, completion_tokens: 500, cost_usd: 0.01, latency_ms: 2500 },
    ],
  },
  {
    label: "RAG Pipeline",
    description: "Embed → search → synthesis",
    workflow_id: "wf-rag-demo-001",
    nodes: [
      { node_name: "Embed Query", node_type: "embedding", model: "text-embedding-3-small", provider: "openai",
        prompt_tokens: 50, completion_tokens: 0, cost_usd: 0.0001, latency_ms: 150 },
      { node_name: "Vector Search", node_type: "search", model: "", provider: "pinecone",
        prompt_tokens: 0, completion_tokens: 0, cost_usd: 0.0, latency_ms: 80 },
      { node_name: "GPT-4o Synthesis", node_type: "llm", model: "gpt-4o", provider: "openai",
        prompt_tokens: 1200, completion_tokens: 300, cost_usd: 0.0075, latency_ms: 2000 },
    ],
  },
  {
    label: "Tool Calling",
    description: "Router → tool → synthesizer",
    workflow_id: "wf-tool-demo-001",
    nodes: [
      { node_name: "Router LLM", node_type: "llm", model: "gpt-4o-mini", provider: "openai",
        prompt_tokens: 100, completion_tokens: 20, cost_usd: 0.0001, latency_ms: 500 },
      { node_name: "Web Search Tool", node_type: "tool", model: "", provider: "serpapi",
        prompt_tokens: 0, completion_tokens: 0, cost_usd: 0.005, latency_ms: 1200 },
      { node_name: "Response Synthesizer", node_type: "llm", model: "gpt-4o", provider: "openai",
        prompt_tokens: 800, completion_tokens: 200, cost_usd: 0.005, latency_ms: 1800 },
    ],
  },
  {
    label: "Multi-Node",
    description: "Parse → reason → execute → format",
    workflow_id: "wf-multi-001",
    nodes: [
      { node_name: "Input Parser", node_type: "transform", model: "", provider: "",
        prompt_tokens: 0, completion_tokens: 0, cost_usd: 0.0, latency_ms: 50 },
      { node_name: "Claude 3.5 Reasoning", node_type: "llm", model: "claude-3-5-sonnet-20241022", provider: "anthropic",
        prompt_tokens: 2000, completion_tokens: 800, cost_usd: 0.021, latency_ms: 4000 },
      { node_name: "Code Executor", node_type: "tool", model: "", provider: "bash",
        prompt_tokens: 0, completion_tokens: 0, cost_usd: 0.0, latency_ms: 1500 },
      { node_name: "Output Formatter", node_type: "transform", model: "", provider: "",
        prompt_tokens: 0, completion_tokens: 0, cost_usd: 0.0, latency_ms: 100 },
    ],
  },
];

const NODE_TYPES  = ["llm", "embedding", "search", "tool", "transform", "other"];
const PROVIDERS   = ["openai", "anthropic", "google", "pinecone", "serpapi", "bash", "other", ""];
const API_KEY_LS  = "ari-playground-api-key";

// ── Helpers ──────────────────────────────────────────────────────────────────

function cloneNode(n: NodeTemplate): NodeTemplate {
  return { ...n };
}

function buildPayload(
  selectedWorkflowId: string,
  nodes: NodeTemplate[],
): object {
  return {
    workflow_id:  selectedWorkflowId,
    execution_id: `playground-${Date.now()}`,
    status:       "success",
    triggered_by: "test-playground",
    started_at:   new Date().toISOString(),
    finished_at:  new Date().toISOString(),
    nodes: nodes.map((n) => ({
      node_name:         n.node_name,
      node_type:         n.node_type,
      model:             n.model,
      provider:          n.provider,
      prompt_tokens:     n.prompt_tokens,
      completion_tokens: n.completion_tokens,
      total_tokens:      n.prompt_tokens + n.completion_tokens,
      cost_usd:          n.cost_usd,
      latency_ms:        n.latency_ms,
    })),
  };
}

function calcSummary(nodes: NodeTemplate[]) {
  const totalTokens = nodes.reduce((s, n) => s + n.prompt_tokens + n.completion_tokens, 0);
  const totalCost    = nodes.reduce((s, n) => s + n.cost_usd, 0);
  return { totalTokens, totalCost };
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function TestPlayground() {
  const navigate    = useNavigate();
  const { data: workflows } = useWorkflows();

  const [activeTemplateIdx, setActiveTemplateIdx] = useState(0);
  const [customWorkflowId, setCustomWorkflowId]  = useState("");
  const [nodes, setNodes]                         = useState<NodeTemplate[]>(cloneNodes(TEMPLATES[0].nodes));
  const [apiKey, setApiKey]                       = useState(() => localStorage.getItem(API_KEY_LS) ?? "");
  const [sending, setSending]                       = useState(false);
  const [result, setResult]                       = useState<{ ok: boolean; data?: { run_id?: string; [k: string]: unknown }; error?: string } | null>(null);

  const activeTemplate = TEMPLATES[activeTemplateIdx];

  // All workflow IDs we can target — registered ones + the built-in demo IDs
  const availableWorkflows = useMemo(() => {
    const registered = (workflows ?? []).map((w) => ({
      id:   w.n8n_workflow_id ?? w.id,
      name: w.name,
    }));
    const builtIn = TEMPLATES.map((t) => ({ id: t.workflow_id, name: `[Demo] ${t.label}` }));
    const seen = new Set<string>();
    return [...registered, ...builtIn].filter((w) => {
      if (seen.has(w.id)) return false;
      seen.add(w.id);
      return true;
    });
  }, [workflows]);

  // Default to the template's built-in workflow_id
  const [selectedWfId, setSelectedWfId] = useState(activeTemplate.workflow_id);

  function cloneNodes(arr: NodeTemplate[]): NodeTemplate[] {
    return arr.map(cloneNode);
  }

  function applyTemplate(idx: number) {
    const t = TEMPLATES[idx];
    setActiveTemplateIdx(idx);
    setNodes(cloneNodes(t.nodes));
    setSelectedWfId(t.workflow_id);
    setResult(null);
  }

  function addNode() {
    setNodes((prev) => [
      ...prev,
      { node_name: "New Node", node_type: "llm", model: "gpt-4o", provider: "openai",
        prompt_tokens: 100, completion_tokens: 50, cost_usd: 0.0005, latency_ms: 1000 },
    ]);
  }

  function removeNode(i: number) {
    setNodes((prev) => prev.filter((_, idx) => idx !== i));
  }

  function updateNode(i: number, field: keyof NodeTemplate, value: string | number) {
    setNodes((prev) =>
      prev.map((n, idx) =>
        idx === i ? { ...n, [field]: field === "model" || field === "provider" || field === "node_name" || field === "node_type" ? String(value) : Number(value) } : n
      )
    );
  }

  const { totalTokens, totalCost } = useMemo(() => calcSummary(nodes), [nodes]);

  const payload = useMemo(
    () => buildPayload(selectedWfId, nodes),
    [selectedWfId, nodes],
  );

  async function sendExecution() {
    if (!apiKey.trim()) { setResult({ ok: false, error: "API key is required — paste your ARI API key above." }); return; }
    setSending(true);
    setResult(null);
    try {
      const baseUrl = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "") || "";
      const endpoint = baseUrl ? `${baseUrl}/api/webhook/custom` : "/api/webhook/custom";
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey.trim() },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setResult({ ok: false, error: data.detail ?? data.reason ?? `HTTP ${res.status}: ${res.statusText}` });
      } else {
        localStorage.setItem(API_KEY_LS, apiKey.trim());
        setResult({ ok: true, data });
      }
    } catch (err: unknown) {
      setResult({ ok: false, error: err instanceof Error ? err.message : String(err) });
    } finally {
      setSending(false);
    }
  }

  function copyJson() {
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
  }

  function copyCurl() {
    const k = apiKey.trim();
    const body = JSON.stringify(payload);
    const curl = `curl -X POST '${import.meta.env.VITE_API_URL ?? ""}/api/webhook/custom' \\\n  -H 'Content-Type: application/json' \\\n  -H 'X-API-Key: ${k}' \\\n  -d '${body}'`;
    navigator.clipboard.writeText(curl);
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Zap className="w-6 h-6 text-yellow-400" /> Test Playground
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Send mock AI workflow executions to ARI — no n8n or external services needed.
          </p>
        </div>
      </div>

      {/* ── API Key ─────────────────────────────────────────────────────── */}
      <div className="card p-5">
        <label className="block text-sm font-medium text-gray-300 mb-1">
          ARI API Key <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="ari-test-key-001  (or paste your own from Settings → API Keys)"
          className="input w-full font-mono text-sm"
        />
        <p className="text-xs text-gray-600 mt-1">
          Use <span className="font-mono text-gray-500">ari-test-key-001</span> if you ran the seed script,
          or generate one at <span className="font-mono text-gray-500">Settings → API Keys</span>.
        </p>
      </div>

      {/* ── Template Selector ───────────────────────────────────────────── */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wide">
          1 · Choose Template
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {TEMPLATES.map((t, idx) => (
            <button
              key={t.label}
              onClick={() => applyTemplate(idx)}
              className={`p-4 rounded-lg border text-left transition-all ${
                activeTemplateIdx === idx
                  ? "border-blue-500 bg-blue-600/10"
                  : "border-gray-700 bg-gray-800/40 hover:border-gray-600"
              }`}
            >
              <p className={`font-semibold text-sm ${activeTemplateIdx === idx ? "text-blue-400" : "text-gray-200"}`}>
                {t.label}
              </p>
              <p className="text-xs text-gray-500 mt-1">{t.description}</p>
              <p className="text-xs text-gray-600 mt-1">{t.nodes.length} node{t.nodes.length !== 1 ? "s" : ""}</p>
            </button>
          ))}
        </div>
      </div>

      {/* ── Workflow Selector ───────────────────────────────────────────── */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wide">
          2 · Target Workflow
        </h2>
        <div className="relative">
          <select
            value={selectedWfId}
            onChange={(e) => setSelectedWfId(e.target.value)}
            className="input w-full pr-10 appearance-none"
          >
            <option value="" disabled>— Select a workflow —</option>
            {availableWorkflows.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name} ({w.id})
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
        </div>
        <p className="text-xs text-gray-600 mt-2">
          Select a registered workflow or use one of the demo IDs built into the template.
        </p>
      </div>

      {/* ── Node Editor ─────────────────────────────────────────────────── */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
            3 · Node Editor
          </h2>
          <button onClick={addNode} className="btn-secondary text-xs flex items-center gap-1">
            <Plus className="w-3.5 h-3.5" /> Add Node
          </button>
        </div>

        <div className="space-y-4">
          {nodes.map((node, i) => (
            <div key={i} className="bg-gray-800/60 border border-gray-700 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-gray-500">Node {i + 1}</span>
                <button onClick={() => removeNode(i)} className="text-gray-500 hover:text-red-400 transition-colors">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <Field label="Name" value={node.node_name} onChange={(v) => updateNode(i, "node_name", v)} />
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Type</label>
                  <select value={node.node_type} onChange={(e) => updateNode(i, "node_type", e.target.value)}
                    className="input w-full text-xs py-1.5">
                    {NODE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <Field label="Model" value={node.model} onChange={(v) => updateNode(i, "model", v)} />
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Provider</label>
                  <select value={node.provider} onChange={(e) => updateNode(i, "provider", e.target.value)}
                    className="input w-full text-xs py-1.5">
                    {PROVIDERS.map((p) => <option key={p} value={p}>{p || "(none)"}</option>)}
                  </select>
                </div>
                <Field label="Prompt Tokens" value={String(node.prompt_tokens)} type="number"
                  onChange={(v) => updateNode(i, "prompt_tokens", Number(v))} />
                <Field label="Completion Tokens" value={String(node.completion_tokens)} type="number"
                  onChange={(v) => updateNode(i, "completion_tokens", Number(v))} />
                <Field label="Cost (USD)" value={String(node.cost_usd)} type="number" step="0.000001"
                  onChange={(v) => updateNode(i, "cost_usd", Number(v))} />
                <Field label="Latency (ms)" value={String(node.latency_ms)} type="number"
                  onChange={(v) => updateNode(i, "latency_ms", Number(v))} />
              </div>
            </div>
          ))}
        </div>

        {/* Summary bar */}
        <div className="mt-4 flex items-center gap-6 bg-gray-900/60 rounded-lg px-4 py-3 border border-gray-700">
          <div>
            <span className="text-xs text-gray-500">Total Tokens</span>
            <p className="font-mono text-white font-semibold">{totalTokens.toLocaleString()}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500">Total Cost</span>
            <p className="font-mono text-green-400 font-semibold">${totalCost.toFixed(6)}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500">Nodes</span>
            <p className="font-mono text-white font-semibold">{nodes.length}</p>
          </div>
        </div>
      </div>

      {/* ── JSON Preview ───────────────────────────────────────────────── */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">4 · Payload Preview</h2>
          <div className="flex gap-2">
            <button onClick={copyJson} className="text-xs text-gray-400 hover:text-white flex items-center gap-1 transition-colors">
              <Copy className="w-3.5 h-3.5" /> Copy JSON
            </button>
            <button onClick={copyCurl} className="text-xs text-gray-400 hover:text-white flex items-center gap-1 transition-colors">
              <Copy className="w-3.5 h-3.5" /> Copy as curl
            </button>
          </div>
        </div>
        <pre className="bg-gray-950 border border-gray-800 rounded-lg p-4 text-xs text-gray-300 font-mono overflow-x-auto max-h-72 overflow-y-auto">
          {JSON.stringify(payload, null, 2)}
        </pre>
      </div>

      {/* ── Send ───────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-4">
        <button
          onClick={sendExecution}
          disabled={sending || !selectedWfId || !apiKey.trim()}
          className="btn-primary flex items-center gap-2 px-6 py-2.5 text-base disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {sending
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Sending…</>
            : <><Send className="w-4 h-4" /> Send Test Execution</>}
        </button>
        {!selectedWfId && <span className="text-sm text-gray-500">Select a workflow first</span>}
      </div>

      {/* ── Response ─────────────────────────────────────────────────────── */}
      {result && (
        <div className={`card p-5 border ${result.ok ? "border-green-700 bg-green-950/20" : "border-red-700 bg-red-950/20"}`}>
          {result.ok ? (
            <>
              <div className="flex items-center gap-2 text-green-400 font-semibold mb-3">
                <CheckCircle className="w-5 h-5" /> Execution recorded!
              </div>
              <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
                {Object.entries(result.data ?? {}).map(([k, v]) => (
                  <div key={k}>
                    <span className="text-gray-500 text-xs">{k}</span>
                    <p className="text-gray-200 font-mono text-xs truncate">{String(v)}</p>
                  </div>
                ))}
              </div>
              {"run_id" in (result.data ?? {}) && (
                <button
                  onClick={() => navigate(`/executions/${result.data?.run_id}`)}
                  className="mt-4 text-sm text-blue-400 hover:text-blue-300 flex items-center gap-1"
                >
                  View Execution → <ChevronDown className="w-3 h-3" />
                </button>
              )}
            </>
          ) : (
            <div className="flex items-start gap-2 text-red-400">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Request Failed</p>
                <p className="text-sm text-red-300 mt-1">{result.error}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Tiny reusable field ────────────────────────────────────────────────────────

function Field({
  label, value, type = "text", step,
  onChange,
}: {
  label: string;
  value: string;
  type?: string;
  step?: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="block text-xs text-gray-500 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        step={step}
        onChange={(e) => onChange(e.target.value)}
        className="input w-full text-xs py-1.5 font-mono"
      />
    </div>
  );
}
