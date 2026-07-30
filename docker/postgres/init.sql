-- ============================================================
-- Init script: PostgREST auth roles + schema + migrations
-- ============================================================
-- NOTA (Fase 0.2 saneamiento): el rol "authenticator" YA NO se crea aquí
-- con password hardcodeada. Se crea en 00-create-roles.sh (que corre antes
-- que este archivo, por orden alfabético en docker-entrypoint-initdb.d/)
-- usando la variable de entorno POSTGREST_AUTHENTICATOR_PASSWORD.
-- Ver docker/postgres/00-create-roles.sh.

CREATE ROLE web_anon WITH NOLOGIN;
GRANT web_anon TO authenticator;

-- Extension pgvector para RAG
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- Migracion 001: Tablas core
-- ============================================================

CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    business_type TEXT NOT NULL CHECK (business_type IN (
        'peluqueria', 'bar', 'restaurante', 'contador',
        'fonatero', 'tienda', 'gimnasio', 'clinica', 'otro'
    )),
    whatsapp_number TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_clients_whatsapp ON clients(whatsapp_number);
CREATE INDEX idx_clients_active ON clients(is_active) WHERE is_active = true;
CREATE INDEX idx_clients_business_type ON clients(business_type);

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    personality TEXT NOT NULL CHECK (length(personality) >= 10),
    tools JSONB NOT NULL DEFAULT '[]'::jsonb,
    knowledge_base_refs TEXT[] NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_agents_client ON agents(client_id);
CREATE INDEX idx_agents_active ON agents(is_active) WHERE is_active = true;

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    wa_phone_number TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conversations_client ON conversations(client_id);
CREATE INDEX idx_conversations_phone ON conversations(wa_phone_number);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created ON messages(conversation_id, created_at);

CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_kb_client ON knowledge_base(client_id);
CREATE INDEX idx_kb_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Funcion updated_at
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_clients_updated BEFORE UPDATE ON clients FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_agents_updated BEFORE UPDATE ON agents FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_conversations_updated BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================================
-- Migracion 002: Auth multi-tenant
-- ============================================================

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

CREATE UNIQUE INDEX idx_clients_email_unique ON clients (email) WHERE email <> '';
CREATE INDEX idx_clients_status ON clients(status);
CREATE INDEX idx_clients_role ON clients(role);

-- ============================================================
-- Tablas adicionales (leads, email_logs, feedback, landing_submissions)
-- ============================================================

CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    source TEXT DEFAULT 'whatsapp',
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'contacted', 'qualified', 'converted', 'lost', 'interested', 'not_interested', 'archived')),
    score INTEGER NOT NULL DEFAULT 0,
    notes TEXT DEFAULT '',
    last_contacted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_leads_updated BEFORE UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TABLE email_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    to_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'sent' CHECK (status IN ('sent', 'failed', 'bounced', 'opened')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE landing_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    landing_slug TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_landing_submissions_slug ON landing_submissions(landing_slug);
CREATE INDEX idx_landing_submissions_client_date ON landing_submissions(client_id, created_at DESC);

-- Columnas de landing en clients
ALTER TABLE clients
    ADD COLUMN landing_slug TEXT NOT NULL DEFAULT '',
    ADD COLUMN landing_title TEXT NOT NULL DEFAULT '',
    ADD COLUMN landing_description TEXT NOT NULL DEFAULT '',
    ADD COLUMN landing_active BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN landing_primary_color TEXT NOT NULL DEFAULT '#3B82F6',
    ADD COLUMN landing_auto_reply TEXT NOT NULL DEFAULT '';

CREATE UNIQUE INDEX idx_clients_landing_slug ON clients (landing_slug) WHERE landing_slug <> '';

-- ============================================================
-- Migracion 003: Agenda (appointments + business_hours)
-- ============================================================

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

CREATE INDEX idx_appointments_client_starts ON appointments(client_id, starts_at);
CREATE INDEX idx_appointments_client_status ON appointments(client_id, status);
CREATE INDEX idx_appointments_client_phone ON appointments(client_id, contact_phone);
CREATE INDEX idx_appointments_reminder ON appointments(starts_at)
    WHERE reminder_sent_at IS NULL AND status IN ('pending', 'confirmed');

CREATE TRIGGER trg_appointments_updated
    BEFORE UPDATE ON appointments
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON appointments FOR ALL USING (true);

-- ============================================================
-- Migracion 004: status en messages
-- ============================================================

ALTER TABLE messages
    ADD COLUMN status TEXT NOT NULL DEFAULT 'received'
        CHECK (status IN ('received', 'sent', 'failed', 'skipped'));

-- ============================================================
-- Migracion 005: credenciales WhatsApp cifradas por tenant
-- ============================================================

ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS whatsapp_access_token_encrypted TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_clients_phone_number_id
    ON clients (phone_number_id)
    WHERE phone_number_id <> '';

-- ============================================================
-- PostgREST: Grant all privileges to web_anon role
-- ============================================================

GRANT USAGE ON SCHEMA public TO web_anon;
GRANT ALL ON ALL TABLES IN SCHEMA public TO web_anon;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO web_anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO web_anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO web_anon;
