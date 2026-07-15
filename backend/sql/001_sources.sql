-- PROJ-1: Quellenerfassung
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('text', 'markdown_file')),
    file_name TEXT,
    extraction_status TEXT NOT NULL DEFAULT 'noch nicht extrahiert'
        CHECK (extraction_status IN (
            'noch nicht extrahiert',
            'wird extrahiert',
            'extrahiert',
            'extrahiert, keine Treffer',
            'Extraktion fehlgeschlagen'
        )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sources_created_at ON sources (created_at DESC);
