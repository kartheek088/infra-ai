import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRuns } from "../hooks/useRuns";
import { Loader2, ChevronRight, Filter } from "lucide-react";
import PlatformBadge from "./PlatformBadge";

const STATUS_OPTIONS = ["", "success", "failed", "running"];
const PLATFORM_OPTIONS = ["", "n8n", "make", "zapier", "custom"];

export default function RunHistoryTable({ workflowId }: { workflowId: string }) {
  const navigate = useNavigate();
  const [status, setStatus]     = useState("");
  const [platform, setPlatform] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const { data: runs, isLoading } = useRuns(workflowId, {
    status:   status   || undefined,
    platform: platform || undefined,
    limit:    50,
  });

  const statusColor: Record<string, string> = {
    success: "text-green-400 bg-green-900/30",
    failed:  "text-red-400 bg-red-900/30",
    running: "text-yellow-400 bg-yellow-900/30",
    unknown: "text-gray-400 bg-gray-800",
  };

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">Run History</h2>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg transition-colors ${
            showFilters ? "bg-blue-600/20 text-blue-400" : "btn-secondary"
          }`}
        >
          <Filter className="w-3.5 h-3.5" />
          Filters {(status || platform) ? "●" : ""}
        </button>
      </div>

      {/* Filter row */}
      {showFilters && (
        <div className="flex gap-3 mb-4 p-3 bg-gray-800/50 rounded-lg">
          <div className="flex-1">
            <label className="block text-xs text-gray-500 mb-1">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-300"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>{s || "All statuses"}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-xs text-gray-500 mb-1">Platform</label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-300"
            >
              {PLATFORM_OPTIONS.map((p) => (
                <option key={p} value={p}>{p || "All platforms"}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => { setStatus(""); setPlatform(""); }}
              className="text-xs text-gray-500 hover:text-gray-300 pb-1.5"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-10">
          <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
        </div>
      ) : !runs?.length ? (
        <div className="text-center py-10 text-gray-600 text-sm">
          No runs found {status || platform ? "for this filter" : "yet"}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-gray-800">
                <th className="text-left py-2 pr-4 font-medium">Status</th>
                <th className="text-left py-2 pr-4 font-medium">Platform</th>
                <th className="text-left py-2 pr-4 font-medium">Triggered by</th>
                <th className="text-right py-2 pr-4 font-medium">Duration</th>
                <th className="text-left py-2 font-medium">Time</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {runs.map((run) => (
                <tr
                  key={run.id}
                  onClick={() => navigate(`/runs/${run.id}`)}
                  className="hover:bg-gray-800/40 cursor-pointer transition-colors group"
                >
                  <td className="py-3 pr-4">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      statusColor[run.status] ?? statusColor.unknown
                    }`}>
                      {run.status}
                    </span>
                  </td>
                  <td className="py-3 pr-4">
                    <PlatformBadge platform={run.platform} />
                  </td>
                  <td className="py-3 pr-4 text-gray-400">
                    {run.triggered_by ?? "—"}
                  </td>
                  <td className="py-3 pr-4 text-right text-gray-400 tabular-nums">
                    {run.duration_ms ? `${(run.duration_ms / 1000).toFixed(1)}s` : "—"}
                  </td>
                  <td className="py-3 text-gray-500 text-xs">
                    {run.created_at
                      ? new Date(run.created_at).toLocaleString()
                      : "—"}
                  </td>
                  <td className="py-3 pl-2">
                    <ChevronRight className="w-4 h-4 text-gray-700 group-hover:text-gray-400 transition-colors" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
