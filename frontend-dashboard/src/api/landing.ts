import { apiFetch } from "./config";

export interface LandingPublicConfig {
  client_name: string;
  landing_title: string;
  landing_description: string;
  landing_active: boolean;
  landing_primary_color: string;
}

export interface LandingSubmitInput {
  name: string;
  whatsapp: string;
  interest?: string;
}

export interface LandingSubmitOutput {
  lead_id: string;
  message: string;
  auto_reply: string;
}

export interface LandingConfig {
  client_id: string;
  landing_slug: string | null;
  landing_title: string;
  landing_description: string;
  landing_active: boolean;
  landing_primary_color: string;
  landing_auto_reply: string;
  leads_count: number;
}

export interface LandingUpdateInput {
  landing_slug?: string;
  landing_title?: string;
  landing_description?: string;
  landing_active?: boolean;
  landing_primary_color?: string;
  landing_auto_reply?: string;
}

export function fetchLandingPublicConfig(slug: string): Promise<LandingPublicConfig> {
  return apiFetch<LandingPublicConfig>(`/landing/${slug}/config`);
}

export function submitLandingForm(
  slug: string,
  data: LandingSubmitInput,
): Promise<LandingSubmitOutput> {
  return apiFetch<LandingSubmitOutput>(`/landing/${slug}/submit`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function fetchLandingConfig(clientId: string): Promise<LandingConfig> {
  return apiFetch<LandingConfig>(`/clients/${clientId}/landing`);
}

export function updateLandingConfig(
  clientId: string,
  data: LandingUpdateInput,
): Promise<LandingConfig> {
  return apiFetch<LandingConfig>(`/clients/${clientId}/landing`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}
