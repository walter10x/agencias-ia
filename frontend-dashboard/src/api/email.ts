import { apiFetch } from "./config";

export interface EmailLogData {
  id: string;
  client_id: string;
  lead_id: string | null;
  to_email: string;
  subject: string;
  template_slug: string;
  sequence_number: number;
  status: string;
  error_message: string;
  sent_at: string;
  created_at: string;
}

export interface EmailListData {
  items: EmailLogData[];
  total: number;
}

export interface EmailStatsData {
  total_sent: number;
  total_opened: number;
  total_clicked: number;
  total_bounced: number;
  open_rate: number;
  click_rate: number;
  by_template: Record<string, number>;
}

export interface EmailSendInput {
  client_id: string;
  to_email: string;
  rubro_slug: string;
  sequence_number: number;
  lead_id?: string | null;
  business_name?: string;
  contact_name?: string;
}

export interface EmailSendResult {
  id: string;
  status: string;
}

export function sendEmail(data: EmailSendInput): Promise<EmailSendResult> {
  return apiFetch<EmailSendResult>("/emails/send", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function fetchEmails(
  client_id: string,
  lead_id?: string,
  limit?: number,
  offset?: number,
): Promise<EmailListData> {
  const params = new URLSearchParams({ client_id });
  if (lead_id) params.set("lead_id", lead_id);
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  return apiFetch<EmailListData>(`/emails?${params}`);
}

export function fetchEmailStats(client_id: string): Promise<EmailStatsData> {
  return apiFetch<EmailStatsData>(`/emails/stats?client_id=${encodeURIComponent(client_id)}`);
}

export function fetchEmailTemplates(): Promise<{ rubros: string[] }> {
  return apiFetch<{ rubros: string[] }>("/emails/templates");
}
