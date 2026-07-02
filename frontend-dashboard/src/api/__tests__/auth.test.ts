import { describe, it, expect, vi, beforeEach } from "vitest";
import { login, register, fetchMe } from "../auth";

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

describe("login", () => {
  it("calls POST /auth/login with email and password", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: "tok", client_id: "1", role: "superadmin", status: "active", token_type: "bearer" }),
    });
    const res = await login("a@b.com", "pass123");
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/auth/login", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ email: "a@b.com", password: "pass123" }),
    }));
    expect(res.access_token).toBe("tok");
  });

  it("throws on error response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Credenciales inválidas", error_type: "auth" }),
    });
    await expect(login("a@b.com", "wrong")).rejects.toThrow("Credenciales inválidas");
  });
});

describe("register", () => {
  it("calls POST /auth/register with data", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ client_id: "1", email: "a@b.com", status: "pending", message: "Ok" }),
    });
    const res = await register({ email: "a@b.com", password: "12345678", business_name: "Mi Negocio", whatsapp_number: "521234567890" });
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/auth/register", expect.objectContaining({ method: "POST" }));
    expect(res.status).toBe("pending");
  });

  it("throws on duplicate email", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({ detail: "Email ya registrado", error_type: "conflict" }),
    });
    await expect(register({ email: "dup@b.com", password: "12345678", business_name: "Dup", whatsapp_number: "521234567890" })).rejects.toThrow("Email ya registrado");
  });
});

describe("fetchMe", () => {
  it("calls GET /auth/me and returns profile", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ client_id: "1", email: "a@b.com", name: "Test", role: "superadmin", status: "active", whatsapp_number: "", whatsapp_connected: false, plan: "free", is_active: true }),
    });
    const res = await fetchMe();
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/auth/me", expect.any(Object));
    expect(res.email).toBe("a@b.com");
    expect(res.role).toBe("superadmin");
  });
});
