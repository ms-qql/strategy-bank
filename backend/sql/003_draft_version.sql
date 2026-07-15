-- PROJ-2: Versionsnummer für bereits angelegte Datenbanken.
ALTER TABLE strategy_drafts
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1);
