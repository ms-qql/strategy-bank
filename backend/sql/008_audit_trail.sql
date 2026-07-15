-- PROJ-8: Audit-Trail
-- Append-only Audit-Eintrag je Run. Entsteht bei Batch-Bestätigung,
-- wird von PROJ-6 ergänzt und finalisiert. Kein UPDATE/DELETE nach
-- Finalisierung.

CREATE TABLE IF NOT EXISTS run_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL UNIQUE REFERENCES runs (id),
    batch_id UUID NOT NULL REFERENCES batches (id),
    strategy_snapshot JSONB NOT NULL,
    profile_snapshot JSONB NOT NULL,
    provider_symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE,
    direction_mode TEXT NOT NULL CHECK (direction_mode IN ('kombiniert', 'long-only', 'short-only')),
    run_kind TEXT NOT NULL CHECK (run_kind IN ('standard', 'holdout', 'forward_test')),
    credit_max INTEGER,
    credit_balance INTEGER,
    credit_remaining INTEGER,
    credit_tier TEXT,
    credit_reset TEXT,
    credit_checked_at TIMESTAMPTZ,
    agent_runtime TEXT,
    model TEXT,
    prompt_version TEXT,
    executor_version TEXT,
    mcp_action TEXT,
    external_job_id TEXT,
    external_result_id TEXT,
    engine_info TEXT,
    data_freshness TEXT,
    report_link TEXT,
    report_available BOOLEAN NOT NULL DEFAULT false,
    raw_response JSONB,
    raw_response_available BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    finalized_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_run_audits_run_id ON run_audits (run_id);
CREATE INDEX IF NOT EXISTS idx_run_audits_batch_id ON run_audits (batch_id);
