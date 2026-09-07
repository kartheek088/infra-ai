import { useState, useEffect } from "react";
import { Shield, AlertTriangle, XCircle, Info, ChevronRight, Loader2, ShieldAlert, ShieldCheck } from "lucide-react";
import { getFindings } from "../api/findings";

const SEVERITY_CONFIG = {
  critical: { icon: XCircle, color: "text-red-400", bg: "bg-red-900/30", border: "border-red-800", label: "Critical" },
  high:     { icon: AlertTriangle, color: "text-orange-400", bg: "bg-orange-900/30", border: "border-orange-800", label: "High" },
  medium:   { icon: ShieldAlert, color: "text-yellow-400", bg: "bg-yellow-900/30", border: "border-yellow-800", label: "Medium" },
  low:      { icon: Shield, color: "text-blue-400", bg: "bg-blue-900/30", border: "border-blue-800", label: "Low" },
  info:     { icon: Info, color: "text-gray-400", bg: "bg-gray-800/50", border: "border-gray-700", label: "Info" },
};

const ACTION_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  BLOCK:           { label: "Block",    color: "text-red-400",   bg: "bg-red-900/40" },
  REQUIRE_REVIEW:  { label: "Review",   color: "text-yellow-400", bg: "bg-yellow-900/40" },
  ALERT:           { label: "Alert",     color: "text-blue-400",  bg: "bg-blue-900/40" },
  ALLOW:           { label: "Allowed",  color: "text-green-400", bg: "bg-green-900/40" },
};

