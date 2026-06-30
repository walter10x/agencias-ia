import { apiFetch } from "./config";

export interface ClientData {
  id: string;
  name: string;
  business_type: string;
  whatsapp_number: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClientListData {
  items: ClientData[];
  count: number;
}

export interface ClientCreateInput {
  name: string;
  business_type: string;
  whatsapp_number: string;
}

export interface ClientUpdateInput {
  name?: string;
  whatsapp_number?: string;
}

export function fetchClients(
  limit: number,
  offset: number,
): Promise<ClientListData> {
  return apiFetch<ClientListData>(
    `/clients?limit=${limit}&offset=${offset}`,
  );
}

export function fetchClient(id: string): Promise<ClientData> {
  return apiFetch<ClientData>(`/clients/${id}`);
}

export function searchClientByWhatsapp(
  whatsapp: string,
): Promise<ClientListData> {
  return apiFetch<ClientListData>(
    `/clients?whatsapp=${encodeURIComponent(whatsapp)}`,
  );
}

export function createClient(data: ClientCreateInput): Promise<ClientData> {
  return apiFetch<ClientData>("/clients", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateClient(
  id: string,
  data: ClientUpdateInput,
): Promise<ClientData> {
  return apiFetch<ClientData>(`/clients/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deactivateClient(id: string): Promise<ClientData> {
  return apiFetch<ClientData>(`/clients/${id}`, { method: "DELETE" });
}
