import { apiFetch } from "./config";

export interface ClientData {
  id: string;
  name: string;
  business_type: string;
  whatsapp_number: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  status?: string;
  whatsapp_connected?: boolean;
  phone_number_id?: string;
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

export interface BusinessHoursData {
  client_id: string;
  timezone: string;
  appointment_duration_minutes: number;
  reminder_offset_minutes: number;
  weekly: Record<string, string[][]>;
}

export interface BusinessHoursUpdateInput {
  timezone: string;
  appointment_duration_minutes: number;
  reminder_offset_minutes?: number;
  weekly: Record<string, string[][]>;
}

export interface AdminClientData {
  id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  is_active: boolean;
  whatsapp_number: string;
  whatsapp_connected: boolean;
  plan: string;
  created_at: string;
  updated_at: string;
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

export function approveClient(id: string): Promise<AdminClientData> {
  return apiFetch<AdminClientData>(`/clients/${id}/approve`, { method: "POST" });
}

export function rejectClient(id: string): Promise<AdminClientData> {
  return apiFetch<AdminClientData>(`/clients/${id}/reject`, { method: "POST" });
}

export function fetchClientSchedule(id: string): Promise<BusinessHoursData> {
  return apiFetch<BusinessHoursData>(`/clients/${id}/schedule`);
}

export function updateClientSchedule(
  id: string,
  data: BusinessHoursUpdateInput,
): Promise<BusinessHoursData> {
  return apiFetch<BusinessHoursData>(`/clients/${id}/schedule`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export interface ConnectWhatsappInput {
  phone_number_id: string;
  access_token: string;
}

export function connectClientWhatsapp(
  id: string,
  data: ConnectWhatsappInput,
): Promise<AdminClientData> {
  return apiFetch<AdminClientData>(`/clients/${id}/connect-whatsapp`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function disconnectClientWhatsapp(id: string): Promise<AdminClientData> {
  return apiFetch<AdminClientData>(`/clients/${id}/disconnect-whatsapp`, {
    method: "POST",
  });
}
