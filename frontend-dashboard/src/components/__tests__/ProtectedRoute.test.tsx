import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthContext } from "@/context/AuthContext";
import ProtectedRoute from "../ProtectedRoute";

function renderWithAuth(authValue: { isAuthenticated: boolean; isLoading: boolean }) {
  return render(
    <MemoryRouter initialEntries={["/protected"]}>
      <AuthContext.Provider value={{ ...authValue, user: null, login: async () => {}, register: async () => ({ client_id: "", email: "", status: "", message: "" }), logout: () => {} } as any}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/protected" element={<div data-testid="content">Protected Content</div>} />
          </Route>
          <Route path="/login" element={<div data-testid="login-page">Login</div>} />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  it("shows spinner while loading", () => {
    renderWithAuth({ isAuthenticated: false, isLoading: true });
    expect(document.querySelector(".animate-spin")).toBeTruthy();
  });

  it("redirects to /login when not authenticated", () => {
    renderWithAuth({ isAuthenticated: false, isLoading: false });
    expect(screen.queryByTestId("content")).toBeNull();
    expect(screen.getByTestId("login-page")).toBeTruthy();
  });

  it("renders children when authenticated", () => {
    renderWithAuth({ isAuthenticated: true, isLoading: false });
    expect(screen.getByTestId("content")).toBeTruthy();
  });
});
