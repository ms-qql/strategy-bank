-- PROJ-5: Credit-Gate
-- Erweitert batches um den unveränderlichen Credit-Snapshot, der bei der
-- Bestätigung miterfasst wird. Keine neue Tabelle — der Snapshot gehört
-- fachlich zum bestätigten Batch und wird danach nie geändert.

ALTER TABLE batches
    ADD COLUMN IF NOT EXISTS credit_max INTEGER,
    ADD COLUMN IF NOT EXISTS credit_balance INTEGER,
    ADD COLUMN IF NOT EXISTS credit_remaining INTEGER,
    ADD COLUMN IF NOT EXISTS credit_tier TEXT,
    ADD COLUMN IF NOT EXISTS credit_reset TEXT,
    ADD COLUMN IF NOT EXISTS credit_checked_at TIMESTAMPTZ;
