import { apiFetch } from "./config";

export interface ContactSummary {
  phone: string;
  display_name: string;
  lead_status: string | null;
  last_activity_at: string | null;
  has_conversation: boolean;
  has_appointments: boolean;
}

export interface ContactListData {
  items: ContactSummary[];
  total: number;
}

export interface ContactDetail {
  client_id: string;
  phone: string;
  display_name: string;
  lead: {
    id: string;
    status: string;
    score: number;
    notes: string;
    name: string;
  } | null;
  conversations: { id: string; status: string; updated_at: string }[];
  appointments: {
    id: string;
    starts_at: string;
    status: string;
    contact_name: string;
  }[];
  last_activity_at: string | null;
}

export function fetchContacts(limit = 50, offset = 0): Promise<ContactListData> {
  return apiFetch<ContactListData>(`/contacts?limit=${limit}&offset=${offset}`);
}

export function fetchContactByPhone(phone: string): Promise<ContactDetail> {
  return apiFetch<ContactDetail>(`/contacts/by-phone/${encodeURIComponent(phone)}`);
}
