-- ============================================================
-- Migración 003: Módulo de agenda (Fase 2 MVP)
-- Ejecutar en: Supabase SQL Editor
--
-- 1. Tabla `appointments`: citas agendadas por el bot o el panel.
-- 2. Config de disponibilidad por cliente: siguiendo el patrón de
--    la migración 002 (extender `clients` con columnas por-tenant,
--    como se hizo con auth y landing), el horario semanal vive en
--    una columna JSONB `business_hours` + `appointment_duration_minutes`
--    en `clients`, en lugar de una tabla aparte. Un negocio = un
--    horario; se lee en una sola query junto al cliente y PostgREST
--    lo devuelve sin joins.
-- ============================================================

-- ------------------------------------------------------------
-- Config de disponibilidad por cliente
-- business_hours formato:
-- {
--   "timezone": "UTC",
--   "weekly": {
--     "monday":    [["09:00", "18:00"]],
--     "tuesday":   [["09:00", "18:00"]],
--     "wednesday": [["09:00", "18:00"]],
--     "thursday":  [["09:00", "18:00"]],
--     "friday":    [["09:00", "18:00"]],
--     "saturday":  [],
--     "sunday":    []
--   }
-- }
-- Cada día admite múltiples rangos (ej. mañana y tarde):
--   "monday": [["09:00","13:00"], ["15:00","19:00"]]
-- ------------------------------------------------------------

ALTER TABLE clients
    ADD COLUMN business_hours JSONB NOT NULL DEFAULT '{
        "timezone": "UTC",
        "weekly": {
            "monday":    [["09:00", "18:00"]],
            "tuesday":   [["09:00", "18:00"]],
            "wednesday": [["09:00", "18:00"]],
            "thursday":  [["09:00", "18:00"]],
            "friday":    [["09:00", "18:00"]],
            "saturday":  [],
            "sunday":    []
        }
    }'::jsonb,
    ADD COLUMN appointment_duration_minutes INTEGER NOT NULL DEFAULT 30
        CHECK (appointment_duration_minutes BETWEEN 5 AND 480);

COMMENT ON COLUMN clients.business_hours IS
    'Horario semanal del negocio: {"timezone": IANA tz, "weekly": {dia: [[HH:MM, HH:MM], ...]}}';
COMMENT ON COLUMN clients.appointment_duration_minutes IS
    'Duración de cita por defecto en minutos (slots de disponibilidad).';

-- ------------------------------------------------------------
-- Tabla de citas
-- ------------------------------------------------------------

CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    contact_phone TEXT NOT NULL,
    contact_name TEXT NOT NULL DEFAULT '',
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed')),
    notes TEXT NOT NULL DEFAULT '',
    reminder_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_appointments_time_range CHECK (ends_at > starts_at)
);

-- Consultas típicas: agenda de un tenant por rango de fechas
CREATE INDEX idx_appointments_client_starts ON appointments(client_id, starts_at);
-- Filtro por estado dentro del tenant (listados del panel)
CREATE INDEX idx_appointments_client_status ON appointments(client_id, status);
-- Búsqueda por teléfono del contacto (cancelación desde el bot)
CREATE INDEX idx_appointments_client_phone ON appointments(client_id, contact_phone);
-- Job de recordatorios (Fase 4): citas próximas sin recordatorio enviado
CREATE INDEX idx_appointments_reminder ON appointments(starts_at)
    WHERE reminder_sent_at IS NULL AND status IN ('pending', 'confirmed');

-- Trigger de updated_at (función definida en la migración 001)
CREATE TRIGGER trg_appointments_updated
    BEFORE UPDATE ON appointments
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- Row Level Security (mismo patrón que las tablas core)
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON appointments FOR ALL USING (true);
