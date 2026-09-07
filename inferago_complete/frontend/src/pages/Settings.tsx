import { useState } from "react";
import { Settings, User, Bell, Key, Globe, CheckCircle } from "lucide-react";

export default function SettingsPage() {
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 text-sm mt-1">Manage your account and preferences</p>
      </div>

      {/* Webhook URLs */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-4">
          <Globe className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-bold text-white">Webhook Endpoints</h2>
        </div>
        <div className="space-y-3">
          {[
            { platform: "n8n",    url: "/api/webhook/n8n" },
            { platform: "Make",   url: "/api/webhook/make" },
            { platform: "Zapier", url: "/api/webhook/zapier" },
            { platform: "Custom", url: "/api/webhook/custom" },
          ].map(({ platform, url }) => (
            <div key={platform} className="flex items-center gap-4">
              <span className="text-sm font-medium text-gray-400 w-20">{platform}</span>
              <code className="flex-1 bg-gray-950 border border-gray-800 rounded px-3 py-2 text-xs text-gray-300 font-mono">
                {window.location.origin}{url}
              </code>
              <button
                onClick={() => navigator.clipboard.writeText(window.location.origin + url)}
                className="text-xs text-blue-400 hover:text-blue-300 whitespace-nowrap">
                Copy
              </button>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-600 mt-4">
          Use the <strong>X-API-Key</strong> header with your ARI API key to authenticate webhook requests.
        </p>
      </div>

      {/* Notifications */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-4">
          <Bell className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-bold text-white">Notifications</h2>
        </div>
        <form onSubmit={handleSave} className="space-y-3">
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-sm text-gray-300">Critical findings detected</span>
            <input type="checkbox" defaultChecked className="accent-blue-600 w-4 h-4" />
          </label>
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-sm text-gray-300">Workflow blocked by policy</span>
            <input type="checkbox" defaultChecked className="accent-blue-600 w-4 h-4" />
          </label>
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-sm text-gray-300">Review required for high-risk findings</span>
            <input type="checkbox" defaultChecked className="accent-blue-600 w-4 h-4" />
          </label>
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-sm text-gray-300">Daily cost summary</span>
            <input type="checkbox" className="accent-blue-600 w-4 h-4" />
          </label>
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-sm text-gray-300">Workflow inactivity alerts</span>
            <input type="checkbox" defaultChecked className="accent-blue-600 w-4 h-4" />
          </label>
          <div className="pt-3">
            <button type="submit" className="btn-primary">
              {saved ? <><CheckCircle className="w-4 h-4 inline mr-1" /> Saved</> : "Save Preferences"}
            </button>
          </div>
        </form>
      </div>

      {/* Threshold settings */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-4">
          <Settings className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-bold text-white">Alert Thresholds</h2>
        </div>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Cost spike threshold (%)</label>
            <input type="number" defaultValue={200} min="100" max="1000" className="input max-w-32" />
            <p className="text-xs text-gray-600 mt-1">Alert when a run costs this % above the 30-run average</p>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Token spike threshold (%)</label>
            <input type="number" defaultValue={200} min="100" max="1000" className="input max-w-32" />
            <p className="text-xs text-gray-600 mt-1">Alert when a run uses this % more tokens than average</p>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Error rate alert threshold (%)</label>
            <input type="number" defaultValue={25} min="0" max="100" className="input max-w-32" />
            <p className="text-xs text-gray-600 mt-1">Alert when the last 30 runs have this % failure rate</p>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Inactivity alert after (hours)</label>
            <input type="number" defaultValue={72} min="1" max="720" className="input max-w-32" />
            <p className="text-xs text-gray-600 mt-1">Alert if a workflow hasn't run for this long</p>
          </div>
          <button type="submit" className="btn-primary">
            {saved ? <><CheckCircle className="w-4 h-4 inline mr-1" /> Saved</> : "Save Thresholds"}
          </button>
        </form>
      </div>

      {/* Profile */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-4">
          <User className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-bold text-white">Profile</h2>
        </div>
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Name</label>
              <input type="text" placeholder="Your name" className="input" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Email</label>
              <input type="email" placeholder="you@example.com" className="input" />
            </div>
          </div>
          <button type="submit" className="btn-primary">
            {saved ? <><CheckCircle className="w-4 h-4 inline mr-1" /> Saved</> : "Update Profile"}
          </button>
        </form>
      </div>

      {/* API Keys */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-4">
          <Key className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-bold text-white">API Keys</h2>
        </div>
        <p className="text-sm text-gray-400 mb-3">Manage your API keys in the <a href="/api-keys" className="text-blue-400 hover:text-blue-300">API Keys page</a>.</p>
      </div>
    </div>
  );
}
