interface HealthScore {
  score: number;
  grade: string;
  message: string;
  breakdown: {
    cost_efficiency: number;
    rag_quality: number;
    reliability: number;
    performance: number;
  };
}

export default function HealthScoreGauge({ health }: { health: HealthScore }) {
  const color = health.score >= 85 ? "text-green-400" : health.score >= 70 ? "text-blue-400" : health.score >= 50 ? "text-yellow-400" : "text-red-400";
  const ring  = health.score >= 85 ? "ring-green-500/30" : health.score >= 70 ? "ring-blue-500/30" : health.score >= 50 ? "ring-yellow-500/30" : "ring-red-500/30";

  return (
    <div className={`card ring-1 ${ring}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-400">Health Score</span>
        <span className={`text-2xl font-bold ${color}`}>{health.grade}</span>
      </div>
      <div className={`text-5xl font-bold ${color} mb-2`}>{health.score}</div>
      <p className="text-xs text-gray-500 mb-4">{health.message}</p>

      {health.breakdown && (
        <div className="space-y-2">
          {Object.entries(health.breakdown).map(([key, val]) => (
            <div key={key}>
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>{key.replace("_", " ")}</span>
                <span>{val}</span>
              </div>
              <div className="h-1.5 bg-gray-800 rounded-full">
                <div className="h-1.5 bg-blue-500 rounded-full transition-all" style={{ width: `${val}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
