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
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'contacted', 'qualified', 'converted', 'lost')),
    notes TEXT DEFAULT '',
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
-- PostgREST: Grant all privileges to web_anon role
-- ============================================================

GRANT USAGE ON SCHEMA public TO web_anon;
GRANT ALL ON ALL TABLES IN SCHEMA public TO web_anon;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO web_anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO web_anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO web_anon;
