"""PROJ-12: Automatische Backtest-Ausführung — Execution-Routes."""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException

from ..db import run_query_one
from ..schemas.execution import AvailabilityResponse

router = APIRouter(prefix="/execution", tags=["execution"])

HEARTBEAT_TIMEOUT_SECONDS = 120


@router.get("/availability", response_model=AvailabilityResponse)
def get_availability() -> dict:
    row = run_query_one(
        "SELECT worker_id, last_heartbeat, last_error_category FROM worker_heartbeat"
    )
    if not row:
        return {
            "available": False,
            "worker_id": "unbekannt",
            "last_heartbeat": datetime(2000, 1, 1, tzinfo=timezone.utc),
        }
    age = (datetime.now(timezone.utc) - row["last_heartbeat"]).total_seconds()
    return {
        "available": age < HEARTBEAT_TIMEOUT_SECONDS,
        "worker_id": row["worker_id"],
        "last_heartbeat": row["last_heartbeat"],
        "last_error_category": row.get("last_error_category"),
    }
