import { useState, useEffect } from "react";
import { FileText, ChevronRight, Loader2, Shield } from "lucide-react";
import { getAuditLogs } from "../api/findings";

const ACTION_COLORS: Record<string, string> = {
  "governance.block":          "text-red-400 bg-red-900/40",
  "governance.require_review": "text-yellow-400 bg-yellow-900/40",
  "governance.alert":           "text-blue-400 bg-blue-900/40",
  "governance.allow":           "text-green-400 bg-green-900/40",
  "policy.create":              "text-green-400 bg-green-900/40",
  "policy.update":              "text-blue-400 bg-blue-900/40",
  "policy.delete":              "text-red-400 bg-red-900/40",
};

export default function AuditLog() {
  const [logs, setLogs]     = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = { limit: 100 };
      if (filter !== "all") params.entity_type = filter;
      const data = await getAuditLogs(params);
      setLogs(data);
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = filter === "all" ? logs : logs.filter((l: any) => l.entity_type === filter);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Audit Log</h1>
          <p className="text-gray-400 text-sm mt-1">Immutable record of governance decisions and actions</p>
        </div>
        <button onClick={load} className="btn-secondary flex items-center gap-2">
          <FileText className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {["all", "security_finding", "policy"].map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              f === filter ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:text-white"
            }`}>
            {f === "all" ? "All Events" : f.replace("_", " ")}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 text-blue-400 animate-spin" /></div>
      ) : error ? (
        <div className="card p-4 border-red-800 bg-red-900/20"><p className="text-red-300 text-sm">{error}</p></div>
      ) : filtered.length === 0 ? (
        <div className="card py-12 text-center">
          <FileText className="w-10 h-10 text-gray-700 mx-auto mb-3" />
          <p className="text-gray-400">No audit events yet</p>
          <p className="text-gray-600 text-xs mt-1">Governance decisions will appear here</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((log: any) => {
            const colorClass = ACTION_COLORS[log.action] ?? "text-gray-400 bg-gray-800";
            return (
              <div key={log.id} className="card py-3 px-4 hover:border-gray-600 transition-colors">
                <div className="flex items-center gap-4">
                  <div className={`px-2.5 py-1 rounded text-xs font-bold uppercase ${colorClass}`}>
                    {log.action}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white">
                      {log.entity_type} <span className="text-gray-500 font-mono text-xs">{log.entity_id?.slice(0, 8)}…</span>
                    </p>
                    {log.note && <p className="text-xs text-gray-500 mt-0.5">{log.note}</p>}
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-xs text-gray-600">{new Date(log.created_at).toLocaleDateString()}</div>
                    <div className="text-xs text-gray-700">{new Date(log.created_at).toLocaleTimeString()}</div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-600" />
                </div>
                {Object.keys(log.snapshot ?? {}).length > 0 && (
                  <details className="mt-2">
                    <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-400">Details</summary>
                    <pre className="bg-gray-950 border border-gray-800 rounded mt-2 p-2 text-xs text-gray-500 font-mono overflow-x-auto">
                      {JSON.stringify(log.snapshot, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
