from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ExtractionRunListItem(BaseModel):
    id: UUID
    source_id: UUID
    status: str
    model: str
    prompt_version: str
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None


class ParameterRead(BaseModel):
    name: str
    value: str
    unit: str | None
    allowed_range: str | None
    is_proposal: bool


class CitationRead(BaseModel):
    rule_field: str
    excerpt: str
    line_reference: str | None


class OpenQuestionRead(BaseModel):
    description: str
    reasoning: str


class DraftRead(BaseModel):
    id: UUID
    extraction_run_id: UUID
    source_hash: str
    name: str
    thesis: str
    category: str
    direction: str
    entry_rule: str | None
    exit_rule: str | None
    warmup_requirement: str | None
    simultaneous_entry_exit_behavior: str | None
    reversal_behavior: str | None
    status: str
    status_reason: str | None
    created_at: datetime
    parameters: list[ParameterRead] = []
    citations: list[CitationRead] = []
    open_questions: list[OpenQuestionRead] = []


class ExtractionRunDetail(ExtractionRunListItem):
    drafts: list[DraftRead] = []


class CategoryList(BaseModel):
    categories: list[str]
