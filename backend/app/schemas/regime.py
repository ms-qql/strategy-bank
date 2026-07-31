"""PROJ-22: Schemas für Regime-Analyse — Modellversionen, Zeitreihen, Trades, Auswertungen."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Modellversion ──────────────────────────────────────────────────────────

class RegimeModelVersionCreate(BaseModel):
    name: str
    course_source: str = "close"
    zscore_length: int = Field(default=75, ge=2)
    hma_length: int = Field(default=2, ge=1)
    confirmation_candles: int = Field(default=2, ge=1)
    upper_threshold: float
    lower_threshold: float


class RegimeModelVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    course_source: str
    zscore_length: int
    hma_length: int
    confirmation_candles: int
    upper_threshold: float
    lower_threshold: float
    created_at: datetime


# ── Zeitreihe ──────────────────────────────────────────────────────────────

class RegimeSeriesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider_symbol: str
    asset: str
    timeframe: str
    model_version_id: UUID
    model_version_name: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    bar_count: int = 0
    unavailable_count: int = 0
    last_refreshed_at: datetime | None = None


class RegimeBarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bar_time: datetime
    regime: str


# ── Import ─────────────────────────────────────────────────────────────────

class RegimeImportRequest(BaseModel):
    asset: str
    timeframe: str
    model_version_id: UUID
    bars: list[RegimeBarRead]


class RegimeImportResponse(BaseModel):
    series_id: UUID
    bars_inserted: int
    bars_skipped: int


class RegimeCoverageIssue(BaseModel):
    issue_type: str   # gap, overlapping_version, timeframe_mismatch
    detail: str


class RegimeSeriesDetailRead(RegimeSeriesRead):
    bars: list[RegimeBarRead] | None = None
    coverage_issues: list[RegimeCoverageIssue] = []


# ── Trades ─────────────────────────────────────────────────────────────────

class ResultTradeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hal_result_id: UUID
    direction: str
    entry_time: datetime
    exit_time: datetime
    net_pnl: float
    data_source: str
    created_at: datetime


class FetchTradesResponse(BaseModel):
    hal_result_id: UUID
    trades_count: int


# ── Regime-Auswertung ──────────────────────────────────────────────────────

class RegimeDetailRow(BaseModel):
    regime: str
    trade_count: int
    net_pnl: float
    max_drawdown_pct: float | None = None
    pnl_share_pct: float
    calmar_ratio: float | None = None
    sortino_ratio: float | None = None
    small_sample: bool = False


class RegimeEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hal_result_id: UUID
    series_id: UUID
    model_version_id: UUID
    model_version_name: str | None = None
    coverage_pct: float
    assignment_rule: str
    is_incomplete: bool
    total_result_pnl: float
    regime_details: list[RegimeDetailRow]
    regime_dominance: str | None = None  # name of dominant regime or None
    created_at: datetime
