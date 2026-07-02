import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiFetch } from "../config";

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
  localStorage.clear();
});

describe("apiFetch JWT interceptor", () => {
  it("sends request without token when not in localStorage", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ data: "ok" }) });
    await apiFetch("/test");
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/test", expect.objectContaining({
      headers: { "Content-Type": "application/json" },
    }));
  });

  it("injects Authorization header when token exists", async () => {
    localStorage.setItem("auth_token", "my-jwt-token");
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ data: "ok" }) });
    await apiFetch("/test");
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/test", expect.objectContaining({
      headers: { "Content-Type": "application/json", Authorization: "Bearer my-jwt-token" },
    }));
  });

  it("returns undefined on 204", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204, json: async () => {} });
    const res = await apiFetch("/no-content");
    expect(res).toBeUndefined();
  });

  it("throws ApiError on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Bad request", error_type: "validation" }),
    });
    await expect(apiFetch("/bad")).rejects.toThrow("Bad request");
  });
});
