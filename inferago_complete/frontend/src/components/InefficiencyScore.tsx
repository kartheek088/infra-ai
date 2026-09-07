import { useInefficiencyScore } from "../hooks/useExecutions";
import { Loader2, AlertTriangle, CheckCircle } from "lucide-react";

export default function InefficiencyScore({ workflowId }: { workflowId: string }) {
  const { data, isLoading } = useInefficiencyScore(workflowId);

  if (isLoading) {
    return (
      <div className="card flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
      </div>
    );
  }

  if (!data) return null;

  const score = data.inefficiency_score ?? 0;
  const color =
    score < 20 ? "text-green-400"
    : score < 50 ? "text-yellow-400"
    : score < 75 ? "text-orange-400"
    : "text-red-400";

  const barColor =
    score < 20 ? "bg-green-500"
    : score < 50 ? "bg-yellow-500"
    : score < 75 ? "bg-orange-500"
    : "bg-red-500";

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-400">Inefficiency Score</h2>
        <span className="text-xs text-gray-500">lower is better</span>
      </div>

      {/* Score display */}
      <div className="flex items-end gap-3 mb-3">
        <span className={`text-5xl font-bold ${color}`}>{score}</span>
        <div className="pb-1">
          <span className={`text-lg font-semibold ${color}`}>/100</span>
          <p className="text-xs text-gray-500">{data.grade}</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-gray-800 rounded-full mb-4">
        <div
          className={`h-2 rounded-full transition-all ${barColor}`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>

      {/* Flags */}
      {data.flags?.length > 0 ? (
        <div className="space-y-1.5">
          {data.flags.map((flag: string, i: number) => (
            <div key={i} className="flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-gray-400">{flag}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-2 text-green-400">
          <CheckCircle className="w-4 h-4" />
          <p className="text-xs">No inefficiency flags detected</p>
        </div>
      )}
    </div>
  );
}
