import { apiFetch } from "./config";

export interface ContactSummary {
  phone: string;
  display_name: string;
  lead_status: string | null;
  last_activity_at: string | null;
  has_conversation: boolean;
  has_appointments: boolean;
  inactive_days?: number | null;
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

export function fetchContacts(
  limit = 50,
  offset = 0,
  inactiveDays?: number | null,
): Promise<ContactListData> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (inactiveDays != null && inactiveDays > 0) {
    params.set("inactive_days", String(inactiveDays));
  }
  return apiFetch<ContactListData>(`/contacts?${params.toString()}`);
}

export function fetchContactByPhone(phone: string): Promise<ContactDetail> {
  return apiFetch<ContactDetail>(`/contacts/by-phone/${encodeURIComponent(phone)}`);
}

export function updateContactNotes(
  phone: string,
  data: { notes: string; display_name?: string | null },
): Promise<ContactDetail> {
  return apiFetch<ContactDetail>(
    `/contacts/by-phone/${encodeURIComponent(phone)}/notes`,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    },
  );
}

export function markContactContacted(phone: string): Promise<ContactDetail> {
  return apiFetch<ContactDetail>(
    `/contacts/by-phone/${encodeURIComponent(phone)}/mark-contacted`,
    { method: "POST" },
  );
}
