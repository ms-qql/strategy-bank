-- PROJ-12: Automatische Backtest-Ausführung — Worker-Heartbeat
-- Genau ein Datensatz: Identität + letzter Lebensnachweis + Fehler.
-- Ein aktueller Lebensnachweis = Worker verfügbar, Start erlaubt.

CREATE TABLE IF NOT EXISTS worker_heartbeat (
    worker_id TEXT PRIMARY KEY DEFAULT 'strategy-bank-worker-v1',
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_error_category TEXT,
    last_error_at TIMESTAMPTZ
);

INSERT INTO worker_heartbeat (worker_id, last_heartbeat)
VALUES ('strategy-bank-worker-v1', '2000-01-01'::timestamptz)
ON CONFLICT (worker_id) DO NOTHING;
