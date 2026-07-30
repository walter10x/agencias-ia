-- CRM ensure lead / mark_contacted necesitan estas columnas
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS last_contacted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS score INTEGER NOT NULL DEFAULT 0;
