-- PROJ-6: Queue und trader.dev-Ausführung
-- Erweitert runs und legt backtest_executions als Provider-Speicher an.

-- (a) batches: erweiterte Status
ALTER TABLE batches
    DROP CONSTRAINT IF EXISTS batches_status_check;
ALTER TABLE batches
    ADD CONSTRAINT batches_status_check CHECK (
        status IN ('entwurf', 'bestätigt', 'in_ausfuehrung')
    );

-- (b) runs: erweiterte Status und Laufzeitfelder
ALTER TABLE runs
    ALTER COLUMN status TYPE TEXT,
    DROP CONSTRAINT IF EXISTS runs_status_check;

ALTER TABLE runs
    ADD CONSTRAINT runs_status_check CHECK (
        status IN ('geplant', 'bestätigt', 'in_queue', 'läuft',
                   'erfolgreich', 'fehlgeschlagen', 'abgebrochen')
    ),
    ADD COLUMN IF NOT EXISTS error_message TEXT,
    ADD COLUMN IF NOT EXISTS error_category TEXT,
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS backtest_execution_id UUID;

CREATE INDEX IF NOT EXISTS idx_runs_status ON runs (batch_id, status);

-- (b) backtest_executions: eine Zeile je Idempotency-Key
CREATE TABLE IF NOT EXISTS backtest_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key TEXT NOT NULL UNIQUE,
    strategy_version_id UUID NOT NULL REFERENCES strategy_versions (id),
    provider_symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE,
    direction_mode TEXT NOT NULL
        CHECK (direction_mode IN ('kombiniert', 'long-only', 'short-only')),
    backtest_profile_version_id UUID NOT NULL REFERENCES backtest_profiles (id),
    evaluation_type TEXT NOT NULL DEFAULT 'standard'
        CHECK (evaluation_type IN ('standard', 'holdout', 'forward_test')),
    pine_source TEXT NOT NULL,
    executor_fingerprint TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 1
        CHECK (attempt IN (1, 2)),
    external_job_id TEXT,
    external_result_id TEXT,
    provider_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (provider_status IN ('pending', 'submitted', 'running', 'completed', 'failed')),
    provider_warnings JSONB,
    backtest_result JSONB,
    report_link TEXT,
    report_available BOOLEAN NOT NULL DEFAULT false,
    cascade_correction_applied BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_backtest_execs_idempotency_key
    ON backtest_executions (idempotency_key);
CREATE INDEX IF NOT EXISTS idx_backtest_execs_strategy_version_id
    ON backtest_executions (strategy_version_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'runs'::regclass
          AND conname = 'fk_runs_backtest_execution_id'
    ) THEN
        ALTER TABLE runs
            ADD CONSTRAINT fk_runs_backtest_execution_id
                FOREIGN KEY (backtest_execution_id) REFERENCES backtest_executions (id);
    END IF;
END $$;
