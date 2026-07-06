import { apiFetch } from "./config";

export interface ConversationData {
  id: string;
  client_id: string;
  agent_id: string | null;
  wa_phone_number: string;
  status: string;
  last_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationListData {
  items: ConversationData[];
  count: number;
}

export interface MessageData {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  status: MessageStatus;
  tokens_used: number;
  created_at: string;
}

export type MessageStatus = "received" | "sent" | "failed" | "skipped";

export interface ConversationMessagesData {
  phone_number: string;
  status: string;
  messages: MessageData[];
}

export interface ConversationStatsData {
  total_conversations: number;
  active_conversations: number;
  messages_today: number;
  clients_with_conversations: number;
}

export function fetchConversations(
  clientId: string,
  limit: number = 20,
  offset: number = 0,
): Promise<ConversationListData> {
  return apiFetch<ConversationListData>(
    `/conversations?client_id=${encodeURIComponent(clientId)}&limit=${limit}&offset=${offset}`,
  );
}

export function fetchConversationMessages(
  conversationId: string,
): Promise<ConversationMessagesData> {
  return apiFetch<ConversationMessagesData>(
    `/conversations/${conversationId}/messages`,
  );
}

export function fetchConversationStats(): Promise<ConversationStatsData> {
  return apiFetch<ConversationStatsData>("/conversations/stats");
}
