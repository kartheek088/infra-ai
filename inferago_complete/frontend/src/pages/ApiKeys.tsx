import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { generateKey, listKeys, revokeKey } from "../api/apiKeys";
import { Key, Plus, Copy, Trash2, CheckCircle } from "lucide-react";

export default function ApiKeys() {
  const qc                         = useQueryClient();
  const { data: keys, isLoading }  = useQuery({ queryKey: ["api-keys"], queryFn: listKeys });
  const [showForm, setShowForm]     = useState(false);
  const [keyName, setKeyName]       = useState("");
  const [newKey, setNewKey]         = useState<string | null>(null);
  const [copied, setCopied]         = useState(false);

  const generateMutation = useMutation({
    mutationFn: () => generateKey(keyName),
    onSuccess: (data) => {
      setNewKey(data.key);
      setKeyName("");
      setShowForm(false);
      qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: revokeKey,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });

  const copyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">API Keys</h1>
          <p className="text-gray-400 text-sm mt-1">Keys are used to authenticate your platform webhooks</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> Generate Key
        </button>
      </div>

      {/* Webhook URL guide */}
      <div className="card bg-blue-900/10 border-blue-800">
        <h2 className="text-sm font-semibold text-blue-400 mb-3">Webhook URLs</h2>
        <div className="space-y-2">
          {["n8n", "make", "zapier", "custom"].map((p) => (
            <div key={p} className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-16">{p}:</span>
              <code className="text-xs text-blue-300 bg-gray-900 px-2 py-1 rounded">
                /api/webhook/{p}?api_key=YOUR_KEY
              </code>
            </div>
          ))}
        </div>
      </div>

      {/* New key display — show once */}
      {newKey && (
        <div className="card bg-green-900/10 border-green-800">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span className="text-green-400 font-semibold text-sm">Key generated — copy it now, it won't be shown again</span>
          </div>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-xs bg-gray-900 px-3 py-2 rounded font-mono text-green-300 break-all">{newKey}</code>
            <button onClick={() => copyKey(newKey)} className="btn-secondary text-xs py-2 flex items-center gap-1">
              {copied ? <CheckCircle className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
          <button onClick={() => setNewKey(null)} className="text-xs text-gray-500 mt-3 hover:text-gray-400">Dismiss</button>
        </div>
      )}

      {/* Keys list */}
      <div className="card">
        {isLoading ? (
          <div className="space-y-3">{[1,2].map((i) => <div key={i} className="h-14 bg-gray-800 rounded-lg animate-pulse" />)}</div>
        ) : !keys?.length ? (
          <div className="text-center py-10">
            <Key className="w-10 h-10 text-gray-700 mx-auto mb-3" />
            <p className="text-gray-400">No API keys yet</p>
            <p className="text-gray-600 text-sm mt-1">Generate a key to connect your automation platforms</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {keys.map((key: any) => (
              <div key={key.id} className="flex items-center justify-between py-4">
                <div className="flex items-center gap-3">
                  <Key className="w-4 h-4 text-blue-400" />
                  <div>
                    <p className="text-sm font-medium text-white">{key.name}</p>
                    <p className="text-xs text-gray-500 font-mono">{key.key_preview}</p>
                    {key.last_used_at && <p className="text-xs text-gray-600">Last used: {new Date(key.last_used_at).toLocaleDateString()}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${key.is_active ? "bg-green-900/40 text-green-400" : "bg-gray-800 text-gray-500"}`}>
                    {key.is_active ? "active" : "revoked"}
                  </span>
                  {key.is_active && (
                    <button onClick={() => { if (confirm("Revoke this key?")) revokeMutation.mutate(key.id); }}
                      className="p-1.5 rounded hover:bg-red-900/40 text-gray-600 hover:text-red-400 transition-colors">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Generate modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold text-white mb-4">Generate API Key</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Key name</label>
                <input value={keyName} onChange={(e) => setKeyName(e.target.value)} placeholder="e.g. Production, Client ABC" className="input" />
              </div>
              <div className="flex gap-3">
                <button onClick={() => setShowForm(false)} className="btn-secondary flex-1">Cancel</button>
                <button onClick={() => generateMutation.mutate()} disabled={!keyName || generateMutation.isPending} className="btn-primary flex-1">
                  {generateMutation.isPending ? "Generating..." : "Generate"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
