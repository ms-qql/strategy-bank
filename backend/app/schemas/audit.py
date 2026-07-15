from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class AuditTrailRead(BaseModel):
    id: UUID
    run_id: UUID
    batch_id: UUID
    strategy_snapshot: dict
    profile_snapshot: dict
    provider_symbol: str
    timeframe: str
    period_start: date
    period_end: date | None
    direction_mode: str
    run_kind: str
    credit_max: int | None
    credit_balance: int | None
    credit_remaining: int | None
    credit_tier: str | None
    credit_reset: str | None
    credit_checked_at: datetime | None
    agent_runtime: str | None
    model: str | None
    prompt_version: str | None
    executor_version: str | None
    mcp_action: str | None
    external_job_id: str | None
    external_result_id: str | None
    engine_info: str | None
    data_freshness: str | None
    report_link: str | None
    report_available: bool
    raw_response: dict | None
    raw_response_available: bool
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    finalized_at: datetime | None
