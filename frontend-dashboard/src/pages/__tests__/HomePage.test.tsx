import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthContext } from "@/context/AuthContext";
import HomePage from "../HomePage";

function renderHome(authValue: { isAuthenticated: boolean }) {
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={{ user: null, isLoading: false, ...authValue, login: async () => {}, register: async () => ({ client_id: "", email: "", status: "", message: "" }), logout: () => {} } as any}>
        <HomePage />
      </AuthContext.Provider>
    </MemoryRouter>
  );
}

describe("HomePage", () => {
  it("renders hero title", () => {
    renderHome({ isAuthenticated: false });
    expect(screen.getByRole("heading", { level: 1 })).toBeTruthy();
  });

  it("shows Comenzar ahora when not authenticated", () => {
    renderHome({ isAuthenticated: false });
    const buttons = screen.getAllByText("Comenzar ahora");
    expect(buttons.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Iniciar sesión")).toBeTruthy();
  });

  it("shows Ir a mi panel when authenticated", () => {
    renderHome({ isAuthenticated: true });
    expect(screen.getByText("Ir a mi panel")).toBeTruthy();
    expect(screen.queryByText("Iniciar sesión")).toBeNull();
  });

  it("renders how it works section", () => {
    renderHome({ isAuthenticated: false });
    expect(screen.getByText("¿Cómo funciona?")).toBeTruthy();
    expect(screen.getByText("Regístrate")).toBeTruthy();
    expect(screen.getByText("Conecta WhatsApp")).toBeTruthy();
    expect(screen.getByText("El agente trabaja por ti")).toBeTruthy();
  });

  it("renders plans section", () => {
    renderHome({ isAuthenticated: false });
    expect(screen.getByText("Planes")).toBeTruthy();
    expect(screen.getByText("Free")).toBeTruthy();
    expect(screen.getByText("Pro")).toBeTruthy();
    expect(screen.getByText("Enterprise")).toBeTruthy();
  });

  it("renders business types section", () => {
    renderHome({ isAuthenticated: false });
    expect(screen.getByText("¿Para quién es?")).toBeTruthy();
    expect(screen.getByText("Restaurantes")).toBeTruthy();
    expect(screen.getByText("Clínicas")).toBeTruthy();
  });
});
