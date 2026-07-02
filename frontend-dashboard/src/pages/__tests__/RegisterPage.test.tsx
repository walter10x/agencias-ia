import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthContext } from "@/context/AuthContext";
import RegisterPage from "../RegisterPage";

const mockRegister = vi.fn();

function renderRegister() {
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={{ user: null, isLoading: false, isAuthenticated: false, login: async () => {}, register: mockRegister, logout: () => {} } as any}>
        <RegisterPage />
      </AuthContext.Provider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  mockRegister.mockReset();
});

describe("RegisterPage", () => {
  it("renders all form fields", () => {
    renderRegister();
    expect(screen.getByPlaceholderText("tu@email.com")).toBeTruthy();
    expect(screen.getByPlaceholderText("••••••••")).toBeTruthy();
    expect(screen.getByPlaceholderText("Mi Negocio")).toBeTruthy();
    expect(screen.getByPlaceholderText("521234567890")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Crear cuenta" })).toBeTruthy();
    const buttons = screen.getAllByRole("button", { name: "Crear cuenta" });
    expect(buttons.length).toBe(1);
  });

  it("shows validation errors", async () => {
    renderRegister();
    await userEvent.click(screen.getAllByRole("button", { name: "Crear cuenta" })[0]);
    expect(await screen.findByText("Ingresa un email válido.")).toBeTruthy();
  });

  it("validates password length", async () => {
    renderRegister();
    await userEvent.type(screen.getByPlaceholderText("tu@email.com"), "a@b.com");
    await userEvent.type(screen.getByPlaceholderText("••••••••"), "short");
    await userEvent.click(screen.getAllByRole("button", { name: "Crear cuenta" })[0]);
    expect(await screen.findByText("La contraseña debe tener al menos 8 caracteres.")).toBeTruthy();
  });

  it("validates whatsapp number digits", async () => {
    renderRegister();
    await userEvent.type(screen.getByPlaceholderText("tu@email.com"), "a@b.com");
    await userEvent.type(screen.getByPlaceholderText("••••••••"), "12345678");
    await userEvent.type(screen.getByPlaceholderText("Mi Negocio"), "Mi Negocio");
    await userEvent.type(screen.getByPlaceholderText("521234567890"), "abc");
    await userEvent.click(screen.getAllByRole("button", { name: "Crear cuenta" })[0]);
    expect(await screen.findByText("El número de WhatsApp debe contener solo dígitos.")).toBeTruthy();
  });

  it("calls register and shows success", async () => {
    mockRegister.mockResolvedValueOnce({ client_id: "1", email: "a@b.com", status: "pending", message: "Registro exitoso!" });
    renderRegister();
    await userEvent.type(screen.getByPlaceholderText("tu@email.com"), "a@b.com");
    await userEvent.type(screen.getByPlaceholderText("••••••••"), "12345678");
    await userEvent.type(screen.getByPlaceholderText("Mi Negocio"), "Mi Negocio");
    await userEvent.type(screen.getByPlaceholderText("521234567890"), "521234567890");
    await userEvent.click(screen.getAllByRole("button", { name: "Crear cuenta" })[0]);
    expect(await screen.findByText("Registro exitoso!")).toBeTruthy();
    expect(mockRegister).toHaveBeenCalledWith({ email: "a@b.com", password: "12345678", business_name: "Mi Negocio", whatsapp_number: "521234567890" });
  });

  it("shows API error on failure", async () => {
    mockRegister.mockRejectedValueOnce({ detail: "Email ya registrado" });
    renderRegister();
    await userEvent.type(screen.getByPlaceholderText("tu@email.com"), "dup@b.com");
    await userEvent.type(screen.getByPlaceholderText("••••••••"), "12345678");
    await userEvent.type(screen.getByPlaceholderText("Mi Negocio"), "Dup");
    await userEvent.type(screen.getByPlaceholderText("521234567890"), "521234567890");
    await userEvent.click(screen.getAllByRole("button", { name: "Crear cuenta" })[0]);
    expect(await screen.findByText("Email ya registrado")).toBeTruthy();
  });

  it("has link to login page", () => {
    renderRegister();
    const link = screen.getByText("Inicia sesión");
    expect(link).toBeTruthy();
    expect(link.closest("a")).toHaveAttribute("href", "/login");
  });
});
