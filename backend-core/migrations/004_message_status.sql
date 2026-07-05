-- ============================================================
-- Migración 004: Estado de entrega en messages (Fase 1 MVP)
-- Añade `status` a la tabla `messages` para persistir el estado
-- real del envío de las respuestas del agente:
--   - received: mensaje entrante del usuario final
--   - sent:     respuesta confirmada por Meta Cloud API
--   - failed:   el envío a Meta falló
--   - skipped:  Meta no configurado; el mensaje NO se envió
-- Nota: se numera 004 porque 003 está reservada para
-- `003_appointments.sql` (Fase 2 del PLAN-MVP).
-- Ejecutar en: Supabase SQL Editor
-- ============================================================

ALTER TABLE messages
    ADD COLUMN status TEXT NOT NULL DEFAULT 'received'
        CHECK (status IN ('received', 'sent', 'failed', 'skipped'));

COMMENT ON COLUMN messages.status IS
    'received: entrante | sent: confirmado por Meta | failed: envío fallido | skipped: Meta no configurado (no enviado)';
