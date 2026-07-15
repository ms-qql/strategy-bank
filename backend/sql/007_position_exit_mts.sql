-- PROJ-10: Positions-, Exit- und Crypto-MTS-Kompatibilitätsmodell

ALTER TABLE strategy_drafts
    ADD COLUMN IF NOT EXISTS position_mode TEXT,
    ADD COLUMN IF NOT EXISTS position_mode_confirmed BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS exit_rule_origin TEXT,
    ADD COLUMN IF NOT EXISTS mts_compatibility TEXT,
    ADD COLUMN IF NOT EXISTS mts_confirmed BOOLEAN NOT NULL DEFAULT false;

-- position_mode: signal_reversal | entry_exit (NULL = noch nicht gewählt)
-- exit_rule_origin: source | system_default | user (NULL = nicht aufgelöst)
-- mts_compatibility: continuous | discrete | unclear (NULL = noch nicht gewählt)

ALTER TABLE strategy_drafts
    DROP CONSTRAINT IF EXISTS strategy_drafts_status_check;

ALTER TABLE strategy_drafts
    ADD CONSTRAINT strategy_drafts_status_check CHECK (
        status IN ('Entwurf', 'nicht testbar', 'gesperrt (unvollständig)', 'freigegeben')
    );
