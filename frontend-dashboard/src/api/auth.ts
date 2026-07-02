import { apiFetch } from "./config";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  client_id: string;
  role: string;
  status: string;
}

export interface RegisterResponse {
  client_id: string;
  email: string;
  status: string;
  message: string;
}

export interface CurrentClientResponse {
  client_id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  whatsapp_number: string;
  whatsapp_connected: boolean;
  plan: string;
  is_active: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  business_name: string;
  whatsapp_number: string;
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function register(data: RegisterData): Promise<RegisterResponse> {
  return apiFetch<RegisterResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function fetchMe(): Promise<CurrentClientResponse> {
  return apiFetch<CurrentClientResponse>("/auth/me");
}
