import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

interface CostPoint { date: string; cost: number; status: string; platform: string; }

export default function CostTrendChart({ data }: { data: CostPoint[] }) {
  const formatted = data.map((d) => ({
    ...d,
    date: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    cost: Number(d.cost.toFixed(6)),
  }));

  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-gray-400 mb-4">Cost per Run (USD)</h2>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={formatted}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 11 }} />
          <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ backgroundColor: "#111827", border: "1px solid #374151", borderRadius: 8 }}
            labelStyle={{ color: "#9ca3af" }}
            itemStyle={{ color: "#60a5fa" }}
          />
          <Line type="monotone" dataKey="cost" stroke="#3b82f6" strokeWidth={2} dot={{ fill: "#3b82f6", r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
