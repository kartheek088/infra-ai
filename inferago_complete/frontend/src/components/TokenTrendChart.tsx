import { useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { useTokenTrend } from "../hooks/useRuns";
import { Loader2 } from "lucide-react";

const DAYS_OPTIONS = [
  { label: "7d",  value: 7  },
  { label: "30d", value: 30 },
  { label: "90d", value: 90 },
];

export default function TokenTrendChart({ workflowId }: { workflowId: string }) {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useTokenTrend(workflowId, days);

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-400">Token Usage Trend</h2>
        <div className="flex gap-1">
          {DAYS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setDays(opt.value)}
              className={`px-3 py-1 text-xs rounded-lg font-medium transition-colors ${
                days === opt.value
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary stats */}
      {data?.summary && (
        <div className="grid grid-cols-3 gap-3 mb-4">
          <MiniStat
            label="Total tokens"
            value={data.summary.total_tokens.toLocaleString()}
          />
          <MiniStat
            label="Peak day"
            value={data.summary.peak_tokens_day.toLocaleString()}
          />
          <MiniStat
            label="Total cost"
            value={`$${data.summary.total_cost_usd.toFixed(4)}`}
          />
        </div>
      )}

      {/* Chart */}
      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
        </div>
      ) : !data?.data?.length ? (
        <div className="flex items-center justify-center h-40 text-gray-600 text-sm">
          No data for this period
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data.data}>
            <defs>
              <linearGradient id="promptGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}   />
              </linearGradient>
              <linearGradient id="completionGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#8b5cf6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}   />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis
              dataKey="date"
              tick={{ fill: "#6b7280", fontSize: 10 }}
              tickFormatter={(v) => v.slice(5)}
            />
            <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#111827",
                border: "1px solid #374151",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ color: "#9ca3af" }}
            />
            <Legend
              wrapperStyle={{ fontSize: 11, color: "#9ca3af" }}
            />
            <Area
              type="monotone"
              dataKey="prompt_tokens"
              name="Prompt"
              stroke="#3b82f6"
              fill="url(#promptGrad)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="completion_tokens"
              name="Completion"
              stroke="#8b5cf6"
              fill="url(#completionGrad)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800/60 rounded-lg px-3 py-2">
      <p className="text-xs text-gray-500 mb-0.5">{label}</p>
      <p className="text-sm font-bold text-white">{value}</p>
    </div>
  );
}