export default function SecurityFindings() {
  const [findings, setFindings]   = useState<any[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [selected, setSelected]   = useState<any | null>(null);
  const [severityFilter, setSev]  = useState<string>("all");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = { limit: 100 };
      if (severityFilter !== "all") params.severity = severityFilter;
      const data = await getFindings(params);
      setFindings(data);
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to load findings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = severityFilter === "all" ? findings : findings.filter((f: any) => f.severity === severityFilter);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Security Findings</h1>
          <p className="text-gray-400 text-sm mt-1">AI-detected risks from your workflow executions</p>
        </div>
        <button onClick={load} className="btn-secondary flex items-center gap-2">
          <Shield className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Severity summary cards */}
      <div className="grid grid-cols-5 gap-4">
        {(["critical", "high", "medium", "low", "info"] as const).map((sev) => {
          const count = findings.filter((f: any) => f.severity === sev).length;
          const cfg = SEVERITY_CONFIG[sev];
          return (
            <button key={sev} onClick={() => setSev(sev === severityFilter ? "all" : sev)}
              className={`card flex items-center gap-3 hover:border-gray-600 transition-colors ${sev === severityFilter ? "border-blue-600 ring-1 ring-blue-600" : ""}`}>
              <cfg.icon className={`w-5 h-5 ${cfg.color}`} />
              <div>
                <p className="text-lg font-bold text-white">{count}</p>
                <p className={`text-xs ${cfg.color}`}>{cfg.label}</p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Severity filter pills */}
      <div className="flex gap-2">
        {["all", "critical", "high", "medium", "low", "info"].map((sev) => (
          <button key={sev} onClick={() => setSev(sev)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              sev === severityFilter ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:text-white"
            }`}>
            {sev === "all" ? "All" : SEVERITY_CONFIG[sev as keyof typeof SEVERITY_CONFIG].label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 text-blue-400 animate-spin" /></div>
      ) : error ? (
        <div className="card p-4 border-red-800 bg-red-900/20">
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card py-12 text-center">
          <ShieldCheck className="w-10 h-10 text-green-600 mx-auto mb-3" />
          <p className="text-gray-400">No security findings</p>
          <p className="text-gray-600 text-xs mt-1">Your workflows are running cleanly</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((f: any) => {
            const cfg = SEVERITY_CONFIG[f.severity as keyof typeof SEVERITY_CONFIG] ?? SEVERITY_CONFIG.info;
            const Icon = cfg.icon;
            const actionCfg = f.governance_action ? (ACTION_CONFIG[f.governance_action] ?? { label: f.governance_action, color: "text-gray-400", bg: "bg-gray-800" }) : null;
            return (
              <div key={f.id}
                onClick={() => setSelected(f)}
                className={`card cursor-pointer hover:border-gray-600 transition-all group ${cfg.border}`}>
                <div className="flex items-start gap-4">
                  <div className={`p-2 rounded-lg ${cfg.bg} mt-0.5`}>
                    <Icon className={`w-4 h-4 ${cfg.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-bold uppercase ${cfg.color}`}>{cfg.label}</span>
                      <span className="text-xs text-gray-600">·</span>
                      <span className="text-xs text-gray-500 font-mono">{f.detector_id}</span>
                      {actionCfg && (
                        <>
                          <span className="text-xs text-gray-600">·</span>
                          <span className={`text-xs px-2 py-0.5 rounded ${actionCfg.bg} ${actionCfg.color} font-medium`}>{actionCfg.label}</span>
                        </>
                      )}
                    </div>
                    <p className="text-sm font-medium text-white group-hover:text-blue-300 transition-colors">{f.title}</p>
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{f.description}</p>
                    {f.policy_name && (
                      <p className="text-xs text-gray-600 mt-1">Policy: {f.policy_name}</p>
                    )}
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className={`text-lg font-bold ${f.risk_score >= 75 ? "text-red-400" : f.risk_score >= 50 ? "text-yellow-400" : "text-gray-400"}`}>
                      {f.risk_score}
                    </div>
                    <div className="text-xs text-gray-600">risk score</div>
                    <div className="text-xs text-gray-600 mt-1">{new Date(f.created_at).toLocaleDateString()}</div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-gray-400 mt-1" />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detail modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4" onClick={() => setSelected(null)}>
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl p-6 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-white">{selected.title}</h2>
                <p className="text-xs text-gray-500 mt-1 font-mono">{selected.id}</p>
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-500 hover:text-white"><XCircle className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="card p-3">
                  <p className="text-xs text-gray-500 mb-1">Severity</p>
                  <p className={`text-sm font-bold ${SEVERITY_CONFIG[selected.severity as keyof typeof SEVERITY_CONFIG]?.color}`}>
                    {SEVERITY_CONFIG[selected.severity as keyof typeof SEVERITY_CONFIG]?.label ?? selected.severity}
                  </p>
                </div>
                <div className="card p-3">
                  <p className="text-xs text-gray-500 mb-1">Risk Score</p>
                  <p className={`text-sm font-bold ${selected.risk_score >= 75 ? "text-red-400" : selected.risk_score >= 50 ? "text-yellow-400" : "text-gray-400"}`}>
                    {selected.risk_score}
                  </p>
                </div>
                <div className="card p-3">
                  <p className="text-xs text-gray-500 mb-1">Action</p>
                  <p className="text-sm font-bold text-white">{selected.governance_action ?? "None"}</p>
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-2">Description</p>
                <p className="text-sm text-gray-300">{selected.description}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-2">Evidence</p>
                <pre className="bg-gray-950 border border-gray-800 rounded-lg p-3 text-xs text-gray-400 font-mono overflow-x-auto">
                  {JSON.stringify(selected.evidence ?? {}, null, 2)}
                </pre>
              </div>
              {selected.policy_name && (
                <div className="card p-3 bg-blue-900/20 border-blue-800">
                  <p className="text-xs text-blue-400 font-medium">Applied Policy</p>
                  <p className="text-sm text-white mt-1">{selected.policy_name}</p>
                </div>
              )}
              <div className="text-xs text-gray-600">
                Detected at {new Date(selected.created_at).toLocaleString()} · Run {selected.run_id?.slice(0, 8)}…
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
