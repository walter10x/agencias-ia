-- 005_client_whatsapp_credentials.sql
-- Fase 3 (3.1): credenciales de WhatsApp Cloud API por tenant.
--
-- Decisión: la columna `phone_number_id` YA existe en `clients` desde
-- 002_auth_multi_tenant.sql, por lo que se REUTILIZA en lugar de crear
-- una columna duplicada `whatsapp_phone_number_id`. Esta migración añade:
--   1. El access token de Meta CIFRADO (Fernet simétrico, clave en la
--      variable de entorno CREDENTIALS_ENCRYPTION_KEY — nunca en claro).
--   2. Un índice parcial sobre phone_number_id para el routing
--      multi-tenant del webhook entrante (lookup por metadata.phone_number_id).

ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS whatsapp_access_token_encrypted TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_clients_phone_number_id
    ON clients (phone_number_id)
    WHERE phone_number_id <> '';

COMMENT ON COLUMN clients.whatsapp_access_token_encrypted IS
    'Access token de Meta Cloud API cifrado con Fernet (clave: CREDENTIALS_ENCRYPTION_KEY). Cadena vacía = el tenant no tiene credenciales propias (se usa el fallback global de env si existe).';
