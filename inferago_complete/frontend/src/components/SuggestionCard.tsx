interface Suggestion {
  type: string;
  impact: "high" | "medium" | "low";
  title: string;
  description: string;
  estimated_saving: string;
  action: string;
}

export default function SuggestionCard({ suggestion }: { suggestion: Suggestion }) {
  const colors = {
    high:   "border-red-500 bg-red-900/10",
    medium: "border-yellow-500 bg-yellow-900/10",
    low:    "border-blue-500 bg-blue-900/10",
  };
  const badges = {
    high:   "badge-high",
    medium: "badge-medium",
    low:    "badge-low",
  };

  return (
    <div className={`border-l-4 p-4 rounded-lg ${colors[suggestion.impact]}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className={badges[suggestion.impact]}>{suggestion.impact}</span>
          <h3 className="font-semibold text-white text-sm">{suggestion.title}</h3>
        </div>
        <span className="text-green-400 font-bold text-sm whitespace-nowrap">{suggestion.estimated_saving}</span>
      </div>
      <p className="text-gray-400 text-sm mt-2">{suggestion.description}</p>
      <p className="text-blue-400 text-xs mt-2">💡 {suggestion.action}</p>
    </div>
  );
}
