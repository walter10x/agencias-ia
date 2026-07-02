import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthContext } from "@/context/AuthContext";
import ClientRoute from "../ClientRoute";

function renderWithAuth(authValue: { isAuthenticated: boolean; isLoading: boolean; user: { role: string } | null }) {
  return render(
    <MemoryRouter initialEntries={["/client"]}>
      <AuthContext.Provider value={{ ...authValue, login: async () => {}, register: async () => ({ client_id: "", email: "", status: "", message: "" }), logout: () => {} } as any}>
        <Routes>
          <Route element={<ClientRoute />}>
            <Route path="/client" element={<div data-testid="content">Client Content</div>} />
          </Route>
          <Route path="/login" element={<div data-testid="login-page">Login</div>} />
          <Route path="/app" element={<div data-testid="app">App</div>} />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>
  );
}

describe("ClientRoute", () => {
  it("redirects to /login when not authenticated", () => {
    renderWithAuth({ isAuthenticated: false, isLoading: false, user: null });
    expect(screen.getByTestId("login-page")).toBeTruthy();
  });

  it("redirects to /app when not client_admin", () => {
    renderWithAuth({ isAuthenticated: true, isLoading: false, user: { role: "superadmin" } });
    expect(screen.getByTestId("app")).toBeTruthy();
  });

  it("renders children when client_admin", () => {
    renderWithAuth({ isAuthenticated: true, isLoading: false, user: { role: "client_admin" } });
    expect(screen.getByTestId("content")).toBeTruthy();
  });
});
