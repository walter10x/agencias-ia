import { apiFetch } from "./config";

export interface LeadData {
  id: string;
  client_id: string;
  phone: string;
  name: string;
  status: string;
  source: string;
  score: number;
  notes: string;
  last_contacted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadListData {
  items: LeadData[];
  total: number;
}

export interface LeadStatsData {
  total: number;
  by_status: Record<string, number>;
  conversion_rate: number;
  new_today: number;
  avg_score: number;
}

export interface LeadCreateInput {
  client_id: string;
  phone: string;
  name?: string;
  source?: string;
}

export interface LeadUpdateInput {
  status?: string;
  score?: number;
  notes?: string;
  name?: string;
}

export function fetchLeads(
  client_id: string,
  status?: string,
  limit?: number,
  offset?: number,
): Promise<LeadListData> {
  const params = new URLSearchParams({ client_id });
  if (status) params.set("status", status);
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  return apiFetch<LeadListData>(`/leads?${params}`);
}

export function updateLead(
  id: string,
  data: LeadUpdateInput,
): Promise<LeadData> {
  return apiFetch<LeadData>(`/leads/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function fetchLeadStats(
  client_id: string,
): Promise<LeadStatsData> {
  return apiFetch<LeadStatsData>(`/leads/stats?client_id=${encodeURIComponent(client_id)}`);
}

export function sendProactiveMessage(
  lead_id: string,
  message_text: string,
): Promise<void> {
  return apiFetch<void>(`/leads/${lead_id}/send-message`, {
    method: "POST",
    body: JSON.stringify({ message_text }),
  });
}

export function createLead(data: LeadCreateInput): Promise<LeadData> {
  return apiFetch<LeadData>("/leads", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
