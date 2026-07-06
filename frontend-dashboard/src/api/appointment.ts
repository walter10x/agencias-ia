import { apiFetch } from "./config";

export type AppointmentStatus =
  | "pending"
  | "confirmed"
  | "cancelled"
  | "completed";

export interface AppointmentData {
  id: string;
  client_id: string;
  conversation_id: string | null;
  contact_phone: string;
  contact_name: string;
  starts_at: string;
  ends_at: string;
  status: string;
  notes: string;
  reminder_sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AppointmentListData {
  items: AppointmentData[];
  total: number;
}

export interface AppointmentCreateInput {
  starts_at: string;
  contact_phone: string;
  contact_name?: string;
  ends_at?: string | null;
  notes?: string;
  conversation_id?: string | null;
}

export interface AppointmentRescheduleInput {
  starts_at: string;
  ends_at?: string | null;
}

export interface AvailabilitySlotData {
  starts_at: string;
  ends_at: string;
  label: string;
}

export interface AvailabilityData {
  date: string;
  timezone: string;
  slot_duration_minutes: number;
  slots: AvailabilitySlotData[];
}

export interface AppointmentFilters {
  dateFrom?: string;
  dateTo?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export function fetchAppointments(
  filters: AppointmentFilters = {},
): Promise<AppointmentListData> {
  const params = new URLSearchParams();
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  if (filters.status) params.set("status", filters.status);
  params.set("limit", String(filters.limit ?? 50));
  params.set("offset", String(filters.offset ?? 0));
  return apiFetch<AppointmentListData>(`/appointments?${params.toString()}`);
}

export function fetchAvailability(date: string): Promise<AvailabilityData> {
  return apiFetch<AvailabilityData>(
    `/appointments/availability?date=${encodeURIComponent(date)}`,
  );
}

export function createAppointment(
  data: AppointmentCreateInput,
): Promise<AppointmentData> {
  return apiFetch<AppointmentData>("/appointments", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function rescheduleAppointment(
  id: string,
  data: AppointmentRescheduleInput,
): Promise<AppointmentData> {
  return apiFetch<AppointmentData>(`/appointments/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function cancelAppointment(id: string): Promise<AppointmentData> {
  return apiFetch<AppointmentData>(`/appointments/${id}`, {
    method: "DELETE",
  });
}
