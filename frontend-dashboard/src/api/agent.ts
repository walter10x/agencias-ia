import { apiFetch } from "./config";

export interface AgentToolData {
  name: string;
  description: string;
  endpoint: string;
}

export interface AgentData {
  id: string;
  client_id: string;
  name: string;
  personality: string;
  tools: AgentToolData[];
  knowledge_base_refs: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgentListData {
  items: AgentData[];
  count: number;
}

export interface AgentCreateInput {
  name: string;
  personality: string;
  tools: AgentToolData[];
  knowledge_base_refs: string[];
}

export interface AgentUpdateInput {
  name?: string;
  personality?: string;
  tools?: AgentToolData[];
  knowledge_base_refs?: string[];
}

export function fetchAgentsByClient(
  clientId: string,
): Promise<AgentListData> {
  return apiFetch<AgentListData>(`/clients/${clientId}/agents`);
}

export function fetchAgent(id: string): Promise<AgentData> {
  return apiFetch<AgentData>(`/agents/${id}`);
}

export function createAgent(
  clientId: string,
  data: AgentCreateInput,
): Promise<AgentData> {
  return apiFetch<AgentData>(`/clients/${clientId}/agents`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateAgent(
  id: string,
  data: AgentUpdateInput,
): Promise<AgentData> {
  return apiFetch<AgentData>(`/agents/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deactivateAgent(id: string): Promise<AgentData> {
  return apiFetch<AgentData>(`/agents/${id}`, { method: "DELETE" });
}

export function deleteAgent(id: string): Promise<void> {
  return apiFetch<void>(`/agents/${id}/permanent`, { method: "DELETE" });
}
