const API_BASE = "/api/v1";

interface ApiErrorShape {
  detail: string;
  error_type: string;
}

export class ApiError extends Error {
  detail: string;
  error_type: string;

  constructor(shape: ApiErrorShape) {
    super(shape.detail);
    this.detail = shape.detail;
    this.error_type = shape.error_type;
  }
}

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("auth_token");
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { "Content-Type": "application/json", ...getAuthHeaders(), ...options?.headers },
    ...options,
  });

  if (!response.ok) {
    const error: ApiErrorShape = await response.json().catch(() => ({
      detail: response.statusText,
      error_type: "unknown",
    }));
    throw new ApiError(error);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}
