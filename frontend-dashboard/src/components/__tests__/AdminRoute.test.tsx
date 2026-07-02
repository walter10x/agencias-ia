import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthContext } from "@/context/AuthContext";
import AdminRoute from "../AdminRoute";

function renderWithAuth(authValue: { isAuthenticated: boolean; isLoading: boolean; user: { role: string } | null }) {
  return render(
    <MemoryRouter initialEntries={["/admin"]}>
      <AuthContext.Provider value={{ ...authValue, login: async () => {}, register: async () => ({ client_id: "", email: "", status: "", message: "" }), logout: () => {} } as any}>
        <Routes>
          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<div data-testid="content">Admin Content</div>} />
          </Route>
          <Route path="/login" element={<div data-testid="login-page">Login</div>} />
          <Route path="/" element={<div data-testid="home">Home</div>} />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>
  );
}

describe("AdminRoute", () => {
  it("redirects to /login when not authenticated", () => {
    renderWithAuth({ isAuthenticated: false, isLoading: false, user: null });
    expect(screen.queryByTestId("content")).toBeNull();
    expect(screen.getByTestId("login-page")).toBeTruthy();
  });

  it("redirects to / when not superadmin", () => {
    renderWithAuth({ isAuthenticated: true, isLoading: false, user: { role: "client_admin" } });
    expect(screen.queryByTestId("content")).toBeNull();
    expect(screen.getByTestId("home")).toBeTruthy();
  });

  it("renders children when superadmin", () => {
    renderWithAuth({ isAuthenticated: true, isLoading: false, user: { role: "superadmin" } });
    expect(screen.getByTestId("content")).toBeTruthy();
  });
});
