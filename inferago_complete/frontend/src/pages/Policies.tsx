import { useState, useEffect } from "react";
import { Plus, Trash2, Shield, ChevronRight, Loader2, XCircle, CheckCircle, AlertTriangle } from "lucide-react";
import { getPolicies, createPolicy, deletePolicy } from "../api/policies";

const ACTION_CONFIG: Record<string, { color: string; bg: string; icon: any }> = {
  BLOCK:          { color: "text-red-400",   bg: "bg-red-900/40",   icon: XCircle },
  REQUIRE_REVIEW: { color: "text-yellow-400", bg: "bg-yellow-900/40", icon: AlertTriangle },
  ALERT:          { color: "text-blue-400",  bg: "bg-blue-900/40",   icon: AlertTriangle },
  ALLOW:          { color: "text-green-400", bg: "bg-green-900/40", icon: CheckCircle },
};

export default function Policies() {
  const [policies, setPolicies]   = useState<any[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]           = useState<string | null>(null);
  const [showModal, setShowModal]   = useState(false);
  const [form, setForm]             = useState({ name: "", description: "", action: "ALERT", priority: 50, applies_to_all_workflows: true });
  const [conditions, setConditions] = useState<any[]>([{ field: "severity", operator: "equals", value: "medium" }]);
  const [saving, setSaving]         = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPolicies();
      setPolicies(data);
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to load policies");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await createPolicy({ ...form, conditions: { all: conditions } });
      setShowModal(false);
      setForm({ name: "", description: "", action: "ALERT", priority: 50, applies_to_all_workflows: true });
      setConditions([{ field: "severity", operator: "equals", value: "medium" }]);
      load();
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to create policy");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this policy?")) return;
    try {
      await deletePolicy(id);
      load();
    } catch (e: any) {
      alert(e.response?.data?.detail ?? "Failed to delete");
    }
  };

  const updateCondition = (idx: number, field: string, value: any) => {
    const updated = [...conditions];
    (updated[idx] as any)[field] = value;
    setConditions(updated);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Policies</h1>
          <p className="text-gray-400 text-sm mt-1">Governance rules that act on security findings</p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> New Policy
        </button>
      </div>

      {/* Policy stats */}
      <div className="grid grid-cols-4 gap-4">
        {["BLOCK", "REQUIRE_REVIEW", "ALERT", "ALLOW"].map((action) => {
          const count = policies.filter((p: any) => p.action === action).length;
          const cfg = ACTION_CONFIG[action] ?? { color: "text-gray-400", bg: "bg-gray-800" };
          const Icon = cfg.icon ?? Shield;
          return (
            <div key={action} className="card flex items-center gap-3">
              <div className={`p-2 rounded-lg ${cfg.bg}`}><Icon className={`w-4 h-4 ${cfg.color}`} /></div>
              <div>
                <p className="text-lg font-bold text-white">{count}</p>
                <p className={`text-xs ${cfg.color}`}>{action.replace("_", " ")}</p>
              </div>
            </div>
          );
        })}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 text-blue-400 animate-spin" /></div>
      ) : error ? (
        <div className="card p-4 border-red-800 bg-red-900/20"><p className="text-red-300 text-sm">{error}</p></div>
      ) : policies.length === 0 ? (
        <div className="card py-12 text-center">
          <Shield className="w-10 h-10 text-gray-700 mx-auto mb-3" />
          <p className="text-gray-400">No policies yet</p>
          <p className="text-gray-600 text-xs mt-1">Create a policy to govern security findings</p>
        </div>
      ) : (
        <div className="space-y-3">
          {policies.map((p: any) => {
            const cfg = ACTION_CONFIG[p.action] ?? { color: "text-gray-400", bg: "bg-gray-800" };
            const Icon = cfg.icon ?? Shield;
            const isEnabled = p.enabled;
            return (
              <div key={p.id} className={`card ${isEnabled ? "border-gray-700" : "border-gray-800 opacity-60"}`}>
                <div className="flex items-start gap-4">
                  <div className={`p-2 rounded-lg ${cfg.bg} mt-0.5`}>
                    <Icon className={`w-4 h-4 ${cfg.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-bold ${isEnabled ? cfg.color : "text-gray-500"}`}>{p.action.replace("_", " ")}</span>
                      <span className="text-xs text-gray-600">·</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${isEnabled ? "bg-green-900/40 text-green-400" : "bg-gray-800 text-gray-500"}`}>
                        {isEnabled ? "Active" : "Disabled"}
                      </span>
                      <span className="text-xs text-gray-600">·</span>
                      <span className="text-xs text-gray-500">Priority {p.priority}</span>
                    </div>
                    <p className="text-sm font-medium text-white">{p.name}</p>
                    {p.description && <p className="text-xs text-gray-500 mt-1">{p.description}</p>}
                    <div className="mt-2 flex flex-wrap gap-1">
                      {(p.conditions?.all ?? []).map((c: any, i: number) => (
                        <span key={i} className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded font-mono">
                          {c.field} {c.operator} {JSON.stringify(c.value)}
                        </span>
                      ))}
                      {(p.conditions?.any ?? []).map((c: any, i: number) => (
                        <span key={i} className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded font-mono">
                          any: {c.field} {c.operator} {JSON.stringify(c.value)}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-xs text-gray-600">{p.applies_to_all_workflows ? "All workflows" : `${(p.workflow_ids ?? []).length} workflows`}</span>
                    <button onClick={() => handleDelete(p.id)} className="p-1.5 rounded hover:bg-red-900/40 text-gray-600 hover:text-red-400 transition-colors">
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <ChevronRight className="w-4 h-4 text-gray-600" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4" onClick={() => setShowModal(false)}>
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-lg p-6" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-white mb-4">Create Policy</h2>
            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Name</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Block Critical Findings" className="input" required />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Description</label>
                <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="What does this policy do?" className="input" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Action</label>
                  <select value={form.action} onChange={(e) => setForm({ ...form, action: e.target.value })} className="input">
                    <option value="ALLOW">Allow</option>
                    <option value="ALERT">Alert</option>
                    <option value="REQUIRE_REVIEW">Require Review</option>
                    <option value="BLOCK">Block</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Priority (1-100, higher first)</label>
                  <input type="number" min="1" max="100" value={form.priority} onChange={(e) => setForm({ ...form, priority: parseInt(e.target.value) })} className="input" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Conditions (all must match)</label>
                <div className="space-y-2">
                  {conditions.map((cond, idx) => (
                    <div key={idx} className="flex gap-2">
                      <select value={cond.field} onChange={(e) => updateCondition(idx, "field", e.target.value)} className="input flex-1">
                        <option value="severity">Severity</option>
                        <option value="risk_score">Risk Score</option>
                        <option value="detector_id">Detector ID</option>
                      </select>
                      <select value={cond.operator} onChange={(e) => updateCondition(idx, "operator", e.target.value)} className="input flex-1">
                        <option value="equals">equals</option>
                        <option value="gte">≥</option>
                        <option value="lte">≤</option>
                        <option value="in">in</option>
                      </select>
                      <input value={typeof cond.value === "object" ? JSON.stringify(cond.value) : cond.value}
                        onChange={(e) => updateCondition(idx, "value", cond.operator === "in" ? JSON.parse(e.target.value) : e.target.value)}
                        placeholder="value" className="input flex-1 font-mono text-xs" />
                      <button type="button" onClick={() => setConditions(conditions.filter((_, i) => i !== idx))}
                        className="text-gray-500 hover:text-red-400 px-2">✕</button>
                    </div>
                  ))}
                </div>
                <button type="button" onClick={() => setConditions([...conditions, { field: "severity", operator: "equals", value: "medium" }])}
                  className="text-xs text-blue-400 mt-2 hover:text-blue-300">+ Add condition</button>
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
                <input type="checkbox" checked={form.applies_to_all_workflows}
                  onChange={(e) => setForm({ ...form, applies_to_all_workflows: e.target.checked })} className="accent-blue-600" />
                Apply to all workflows
              </label>
              {error && <div className="bg-red-900/40 border border-red-700 rounded-lg px-4 py-3"><p className="text-red-300 text-sm">{error}</p></div>}
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" disabled={saving} className="btn-primary flex-1">{saving ? "Saving..." : "Create"}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
