import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getReviews, getReview, getReviewStats, decideReview, Review } from "../api/review";

export const reviewKeys = {
  all:     ["reviews"] as const,
  stats:   ["reviews", "stats"] as const,
  detail:  (id: string) => ["reviews", id] as const,
};

export const useReviews    = (params?: Parameters<typeof getReviews>[0]) =>
  useQuery({ queryKey: [...reviewKeys.all, params], queryFn: () => getReviews(params) });

export const useReview     = (id: string) =>
  useQuery({ queryKey: reviewKeys.detail(id), queryFn: () => getReview(id), enabled: !!id });

export const useReviewStats = () =>
  useQuery({ queryKey: reviewKeys.stats, queryFn: getReviewStats });

export const useDecideReview = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { status: string; decision_note?: string } }) =>
      decideReview(id, payload),
    onSuccess: (_data: Review, vars) => {
      qc.invalidateQueries({ queryKey: reviewKeys.all });
      qc.invalidateQueries({ queryKey: reviewKeys.stats });
      qc.invalidateQueries({ queryKey: reviewKeys.detail(vars.id) });
    },
  });
};
