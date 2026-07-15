from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BacktestProfileWrite(BaseModel):
    name: str = Field(min_length=1)
    timezone_session: str = Field(min_length=1)
    signal_timing: str = "Schlusskurs"
    fill_timing: str = "nächster verfügbarer Bar-Open"
    order_type: str = Field(min_length=1)
    fee_pct: float = 0.06
    slippage_ticks: float = 2
    starting_capital: float = 10000
    quote_currency: str = "USD"
    position_sizing: str = Field(min_length=1)
    compounding_rule: str = Field(min_length=1)
    leverage: float = 1
    pyramiding: bool = False
    max_open_positions: int = 1
    missing_bars_handling: str = Field(min_length=1)
    corporate_actions_handling: str = Field(min_length=1)


class BacktestProfileRead(BacktestProfileWrite):
    id: UUID
    family_id: UUID
    version_number: int
    created_at: datetime


class InstrumentIn(BaseModel):
    provider_symbol: str = Field(min_length=1)
    label: str | None = None


class BatchCreate(BaseModel):
    backtest_profile_id: UUID
    strategy_version_ids: list[UUID] = Field(min_length=1)
    instruments: list[InstrumentIn] | None = None
    direction_modes: list[str] | None = None
    timeframe: str | None = None
    period_start: date | None = None
    period_end: date | None = None


class HoldoutBatchCreate(BaseModel):
    backtest_profile_id: UUID
    instruments: list[InstrumentIn] | None = None
    direction_modes: list[str] | None = None
    timeframe: str | None = None


class BatchUpdate(BaseModel):
    backtest_profile_id: UUID | None = None
    strategy_version_ids: list[UUID] | None = None
    instruments: list[InstrumentIn] | None = None
    direction_modes: list[str] | None = None
    timeframe: str | None = None
    period_start: date | None = None
    period_end: date | None = None


class InstrumentRead(BaseModel):
    provider_symbol: str
    label: str | None


class BatchRead(BaseModel):
    id: UUID
    backtest_profile_id: UUID
    timeframe: str
    period_start: date
    period_end: date | None
    run_kind: str
    status: str
    confirmed_at: datetime | None
    created_at: datetime
    strategy_version_ids: list[UUID]
    instruments: list[InstrumentRead]
    direction_modes: list[str]
    credit_max: int | None = None
    credit_balance: int | None = None
    credit_remaining: int | None = None
    credit_tier: str | None = None
    credit_reset: str | None = None
    credit_checked_at: datetime | None = None


class BatchConfirmIn(BaseModel):
    credit_max: int = Field(ge=1)


class CreditStatus(BaseModel):
    planned_actions: int
    credit_balance: int
    credit_remaining: int
    tier: str
    reset: str
    blocked: bool
    block_reason: str | None = None


class PreviewRun(BaseModel):
    strategy_version_id: UUID
    provider_symbol: str
    direction_mode: str


class BacktestMetrics(BaseModel):
    """Extrahiert aus der trader.dev-Antwort. Alle Felder optional, da nicht
    jeder Run Kennzahlen liefert (Null bei keinen Trades, nicht berechenbaren
    Werten)."""
    net_profit_pct: float | None = None
    profit_factor: float | None = None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    max_drawdown_pct: float | None = None
    win_rate_pct: float | None = None
    trade_count: int | None = None


class RunRead(BaseModel):
    id: UUID
    batch_id: UUID
    strategy_version_id: UUID
    provider_symbol: str
    direction_mode: str
    run_kind: str
    status: str
    error_message: str | None = None
    error_category: str | None = None
    backtest_metrics: BacktestMetrics | None = None
    backtest_job_id: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class RunSummary(BaseModel):
    total: int
    erfolgreich: int
    fehlgeschlagen: int
    offen: int
    abgebrochen: int


class BatchRunsResponse(BaseModel):
    batch_status: str
    runs: list[RunRead]
    summary: RunSummary


class RetryCreditCheckResponse(BaseModel):
    ok: bool
    reason: str | None = None


class RunCreate(BaseModel):
    strategy_version_id: UUID
    provider_symbol: str
    direction_mode: str
    run_kind: str = "standard"


class HoldoutStatusRead(BaseModel):
    family_id: UUID
    consumed: bool
    consumed_at: datetime | None
