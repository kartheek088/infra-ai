import api from "./client";

export interface Review {
  id: string;
  tenant_id: string;
  run_id: string;
  workflow_id: string;
  user_id: string;
  status: "pending" | "in_review" | "approved" | "blocked" | "escalated" | "completed";
  decision: string | null;
  max_risk_score: number;
  finding_count: number;
  top_finding_severity: string | null;
  governing_policy_id: string | null;
  governing_policy_name: string | null;
  decision_by: string | null;
  decision_at: string | null;
  decision_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewQueueStats {
  total: number;
  pending: number;
  in_review: number;
  approved: number;
  blocked: number;
  escalated: number;
  avg_risk_score: number;
}

export const getReviews = (params?: {
  status?: string;
  workflow_id?: string;
  min_risk?: number;
  limit?: number;
}): Promise<Review[]> =>
  api.get("/api/reviews", { params }).then((r) => r.data);

export const getReview = (id: string): Promise<Review> =>
  api.get(`/api/reviews/${id}`).then((r) => r.data);

export const getReviewStats = (): Promise<ReviewQueueStats> =>
  api.get("/api/reviews/stats").then((r) => r.data);

export const decideReview = (
  id: string,
  payload: { status: string; decision_note?: string }
): Promise<Review> =>
  api.patch(`/api/reviews/${id}`, payload).then((r) => r.data);
