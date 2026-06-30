import { apiFetch } from "./config";
import type { ClientData } from "./client";
import type { AgentData } from "./agent";

export interface TemplateItem {
  slug: string;
  name: string;
  emoji: string;
  description: string;
  tools_count: number;
}

export interface TemplateListData {
  templates: TemplateItem[];
}

export interface ApplyTemplateInput {
  name: string;
  whatsapp_number: string;
}

export interface ApplyTemplateOutput {
  template_slug: string;
  client: ClientData;
  agent: AgentData;
  message: string;
}

export function fetchTemplates(): Promise<TemplateListData> {
  return apiFetch<TemplateListData>("/templates");
}

export function applyTemplate(
  slug: string,
  data: ApplyTemplateInput,
): Promise<ApplyTemplateOutput> {
  return apiFetch<ApplyTemplateOutput>(`/templates/${slug}/apply`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}
