-- PROJ-22: Regime-Analyse
-- Modellversionen, Kursbars, Regime-Zeitreihen, Trades und Auswertungen.

CREATE TABLE IF NOT EXISTS regime_model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    course_source TEXT NOT NULL DEFAULT 'close',
    zscore_length INTEGER NOT NULL CHECK (zscore_length >= 2),
    hma_length INTEGER NOT NULL CHECK (hma_length >= 1),
    confirmation_candles INTEGER NOT NULL CHECK (confirmation_candles >= 1),
    upper_threshold NUMERIC NOT NULL,
    lower_threshold NUMERIC NOT NULL,
    CHECK (lower_threshold < upper_threshold),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_regime_model_versions_name ON regime_model_versions (name);

CREATE TABLE IF NOT EXISTS price_bars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    bar_time TIMESTAMPTZ NOT NULL,
    open NUMERIC NOT NULL,
    high NUMERIC NOT NULL,
    low NUMERIC NOT NULL,
    close NUMERIC NOT NULL,
    UNIQUE (asset, timeframe, bar_time),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_price_bars_asset_timeframe ON price_bars (asset, timeframe);
CREATE INDEX IF NOT EXISTS idx_price_bars_bar_time ON price_bars (bar_time);

CREATE TABLE IF NOT EXISTS regime_series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_symbol TEXT NOT NULL DEFAULT 'BYBIT:BTCUSDT.P',
    asset TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    model_version_id UUID NOT NULL REFERENCES regime_model_versions (id),
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    last_refreshed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider_symbol, asset, timeframe, model_version_id)
);

CREATE INDEX IF NOT EXISTS idx_regime_series_model_version ON regime_series (model_version_id);
CREATE INDEX IF NOT EXISTS idx_regime_series_asset_timeframe ON regime_series (asset, timeframe);

CREATE TABLE IF NOT EXISTS regime_bars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    series_id UUID NOT NULL REFERENCES regime_series (id),
    bar_time TIMESTAMPTZ NOT NULL,
    regime TEXT NOT NULL CHECK (regime IN ('bullish', 'bearish', 'sideways', 'nicht verfügbar')),
    UNIQUE (series_id, bar_time)
);

CREATE INDEX IF NOT EXISTS idx_regime_bars_series_time ON regime_bars (series_id, bar_time);

CREATE TABLE IF NOT EXISTS result_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hal_result_id UUID NOT NULL REFERENCES hal_results (id) ON DELETE CASCADE,
    direction TEXT NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ NOT NULL,
    net_pnl NUMERIC NOT NULL,
    data_source TEXT NOT NULL DEFAULT 'trader_dev',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_result_trades_hal_result_id ON result_trades (hal_result_id);
CREATE INDEX IF NOT EXISTS idx_result_trades_entry_time ON result_trades (entry_time);
CREATE UNIQUE INDEX IF NOT EXISTS uq_result_trades_entry_per_result ON result_trades (hal_result_id, direction, entry_time, exit_time);

CREATE TABLE IF NOT EXISTS regime_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hal_result_id UUID NOT NULL REFERENCES hal_results (id) ON DELETE CASCADE,
    series_id UUID NOT NULL REFERENCES regime_series (id),
    model_version_id UUID NOT NULL REFERENCES regime_model_versions (id),
    coverage_pct NUMERIC NOT NULL DEFAULT 0,
    assignment_rule TEXT NOT NULL DEFAULT 'entry_bar_regime',
    is_incomplete BOOLEAN NOT NULL DEFAULT false,
    total_result_pnl NUMERIC NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_regime_evaluations_hal_result_id ON regime_evaluations (hal_result_id);
CREATE INDEX IF NOT EXISTS idx_regime_evaluations_model_version ON regime_evaluations (model_version_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_regime_eval_result_model ON regime_evaluations (hal_result_id, model_version_id);

CREATE TABLE IF NOT EXISTS regime_eval_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id UUID NOT NULL REFERENCES regime_evaluations (id) ON DELETE CASCADE,
    regime TEXT NOT NULL CHECK (regime IN ('bullish', 'bearish', 'sideways', 'ohne Regimezuordnung')),
    trade_count INTEGER NOT NULL DEFAULT 0,
    net_pnl NUMERIC NOT NULL DEFAULT 0,
    max_drawdown_pct NUMERIC,
    pnl_share_pct NUMERIC NOT NULL DEFAULT 0,
    calmar_ratio NUMERIC,
    sortino_ratio NUMERIC,
    small_sample BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_regime_eval_details_eval_id ON regime_eval_details (evaluation_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_regime_eval_detail_regime ON regime_eval_details (evaluation_id, regime);
