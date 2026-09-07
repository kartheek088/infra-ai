import { useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardCheck, AlertTriangle, ArrowUpRight, CheckCircle, XCircle, ArrowUpCircle, Clock, ChevronRight, Loader2 } from "lucide-react";
import { useReviews, useReviewStats, useDecideReview } from "../hooks/useReviews";
import type { Review } from "../api/review";

// ── Config ────────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof CheckCircle }> = {
  pending:    { label: "Pending",    color: "bg-yellow-900/30 text-yellow-400 border-yellow-700/50", icon: Clock },
  in_review:  { label: "In Review",  color: "bg-blue-900/30 text-blue-400 border-blue-700/50",    icon: ClipboardCheck },
  approved:  { label: "Approved",   color: "bg-green-900/30 text-green-400 border-green-700/50",  icon: CheckCircle },
  blocked:   { label: "Blocked",    color: "bg-red-900/30 text-red-400 border-red-700/50",       icon: XCircle },
  escalated: { label: "Escalated",  color: "bg-orange-900/30 text-orange-400 border-orange-700/50", icon: ArrowUpCircle },
  completed: { label: "Completed",  color: "bg-gray-800 text-gray-400 border-gray-700",            icon: CheckCircle },
};

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "text-red-400",
  HIGH:     "text-orange-400",
  MEDIUM:   "text-yellow-400",
  LOW:      "text-blue-400",
  INFO:     "text-gray-400",
};

const RISK_COLOR = (score: number) =>
  score >= 80 ? "text-red-400" : score >= 50 ? "text-orange-400" : score >= 25 ? "text-yellow-400" : "text-green-400";

const DECISION_COLOR: Record<string, string> = {
  REQUIRE_REVIEW: "text-yellow-400",
  BLOCK:          "text-red-400",
  ALERT:          "text-orange-400",
  ALLOW:          "text-green-400",
};

// ── Review Drawer ────────────────────────────────────────────────────────────

