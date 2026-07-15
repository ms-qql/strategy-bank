from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SourceListItem(BaseModel):
    id: UUID
    source_hash: str
    source_type: str
    filename: str | None
    extraction_status: str
    captured_at: datetime


class SourceDetail(BaseModel):
    id: UUID
    content: str
    source_hash: str
    source_type: str
    filename: str | None
    extraction_status: str
    captured_at: datetime
