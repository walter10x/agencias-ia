import { apiFetch } from "./config";

export interface FeedbackData {
  id: string;
  client_id: string;
  lead_id: string | null;
  conversation_id: string | null;
  rating: number;
  comment: string;
  created_at: string;
}

export interface FeedbackListData {
  items: FeedbackData[];
  total: number;
}

export interface FeedbackStatsData {
  total: number;
  average_rating: number;
  rating_distribution: Record<number, number>;
}

export interface FeedbackCreateInput {
  client_id: string;
  rating: number;
  lead_id?: string;
  conversation_id?: string;
  comment?: string;
}

export function fetchFeedbackList(
  client_id: string,
  limit?: number,
  offset?: number,
): Promise<FeedbackListData> {
  const params = new URLSearchParams({ client_id });
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  return apiFetch<FeedbackListData>(`/feedback?${params}`);
}

export function createFeedback(
  data: FeedbackCreateInput,
): Promise<FeedbackData> {
  return apiFetch<FeedbackData>("/feedback", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function fetchFeedbackStats(
  client_id: string,
): Promise<FeedbackStatsData> {
  return apiFetch<FeedbackStatsData>(
    `/feedback/stats?client_id=${encodeURIComponent(client_id)}`,
  );
}
