-- PROJ-3: Verifizierung und Versionierung

-- (a) strategy_drafts erweitern
ALTER TABLE strategy_drafts
    ADD COLUMN IF NOT EXISTS family_id UUID,
    ADD COLUMN IF NOT EXISTS parent_version_id UUID,
    ADD COLUMN IF NOT EXISTS original_snapshot JSONB,
    ADD COLUMN IF NOT EXISTS frozen_at TIMESTAMPTZ;

-- family_id beim ersten Entwurf = dessen eigene ID
UPDATE strategy_drafts SET family_id = id WHERE family_id IS NULL;

ALTER TABLE strategy_drafts ALTER COLUMN family_id SET NOT NULL;

-- Status-Check erweitern: 'freigegeben' hinzu
ALTER TABLE strategy_drafts
    DROP CONSTRAINT IF EXISTS strategy_drafts_status_check;

ALTER TABLE strategy_drafts
    ADD CONSTRAINT strategy_drafts_status_check CHECK (
        status IN ('Entwurf', 'nicht testbar', 'gesperrt (unvollständig)', 'freigegeben')
    );

-- (b) strategy_versions: append-only Snapshot einer freigegebenen Strategie
CREATE TABLE IF NOT EXISTS strategy_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL,
    family_id UUID NOT NULL,
    version_number INTEGER NOT NULL CHECK (version_number >= 1),
    source_id UUID NOT NULL,
    source_hash TEXT NOT NULL,
    extraction_model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    snapshot JSONB NOT NULL,
    frozen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (family_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_strategy_versions_family_id ON strategy_versions (family_id);
CREATE INDEX IF NOT EXISTS idx_strategy_versions_draft_id ON strategy_versions (draft_id);

-- Kein UPDATE/DELETE auf freigegebene Versionen
REVOKE UPDATE, DELETE ON strategy_versions FROM PUBLIC;

-- (c) version_parameters: zum Freeze-Zeitpunkt gültige Parameter
CREATE TABLE IF NOT EXISTS version_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID NOT NULL REFERENCES strategy_versions (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    unit TEXT,
    allowed_range TEXT
);

CREATE INDEX IF NOT EXISTS idx_version_parameters_version_id ON version_parameters (version_id);

REVOKE UPDATE, DELETE ON version_parameters FROM PUBLIC;
