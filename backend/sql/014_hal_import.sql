-- PROJ-21: HAL-Import und Ergebnis-Screening
-- Tabellen für Import, Ergebnisauswertung und Shortlist.

CREATE TABLE IF NOT EXISTS hal_import_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    total_files INTEGER NOT NULL DEFAULT 0,
    status_imported INTEGER NOT NULL DEFAULT 0,
    status_unchanged INTEGER NOT NULL DEFAULT 0,
    status_updated INTEGER NOT NULL DEFAULT 0,
    status_failed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hal_imported_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_run_id UUID NOT NULL REFERENCES hal_import_runs (id),
    origin_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    import_version INTEGER NOT NULL DEFAULT 1,
    is_current BOOLEAN NOT NULL DEFAULT true,
    processing_status TEXT NOT NULL DEFAULT 'importiert'
        CHECK (processing_status IN ('importiert', 'unverändert', 'aktualisiert', 'fehlerhaft')),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hal_imported_files_import_run_id ON hal_imported_files (import_run_id);
CREATE INDEX IF NOT EXISTS idx_hal_imported_files_origin_path ON hal_imported_files (origin_path);
CREATE UNIQUE INDEX IF NOT EXISTS uq_hal_imported_files_path_hash_version ON hal_imported_files (origin_path, content_hash, import_version);

CREATE TABLE IF NOT EXISTS hal_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    imported_file_id UUID NOT NULL REFERENCES hal_imported_files (id),
    strategy_name TEXT NOT NULL,
    asset TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE,
    net_return_pct NUMERIC NOT NULL,
    max_drawdown_pct NUMERIC NOT NULL,
    trade_count INTEGER NOT NULL,
    sortino_ratio NUMERIC,
    profit_factor NUMERIC,
    sharpe_ratio NUMERIC,
    win_rate_pct NUMERIC,
    cagr_pct NUMERIC,
    calmar_ratio NUMERIC,
    report_link TEXT,
    parameters JSONB,
    long_short_breakdown JSONB,
    pine_code TEXT,
    direction TEXT,
    fee_pct NUMERIC,
    slippage_ticks NUMERIC,
    sizing_model TEXT,
    raw_extracted JSONB,
    strategy_version_id UUID REFERENCES strategy_versions (id),
    assignment_origin TEXT
        CHECK (assignment_origin IS NULL OR assignment_origin IN ('file_identifier', 'suggestion_accepted', 'manual')),
    import_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hal_results_imported_file_id ON hal_results (imported_file_id);
CREATE INDEX IF NOT EXISTS idx_hal_results_strategy_version_id ON hal_results (strategy_version_id);
CREATE INDEX IF NOT EXISTS idx_hal_results_asset_timeframe ON hal_results (asset, timeframe);
CREATE INDEX IF NOT EXISTS idx_hal_results_strategy_name ON hal_results (strategy_name);

CREATE TABLE IF NOT EXISTS shortlist (
    strategy_version_id UUID PRIMARY KEY REFERENCES strategy_versions (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
