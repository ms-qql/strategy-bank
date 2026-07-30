"""PROJ-21: Schemas für HAL-Import, Ergebnis-Screening und Shortlist."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HalImportRunRead(BaseModel):
    id: UUID
    total_files: int
    status_imported: int
    status_unchanged: int
    status_updated: int
    status_failed: int
    created_at: datetime


class HalImportedFileRow(BaseModel):
    id: UUID
    import_run_id: UUID
    origin_path: str
    content_hash: str
    import_version: int
    processing_status: str
    error_message: str | None = None
    created_at: datetime


class HalImportFileResult(BaseModel):
    origin_path: str
    content_hash: str
    status: str  # importiert / unverändert / aktualisiert / fehlerhaft
    error_message: str | None = None
    strategy_name: str | None = None


class HalImportResponse(BaseModel):
    import_run_id: UUID
    total: int
    files: list[HalImportFileResult]


class HalAssignRequest(BaseModel):
    strategy_version_id: UUID | None = None


class HalResultRead(BaseModel):
    id: UUID
    imported_file_id: UUID
    strategy_name: str
    asset: str
    timeframe: str
    period_start: date
    period_end: date | None = None
    net_return_pct: float
    max_drawdown_pct: float
    trade_count: int
    sortino_ratio: float | None = None
    profit_factor: float | None = None
    sharpe_ratio: float | None = None
    win_rate_pct: float | None = None
    cagr_pct: float | None = None
    calmar_ratio: float | None = None
    report_link: str | None = None
    parameters: dict | list | None = None
    long_short_breakdown: dict | None = None
    direction: str | None = None
    fee_pct: float | None = None
    slippage_ticks: float | None = None
    sizing_model: str | None = None
    strategy_version_id: UUID | None = None
    assignment_origin: str | None = None
    import_version: int
    created_at: datetime


class HalUnassignedRead(HalResultRead):
    import_origin_path: str
    suggested_version_id: UUID | None = None
    suggested_version_name: str | None = None


class ShortlistEntry(BaseModel):
    strategy_version_id: UUID
    created_at: datetime


SUCCESS_GROUP_CALMAR_MIN = 0.8
SUCCESS_GROUP_SORTINO_MIN = 0.5
SUCCESS_GROUP_MIN_TRADES_PER_YEAR = 6
