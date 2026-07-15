-- PROJ-2: KI-Extraktion
CREATE TABLE IF NOT EXISTS extraction_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources (id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'läuft'
        CHECK (status IN ('läuft', 'abgeschlossen', 'keine Treffer', 'fehlgeschlagen')),
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_extraction_runs_source_id ON extraction_runs (source_id);
CREATE INDEX IF NOT EXISTS idx_extraction_runs_started_at ON extraction_runs (started_at DESC);

CREATE TABLE IF NOT EXISTS strategy_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_run_id UUID NOT NULL REFERENCES extraction_runs (id) ON DELETE CASCADE,
    source_hash TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    name TEXT NOT NULL,
    thesis TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN (
        'Trendfolge', 'Mean Reversion', 'Breakout', 'Volatilität', 'Momentum',
        'Saison/Zeit', 'Preis-/Candlestick-Muster', 'Hybrid', 'Sonstige'
    )),
    direction TEXT NOT NULL CHECK (direction IN ('kombiniert', 'long-only', 'short-only')),
    entry_rule TEXT,
    exit_rule TEXT,
    warmup_requirement TEXT,
    simultaneous_entry_exit_behavior TEXT,
    reversal_behavior TEXT,
    status TEXT NOT NULL DEFAULT 'Entwurf'
        CHECK (status IN ('Entwurf', 'nicht testbar', 'gesperrt (unvollständig)')),
    status_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_strategy_drafts_run_id ON strategy_drafts (extraction_run_id);

CREATE TABLE IF NOT EXISTS draft_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL REFERENCES strategy_drafts (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    unit TEXT,
    allowed_range TEXT,
    is_proposal BOOLEAN NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_draft_parameters_draft_id ON draft_parameters (draft_id);

CREATE TABLE IF NOT EXISTS draft_source_citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL REFERENCES strategy_drafts (id) ON DELETE CASCADE,
    rule_field TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    line_reference TEXT
);

CREATE INDEX IF NOT EXISTS idx_draft_citations_draft_id ON draft_source_citations (draft_id);

CREATE TABLE IF NOT EXISTS draft_open_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL REFERENCES strategy_drafts (id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    reasoning TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_draft_open_questions_draft_id ON draft_open_questions (draft_id);