function ReviewDrawer({ review, onClose, onDecide }: {
  review: Review;
  onClose: () => void;
  onDecide: (status: "approved" | "blocked" | "escalated", note: string) => void;
}) {
  const [note, setNote] = useState("");
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const cfg = STATUS_CONFIG[review.status] ?? STATUS_CONFIG.pending;
  const StatusIcon = cfg.icon;
  const isActionable = review.status === "pending" || review.status === "in_review";

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative w-[520px] h-full bg-gray-900 border-l border-gray-700 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <StatusIcon className="w-5 h-5 text-blue-400" />
            <h2 className="text-white font-semibold">Review Details</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl leading-none">&times;</button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

          {/* Status badge */}
          <div className="flex items-center gap-3">
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${cfg.color}`}>
              <StatusIcon className="w-3 h-3" />
              {cfg.label}
            </span>
            {review.decision && (
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${DECISION_COLOR[review.decision] ?? "text-gray-400"} bg-gray-800 border border-gray-700`}>
                {review.decision}
              </span>
            )}
          </div>

          {/* Execution link */}
          <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">Execution</p>
            <Link to={`/executions/${review.run_id}`} className="text-blue-400 hover:text-blue-300 text-sm font-mono flex items-center gap-1">
              {review.run_id.slice(0, 8)}… <ArrowUpRight className="w-3 h-3" />
            </Link>
          </div>

          {/* Workflow */}
          <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">Workflow</p>
            <p className="text-gray-300 text-sm">{review.workflow_id}</p>
          </div>

          {/* Risk & Findings summary */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">Risk Score</p>
              <p className={`text-2xl font-bold ${RISK_COLOR(review.max_risk_score)}`}>
                {review.max_risk_score}
              </p>
            </div>
            <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">Findings</p>
              <p className="text-2xl font-bold text-white">{review.finding_count}</p>
            </div>
          </div>

          {/* Top severity */}
          {review.top_finding_severity && (
            <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">Top Severity</p>
              <p className={`text-sm font-semibold ${SEVERITY_COLORS[review.top_finding_severity] ?? "text-gray-300"}`}>
                {review.top_finding_severity}
              </p>
            </div>
          )}

          {/* Governing Policy */}
          {review.governing_policy_name && (
            <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">Governing Policy</p>
              <p className="text-gray-300 text-sm">{review.governing_policy_name}</p>
            </div>
          )}

          {/* Decision meta */}
          {review.decision_by && (
            <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">Decision By</p>
              <p className="text-gray-300 text-sm">{review.decision_by.slice(0, 8)}… {review.decision_at && `on ${new Date(review.decision_at).toLocaleString()}`}</p>
              {review.decision_note && <p className="text-gray-400 text-xs mt-2 italic">{review.decision_note}</p>}
            </div>
          )}

          {/* Created */}
          <div className="text-xs text-gray-500">
            Submitted {new Date(review.created_at).toLocaleString()}
          </div>
        </div>

        {/* Action bar */}
        {isActionable && (
          <div className="border-t border-gray-700 px-6 py-4 space-y-3">
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add a note (optional)..."
              rows={2}
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500"
            />
            <div className="flex gap-2">
              <button
                onClick={() => { setPendingAction("approved"); onDecide("approved", note); setPendingAction(null); }}
                disabled={!!pendingAction}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white text-sm font-medium transition-colors"
              >
                {pendingAction === "approved" ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                Approve
              </button>
              <button
                onClick={() => { setPendingAction("escalated"); onDecide("escalated", note); setPendingAction(null); }}
                disabled={!!pendingAction}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-orange-700 hover:bg-orange-600 disabled:opacity-50 text-white text-sm font-medium transition-colors"
              >
                {pendingAction === "escalated" ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowUpCircle className="w-4 h-4" />}
                Escalate
              </button>
              <button
                onClick={() => { setPendingAction("blocked"); onDecide("blocked", note); setPendingAction(null); }}
                disabled={!!pendingAction}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-red-700 hover:bg-red-600 disabled:opacity-50 text-white text-sm font-medium transition-colors"
              >
                {pendingAction === "blocked" ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                Block
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Stats Bar ────────────────────────────────────────────────────────────────

function StatsBar({ stats }: { stats: { total: number; pending: number; in_review: number; approved: number; blocked: number; escalated: number; avg_risk_score: number } }) {
  const items = [
    { label: "Total",     value: stats.total,     color: "text-white" },
    { label: "Pending",   value: stats.pending,   color: "text-yellow-400" },
    { label: "In Review", value: stats.in_review,  color: "text-blue-400" },
    { label: "Approved",  value: stats.approved,   color: "text-green-400" },
    { label: "Blocked",   value: stats.blocked,   color: "text-red-400" },
    { label: "Escalated", value: stats.escalated,  color: "text-orange-400" },
    { label: "Avg Risk",  value: stats.avg_risk_score, color: "text-gray-400", suffix: "/100" },
  ];

  return (
    <div className="grid grid-cols-7 gap-3 mb-6">
      {items.map(({ label, value, color, suffix }) => (
        <div key={label} className="bg-gray-800/60 border border-gray-700 rounded-lg px-4 py-3">
          <p className={`text-2xl font-bold ${color}`}>{value}{suffix ?? ""}</p>
          <p className="text-xs text-gray-500 mt-0.5">{label}</p>
        </div>
      ))}
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

const STATUS_FILTERS = ["all", "pending", "in_review", "approved", "blocked", "escalated"] as const;

export default function ReviewQueue() {
  const [filter, setFilter] = useState<string>("all");
  const [selected, setSelected] = useState<Review | null>(null);
  const { data: stats }   = useReviewStats();
  const { data: reviews, isLoading } = useReviews(
    filter !== "all" ? { status: filter, limit: 200 } : { limit: 200 }
  );
  const decide = useDecideReview();

  const handleDecide = (status: "approved" | "blocked" | "escalated", note: string) => {
    if (!selected) return;
    decide.mutate(
      { id: selected.id, payload: { status, decision_note: note || undefined } },
      {
        onSuccess: (updated) => {
          setSelected(updated);
        },
      }
    );
  };

  return (
    <div className="p-8 min-h-screen">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <ClipboardCheck className="w-7 h-7 text-blue-400" />
        <h1 className="text-2xl font-bold text-white">Review Queue</h1>
      </div>

      {/* Stats */}
      {stats && <StatsBar stats={stats} />}

      {/* Filter pills */}
      <div className="flex gap-2 mb-4">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
              filter === f
                ? "bg-blue-600/30 text-blue-400 border-blue-600/50"
                : "bg-gray-800 text-gray-400 border-gray-700 hover:border-gray-600"
            }`}
          >
            {f === "all" ? "All" : f === "in_review" ? "In Review" : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              {["Status", "Execution", "Workflow", "Risk", "Findings", "Severity", "Policy", "Created"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                  <Loader2 className="w-5 h-5 animate-spin inline" /> Loading...
                </td>
              </tr>
            ) : !reviews?.length ? (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                  No reviews found
                </td>
              </tr>
            ) : (
              reviews.map((r) => {
                const cfg = STATUS_CONFIG[r.status] ?? STATUS_CONFIG.pending;
                const StatusIcon = cfg.icon;
                return (
                  <tr
                    key={r.id}
                    onClick={() => setSelected(r)}
                    className="border-b border-gray-800/50 hover:bg-gray-800/50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border ${cfg.color}`}>
                        <StatusIcon className="w-3 h-3" />
                        {cfg.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-blue-400">
                      {r.run_id.slice(0, 8)}… <ChevronRight className="w-3 h-3 inline" />
                    </td>
                    <td className="px-4 py-3 text-gray-400 font-mono text-xs">
                      {r.workflow_id.slice(0, 8)}…
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-bold ${RISK_COLOR(r.max_risk_score)}`}>{r.max_risk_score}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-300">{r.finding_count}</td>
                    <td className="px-4 py-3">
                      {r.top_finding_severity ? (
                        <span className={`font-medium ${SEVERITY_COLORS[r.top_finding_severity] ?? "text-gray-300"}`}>
                          {r.top_finding_severity}
                        </span>
                      ) : (
                        <span className="text-gray-600">N/A</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs max-w-[160px] truncate">
                      {r.governing_policy_name ?? <span className="text-gray-600">N/A</span>}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {new Date(r.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Drawer */}
      {selected && (
        <ReviewDrawer
          review={selected}
          onClose={() => setSelected(null)}
          onDecide={handleDecide}
        />
      )}
    </div>
  );
}
