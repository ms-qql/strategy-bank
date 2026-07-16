from datetime import datetime

from pydantic import BaseModel


class AvailabilityResponse(BaseModel):
    available: bool
    worker_id: str
    last_heartbeat: datetime
    last_error_category: str | None = None
