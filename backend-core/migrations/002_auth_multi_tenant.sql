-- ============================================================
-- Migración 002: Auth Multi-Tenant
-- Añade email, password_hash, role, status, phone_number_id,
-- whatsapp_connected y plan a la tabla `clients` para soportar
-- registro público, aprobación manual y login JWT por tenant.
-- Ejecutar en: Supabase SQL Editor
-- ============================================================

-- PRE-MIGRACIÓN (recomendado):
-- Si existen filas en `clients` sin email (email = ''), antes de
-- crear el UNIQUE INDEX ejecuta:
--   UPDATE clients
--   SET email = 'pre_' || id::text || '@migrate.local'
--   WHERE email = '';
-- Esto evita el violación del UNIQUE INDEX por filas legacy con
-- email vacío. El índice parcial `WHERE email <> ''` ya permite
-- múltiples filas con email vacío, pero conviene нормativizar.

ALTER TABLE clients
    ADD COLUMN email             TEXT NOT NULL DEFAULT '',
    ADD COLUMN password_hash     TEXT NOT NULL DEFAULT '',
    ADD COLUMN role              TEXT NOT NULL DEFAULT 'client_admin'
        CHECK (role IN ('superadmin', 'client_admin', 'client_user')),
    ADD COLUMN status            TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'active', 'inactive')),
    ADD COLUMN phone_number_id   TEXT NOT NULL DEFAULT '',
    ADD COLUMN whatsapp_connected BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN plan              TEXT NOT NULL DEFAULT 'free'
        CHECK (plan IN ('free', 'starter', 'pro', 'enterprise'));

-- Email único cuando no esté vacío (garantiza auth por email)
CREATE UNIQUE INDEX idx_clients_email_unique
    ON clients (email) WHERE email <> '';

-- Índices para listar pendientes / filtrar por role (admin)
CREATE INDEX idx_clients_status ON clients(status);
CREATE INDEX idx_clients_role   ON clients(role);

COMMENT ON COLUMN clients.email IS 'Email de login del cliente (único cuando no vacío). Normalizado a lowercase.';
COMMENT ON COLUMN clients.password_hash IS 'Hash bcrypt ($2a$|$2b$|$2y$), 60 chars. Nunca plain text.';
COMMENT ON COLUMN clients.role IS 'superadmin | client_admin | client_user';
COMMENT ON COLUMN clients.status IS 'pending -> approved -> active; inactive para rechazados/suspendidos.';
COMMENT ON COLUMN clients.phone_number_id IS 'Phone Number ID de Meta Cloud API (WABA central).';
COMMENT ON COLUMN clients.whatsapp_connected IS 'True si el WABA está conectado y operativo.';
COMMENT ON COLUMN clients.plan IS 'free | starter | pro | enterprise';