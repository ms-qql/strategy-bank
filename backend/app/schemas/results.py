from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class ResultRow(BaseModel):
    run_id: UUID
    strategy_id: UUID
    strategy_name: str
    strategy_version_number: int
    strategy_family_id: UUID
    category: str
    instrument: str
    direction: str
    result_type: str
    status: str
    error_message: str | None = None

    profile_id: UUID
    profile_name: str
    profile_version_number: int
    profile_family_id: UUID

    timeframe: str
    period_start: date
    period_end: date | None = None

    net_profit_pct: float | None = None
    cagr_pct: float | None = None
    trade_count: int | None = None
    max_drawdown_pct: float | None = None
    sharpe_ratio: float | None = None
    profit_factor: float | None = None
    calmar_ratio: float | None = None

    report_link: str | None = None
    incomplete: bool = False
    low_activity: bool = False

    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
