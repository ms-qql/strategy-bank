from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class ResultRow(BaseModel):
    run_id: UUID
    strategy_id: UUID | None = None
    strategy_name: str
    strategy_version_number: int | None = None
    strategy_family_id: UUID | None = None
    category: str | None = None
    instrument: str
    direction: str | None = None
    result_type: str
    status: str | None = None
    error_message: str | None = None

    profile_id: UUID | None = None
    profile_name: str | None = None
    profile_version_number: int | None = None
    profile_family_id: UUID | None = None

    timeframe: str
    period_start: date
    period_end: date | None = None

    net_profit_pct: float | None = None
    cagr_pct: float | None = None
    trade_count: int | None = None
    max_drawdown_pct: float | None = None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    profit_factor: float | None = None
    calmar_ratio: float | None = None

    trades_per_year: float | None = None
    is_comparable: bool = False
    success_group: bool = False
    shortlisted: bool = False

    report_link: str | None = None
    incomplete: bool = False
    low_activity: bool = False

    import_origin_path: str | None = None
    import_hash: str | None = None
    import_version: int | None = None
    import_created_at: datetime | None = None
    strategy_version_status: str | None = None
    source_name: str | None = None
    mts_compatibility: str | None = None
    robustness_status: str | None = None

    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
