-- PROJ-4: Batch-Konfiguration

-- (a) backtest_profiles: append-only Snapshot je Profilversion (Muster wie
-- strategy_versions) — jede Änderung legt eine neue Version derselben
-- family_id an, nie ein Überschreiben.
CREATE TABLE IF NOT EXISTS backtest_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL,
    version_number INTEGER NOT NULL CHECK (version_number >= 1),
    name TEXT NOT NULL,
    timezone_session TEXT NOT NULL,
    signal_timing TEXT NOT NULL DEFAULT 'Schlusskurs',
    fill_timing TEXT NOT NULL DEFAULT 'nächster verfügbarer Bar-Open',
    order_type TEXT NOT NULL,
    fee_pct NUMERIC NOT NULL DEFAULT 0.06,
    slippage_ticks NUMERIC NOT NULL DEFAULT 2,
    starting_capital NUMERIC NOT NULL DEFAULT 10000,
    quote_currency TEXT NOT NULL DEFAULT 'USD',
    position_sizing TEXT NOT NULL,
    compounding_rule TEXT NOT NULL,
    leverage NUMERIC NOT NULL DEFAULT 1,
    pyramiding BOOLEAN NOT NULL DEFAULT false,
    max_open_positions INTEGER NOT NULL DEFAULT 1,
    missing_bars_handling TEXT NOT NULL,
    corporate_actions_handling TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (family_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_backtest_profiles_family_id ON backtest_profiles (family_id);

REVOKE UPDATE, DELETE ON backtest_profiles FROM PUBLIC;

-- (b) batches: Entwurf bis Bestätigung frei änderbar, danach gesperrt.
CREATE TABLE IF NOT EXISTS batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backtest_profile_id UUID NOT NULL REFERENCES backtest_profiles (id),
    timeframe TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE,
    run_kind TEXT NOT NULL DEFAULT 'standard'
        CHECK (run_kind IN ('standard', 'holdout', 'forward_test')),
    status TEXT NOT NULL DEFAULT 'entwurf' CHECK (status IN ('entwurf', 'bestätigt')),
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_batches_backtest_profile_id ON batches (backtest_profile_id);

-- (c) Instrumente, Strategieversionen und Richtungsmodi je Batch (nur
-- änderbar solange batches.status = 'entwurf' — auf Anwendungsebene geprüft).
CREATE TABLE IF NOT EXISTS batch_instruments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES batches (id) ON DELETE CASCADE,
    provider_symbol TEXT NOT NULL,
    label TEXT
);

CREATE INDEX IF NOT EXISTS idx_batch_instruments_batch_id ON batch_instruments (batch_id);

CREATE TABLE IF NOT EXISTS batch_strategy_versions (
    batch_id UUID NOT NULL REFERENCES batches (id) ON DELETE CASCADE,
    strategy_version_id UUID NOT NULL REFERENCES strategy_versions (id),
    PRIMARY KEY (batch_id, strategy_version_id)
);

CREATE TABLE IF NOT EXISTS batch_direction_modes (
    batch_id UUID NOT NULL REFERENCES batches (id) ON DELETE CASCADE,
    mode TEXT NOT NULL CHECK (mode IN ('kombiniert', 'long-only', 'short-only')),
    PRIMARY KEY (batch_id, mode)
);

-- (d) runs: entsteht erst bei „Batch bestätigen" (kartesisches Produkt aus
-- Strategieversionen × Instrumenten × Richtungsmodi). Zeilen sind append-only
-- (kein DELETE, siehe PROJ-8 Audit-Trail); der status wird von PROJ-6 weiter
-- aktualisiert (Queue/Ausführung), daher kein REVOKE UPDATE hier.
CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES batches (id),
    strategy_version_id UUID NOT NULL REFERENCES strategy_versions (id),
    provider_symbol TEXT NOT NULL,
    direction_mode TEXT NOT NULL CHECK (direction_mode IN ('kombiniert', 'long-only', 'short-only')),
    run_kind TEXT NOT NULL CHECK (run_kind IN ('standard', 'holdout', 'forward_test')),
    status TEXT NOT NULL DEFAULT 'geplant',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_runs_batch_id ON runs (batch_id);
CREATE INDEX IF NOT EXISTS idx_runs_strategy_version_id ON runs (strategy_version_id);

REVOKE DELETE ON runs FROM PUBLIC;

-- (e) family_holdout_status: markiert, sobald der historische Holdout für
-- eine Strategie-Familie erstmals ausgewertet wurde (dann für alle
-- Nachfolgeversionen "bereits verwendet").
CREATE TABLE IF NOT EXISTS family_holdout_status (
    family_id UUID PRIMARY KEY,
    consumed_at TIMESTAMPTZ
);
