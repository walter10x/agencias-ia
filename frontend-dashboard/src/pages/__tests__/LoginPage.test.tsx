import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthContext } from "@/context/AuthContext";
import LoginPage from "../LoginPage";

const mockLogin = vi.fn();
const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual as any, useNavigate: () => mockNavigate };
});

function renderLogin() {
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={{ user: null, isLoading: false, isAuthenticated: false, login: mockLogin, register: async () => ({ client_id: "", email: "", status: "", message: "" }), logout: () => {} } as any}>
        <LoginPage />
      </AuthContext.Provider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  mockLogin.mockReset();
  mockNavigate.mockReset();
});

describe("LoginPage", () => {
  it("renders form fields and submit button", () => {
    renderLogin();
    expect(screen.getByPlaceholderText("admin@agencia-ia.com")).toBeTruthy();
    expect(screen.getByPlaceholderText("••••••••")).toBeTruthy();
    expect(screen.getByText("Iniciar sesión")).toBeTruthy();
  });

  it("shows error when login fails", async () => {
    mockLogin.mockRejectedValueOnce({ detail: "Credenciales inválidas" });
    renderLogin();
    await userEvent.type(screen.getByPlaceholderText("admin@agencia-ia.com"), "a@b.com");
    await userEvent.type(screen.getByPlaceholderText("••••••••"), "wrong");
    await userEvent.click(screen.getByText("Iniciar sesión"));
    expect(await screen.findByText("Credenciales inválidas")).toBeTruthy();
  });

  it("calls login and navigates to /app on success", async () => {
    mockLogin.mockResolvedValueOnce(undefined);
    renderLogin();
    await userEvent.type(screen.getByPlaceholderText("admin@agencia-ia.com"), "a@b.com");
    await userEvent.type(screen.getByPlaceholderText("••••••••"), "pass123");
    await userEvent.click(screen.getByText("Iniciar sesión"));
    expect(mockLogin).toHaveBeenCalledWith("a@b.com", "pass123");
    await vi.waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/app"));
  });

  it("has link to register page", () => {
    renderLogin();
    expect(screen.getByText("Regístrate")).toBeTruthy();
    expect(screen.getByText("Regístrate").closest("a")).toHaveAttribute("href", "/register");
  });
});
