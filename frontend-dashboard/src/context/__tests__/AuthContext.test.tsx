import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { AuthProvider } from "../AuthContext";

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

function TestComponent() {
  const { user, isLoading, isAuthenticated, login, logout } = useAuth();
  return (
    <div>
      <div data-testid="loading">{String(isLoading)}</div>
      <div data-testid="auth">{String(isAuthenticated)}</div>
      <div data-testid="user-email">{user?.email ?? "null"}</div>
      <div data-testid="user-role">{user?.role ?? "null"}</div>
      <button data-testid="login-btn" onClick={() => login("a@b.com", "pass")}>Login</button>
      <button data-testid="logout-btn" onClick={() => logout()}>Logout</button>
    </div>
  );
}

function renderWithProvider(initialEntries = ["/"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  mockFetch.mockReset();
  localStorage.clear();
});

const mockProfile = {
  client_id: "1", email: "a@b.com", name: "Test", role: "superadmin",
  status: "active", whatsapp_number: "", whatsapp_connected: false, plan: "free", is_active: true,
};

describe("AuthContext", () => {
  it("starts loading, then unauthenticated when no token", async () => {
    renderWithProvider();
    expect(screen.getByTestId("loading").textContent).toBe("true");
    await waitFor(() => expect(screen.getByTestId("loading").textContent).toBe("false"));
    expect(screen.getByTestId("auth").textContent).toBe("false");
  });

  it("fetches profile when token exists", async () => {
    localStorage.setItem("auth_token", "valid-token");
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockProfile });
    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId("user-email").textContent).toBe("a@b.com"));
    expect(screen.getByTestId("auth").textContent).toBe("true");
  });

  it("clears state when fetchMe fails (invalid token)", async () => {
    localStorage.setItem("auth_token", "bad-token");
    mockFetch.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({ detail: "Unauthorized", error_type: "auth" }) });
    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId("auth").textContent).toBe("false"));
    expect(localStorage.getItem("auth_token")).toBeNull();
  });

  it("login stores token and sets user", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ access_token: "new-token", client_id: "1", role: "superadmin", status: "active", token_type: "bearer" }) });
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockProfile });
    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId("loading").textContent).toBe("false"));
    await userEvent.click(screen.getByTestId("login-btn"));
    await waitFor(() => expect(screen.getByTestId("user-email").textContent).toBe("a@b.com"));
    expect(localStorage.getItem("auth_token")).toBe("new-token");
  });

  it("logout clears user and token", async () => {
    localStorage.setItem("auth_token", "some-token");
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockProfile });
    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId("auth").textContent).toBe("true"));
    await userEvent.click(screen.getByTestId("logout-btn"));
    expect(localStorage.getItem("auth_token")).toBeNull();
    expect(screen.getByTestId("user-email").textContent).toBe("null");
  });
});
