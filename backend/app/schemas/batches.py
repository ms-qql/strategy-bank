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


class PreviewRun(BaseModel):
    strategy_version_id: UUID
    provider_symbol: str
    direction_mode: str


class RunRead(BaseModel):
    id: UUID
    batch_id: UUID
    strategy_version_id: UUID
    provider_symbol: str
    direction_mode: str
    run_kind: str
    status: str
    created_at: datetime


class HoldoutStatusRead(BaseModel):
    family_id: UUID
    consumed: bool
    consumed_at: datetime | None
