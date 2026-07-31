-- PROJ-23: Erfolgsfaktorenanalyse
-- Analyseläufe (Momentaufnahmen) und eingefrorene Lauf-Zeilen.

CREATE TABLE IF NOT EXISTS analysis_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comparison_group TEXT NOT NULL,
    success_definition JSONB NOT NULL,
    total_analyzed INTEGER NOT NULL,
    total_excluded INTEGER NOT NULL,
    excluded_reasons JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analysis_run_rows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs (id) ON DELETE CASCADE,
    hal_result_id UUID NOT NULL,
    strategy_name TEXT NOT NULL,
    strategy_version_id UUID,
    calmar_ratio NUMERIC,
    sortino_ratio NUMERIC,
    trades_per_year NUMERIC,
    is_success BOOLEAN NOT NULL,
    indicators JSONB NOT NULL DEFAULT '[]',
    indicator_count INTEGER NOT NULL DEFAULT 0,
    parameter_count INTEGER NOT NULL DEFAULT 0,
    entry_archetype TEXT NOT NULL DEFAULT 'nicht verfügbar',
    exit_archetype TEXT NOT NULL DEFAULT 'nicht verfügbar',
    category TEXT,
    direction TEXT,
    mts_compatibility TEXT
);

CREATE INDEX IF NOT EXISTS idx_analysis_run_rows_run_id ON analysis_run_rows (analysis_run_id);
