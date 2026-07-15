from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ..constants import CATEGORIES, DIRECTIONS


class ParameterEdit(BaseModel):
    name: str
    value: str
    unit: str | None = None
    allowed_range: str | None = None


class DraftUpdate(BaseModel):
    name: str | None = None
    thesis: str | None = None
    category: str | None = None
    direction: str | None = None
    entry_rule: str | None = None
    exit_rule: str | None = None
    warmup_requirement: str | None = None
    simultaneous_entry_exit_behavior: str | None = None
    reversal_behavior: str | None = None
    status_reason: str | None = None
    parameters: list[ParameterEdit] | None = None


class MarkUntestableRequest(BaseModel):
    reason: str = Field(min_length=1)


class VersionParameterRead(BaseModel):
    name: str
    value: str
    unit: str | None
    allowed_range: str | None


class VersionRead(BaseModel):
    id: UUID
    draft_id: UUID
    family_id: UUID
    version_number: int
    source_id: UUID
    source_hash: str
    extraction_model: str
    prompt_version: str
    snapshot: dict
    frozen_at: datetime
    created_at: datetime
    parameters: list[VersionParameterRead] = []
    user_diff: list[dict] = []


class VersionListItem(BaseModel):
    id: UUID
    draft_id: UUID
    version_number: int
    frozen_at: datetime
    created_at: datetime


class VersionSummary(BaseModel):
    id: UUID
    family_id: UUID
    version_number: int
    name: str | None
    frozen_at: datetime
