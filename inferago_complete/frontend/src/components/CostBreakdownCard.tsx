import { useCostBreakdown } from "../hooks/useRuns";
import { Loader2, TrendingUp } from "lucide-react";

export default function CostBreakdownCard({ workflowId }: { workflowId: string }) {
  const { data, isLoading } = useCostBreakdown(workflowId);

  if (isLoading) {
    return (
      <div className="card flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
      </div>
    );
  }

  if (!data || !data.avg_cost_per_run) {
    return (
      <div className="card flex items-center justify-center py-8 text-gray-600 text-sm">
        No cost data yet
      </div>
    );
  }

  const rows = [
    { label: "Per run",           value: `$${data.avg_cost_per_run.toFixed(6)}` },
    { label: "Per day",           value: `$${data.per_day.toFixed(4)}` },
    { label: "Per week",          value: `$${data.per_week.toFixed(4)}` },
    { label: "Per month",         value: `$${data.per_month.toFixed(4)}` },
    { label: "Projected monthly", value: `$${data.projected_monthly.toFixed(4)}`, highlight: true },
  ];

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="w-4 h-4 text-green-400" />
        <h2 className="text-sm font-semibold text-gray-400">Cost Breakdown</h2>
      </div>

      <div className="space-y-2">
        {rows.map((row) => (
          <div
            key={row.label}
            className={`flex items-center justify-between px-3 py-2 rounded-lg ${
              row.highlight
                ? "bg-green-900/20 border border-green-800/50"
                : "bg-gray-800/40"
            }`}
          >
            <span className={`text-sm ${row.highlight ? "text-green-400 font-medium" : "text-gray-400"}`}>
              {row.label}
            </span>
            <span className={`text-sm font-bold ${row.highlight ? "text-green-300" : "text-white"}`}>
              {row.value}
            </span>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-600 mt-3">
        Based on {data.total_runs_analyzed} runs ·{" "}
        ~{data.runs_per_day_estimate.toFixed(1)} runs/day estimated
      </p>
    </div>
  );
}
