-- =============================================================================
-- Paso 24 — Onboarding tenant #N (clon del patrón Orinoco / bot padre)
-- =============================================================================
-- REQUISITO: un número WhatsApp DISTINTO al de Orinoco (+34682743315).
-- No se puede compartir el mismo phone_number_id: el webhook enruta por `to`.
--
-- Antes de ejecutar, sustituye TODOS los placeholders:
--   __CLIENT_UUID__     → uuid gen_random_uuid() o fijo
--   __AGENT_UUID__      → otro uuid
--   __BUSINESS_NAME__   → ej. Clínica Demo
--   __WHATSAPP_DIGITS__ → ej. 34611122334  (sin +)
--   __PHONE_NUMBER_ID__ → ej. +34611122334 (E.164, YCloud `to`)
--   __EMAIL__           → login del client_admin (opcional)
--   __TIMEZONE__        → ej. Europe/Madrid
--   __AGENT_NAME__      → ej. Asistente Clínica Demo
--   __PERSONALITY__     → prompt del negocio (calificar + agenda)
--
-- Uso (Dokploy / servidor):
--   docker exec -i agencia-postgres psql -U postgres -d agencias_db -v ON_ERROR_STOP=1 < onboard.sql
-- =============================================================================

BEGIN;

INSERT INTO clients (
  id, name, business_type, whatsapp_number, is_active,
  email, password_hash, role, status,
  phone_number_id, whatsapp_connected, plan,
  appointment_duration_minutes,
  business_hours
) VALUES (
  '__CLIENT_UUID__',
  '__BUSINESS_NAME__',
  'otro',
  '__WHATSAPP_DIGITS__',
  true,
  '__EMAIL__',
  '',
  'client_admin',
  'active',
  '__PHONE_NUMBER_ID__',
  true,
  'pro',
  30,
  '{
    "timezone": "__TIMEZONE__",
    "reminder_offset_minutes": 1440,
    "weekly": {
      "monday":    [["09:00", "18:00"]],
      "tuesday":   [["09:00", "18:00"]],
      "wednesday": [["09:00", "18:00"]],
      "thursday":  [["09:00", "18:00"]],
      "friday":    [["09:00", "18:00"]],
      "saturday":  [],
      "sunday":    []
    }
  }'::jsonb
)
ON CONFLICT (whatsapp_number) DO UPDATE SET
  name = EXCLUDED.name,
  is_active = true,
  status = 'active',
  phone_number_id = EXCLUDED.phone_number_id,
  whatsapp_connected = true,
  appointment_duration_minutes = EXCLUDED.appointment_duration_minutes,
  business_hours = EXCLUDED.business_hours,
  updated_at = now();

INSERT INTO agents (
  id, client_id, name, personality, tools, knowledge_base_refs, is_active
) VALUES (
  '__AGENT_UUID__',
  '__CLIENT_UUID__',
  '__AGENT_NAME__',
  $personality$
__PERSONALITY__
$personality$,
  '[
    {
      "name": "consultar_disponibilidad",
      "description": "Consulta horarios libres para un día (YYYY-MM-DD).",
      "endpoint": ""
    },
    {
      "name": "agendar_cita",
      "description": "Agenda una cita. fecha_hora local YYYY-MM-DDTHH:MM y nombre.",
      "endpoint": ""
    },
    {
      "name": "cancelar_cita",
      "description": "Cancela por ID de cita o teléfono del contacto.",
      "endpoint": ""
    }
  ]'::jsonb,
  '[]'::jsonb,
  true
)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  personality = EXCLUDED.personality,
  tools = EXCLUDED.tools,
  is_active = true,
  updated_at = now();

COMMIT;

-- Verificación
SELECT c.id, c.name, c.phone_number_id, c.business_hours->>'timezone' AS tz,
       a.name AS agent, jsonb_array_length(a.tools) AS tools
FROM clients c
LEFT JOIN agents a ON a.client_id = c.id
WHERE c.phone_number_id = '__PHONE_NUMBER_ID__'
   OR c.whatsapp_number = '__WHATSAPP_DIGITS__';
