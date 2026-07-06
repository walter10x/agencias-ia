import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchAppointments,
  fetchAvailability,
  createAppointment,
  rescheduleAppointment,
  cancelAppointment,
} from "../appointment";

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

function okJson(data: unknown) {
  return { ok: true, status: 200, json: async () => data };
}

describe("fetchAppointments", () => {
  it("construye query con filtros y defaults de paginación", async () => {
    mockFetch.mockResolvedValueOnce(okJson({ items: [], total: 0 }));
    await fetchAppointments({ dateFrom: "2026-07-01", dateTo: "2026-07-08", status: "pending" });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("/api/v1/appointments?");
    expect(url).toContain("date_from=2026-07-01");
    expect(url).toContain("date_to=2026-07-08");
    expect(url).toContain("status=pending");
    expect(url).toContain("limit=50");
    expect(url).toContain("offset=0");
  });

  it("omite filtros ausentes", async () => {
    mockFetch.mockResolvedValueOnce(okJson({ items: [], total: 0 }));
    await fetchAppointments();
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).not.toContain("date_from");
    expect(url).not.toContain("status=");
  });
});

describe("fetchAvailability", () => {
  it("llama GET /appointments/availability con la fecha codificada", async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({ date: "2026-07-06", timezone: "UTC", slot_duration_minutes: 30, slots: [] }),
    );
    const res = await fetchAvailability("2026-07-06");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/appointments/availability?date=2026-07-06",
      expect.any(Object),
    );
    expect(res.slot_duration_minutes).toBe(30);
  });
});

describe("createAppointment", () => {
  it("hace POST con el cuerpo de la cita", async () => {
    mockFetch.mockResolvedValueOnce(okJson({ id: "a1", status: "pending" }));
    await createAppointment({
      starts_at: "2026-07-06T10:00:00",
      contact_phone: "34606572976",
      contact_name: "Ana",
    });
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/appointments",
      expect.objectContaining({ method: "POST" }),
    );
    const body = JSON.parse((mockFetch.mock.calls[0][1] as RequestInit).body as string);
    expect(body.contact_phone).toBe("34606572976");
  });

  it("propaga errores de la API (p.ej. solape 409)", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({ detail: "El horario se solapa con otra cita", error_type: "conflict" }),
    });
    await expect(
      createAppointment({ starts_at: "2026-07-06T10:00:00", contact_phone: "34606572976" }),
    ).rejects.toThrow("El horario se solapa con otra cita");
  });
});

describe("rescheduleAppointment", () => {
  it("hace PATCH /appointments/:id con el nuevo inicio", async () => {
    mockFetch.mockResolvedValueOnce(okJson({ id: "a1", status: "pending" }));
    await rescheduleAppointment("a1", { starts_at: "2026-07-07T09:00:00" });
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/appointments/a1",
      expect.objectContaining({ method: "PATCH" }),
    );
  });
});

describe("cancelAppointment", () => {
  it("hace DELETE /appointments/:id", async () => {
    mockFetch.mockResolvedValueOnce(okJson({ id: "a1", status: "cancelled" }));
    const res = await cancelAppointment("a1");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/appointments/a1",
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(res.status).toBe("cancelled");
  });
});
