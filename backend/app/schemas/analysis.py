"""PROJ-23: Schemas für Erfolgsfaktorenanalyse."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AnalysisRunRead(BaseModel):
    id: UUID
    comparison_group: str
    success_definition: dict
    total_analyzed: int
    total_excluded: int
    excluded_reasons: dict
    created_at: datetime


class AnalysisRunRowRead(BaseModel):
    id: UUID
    strategy_name: str
    strategy_version_id: UUID | None = None
    calmar_ratio: float | None = None
    sortino_ratio: float | None = None
    trades_per_year: float | None = None
    is_success: bool
    indicators: list[str]
    indicator_count: int
    parameter_count: int
    entry_archetype: str
    exit_archetype: str
    category: str | None = None
    direction: str | None = None
    mts_compatibility: str | None = None


class CohortRow(BaseModel):
    value: str
    success: int
    total: int
    success_quote: float | None = None
    lift: float | None = None
    median_calmar: float | None = None


class AnalysisRunDetailRead(AnalysisRunRead):
    rows: list[AnalysisRunRowRead]
    cohort: list[CohortRow]
