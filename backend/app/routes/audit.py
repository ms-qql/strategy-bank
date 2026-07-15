from uuid import UUID

from fastapi import APIRouter, HTTPException

from ..db import run_query_one
from ..schemas.audit import AuditTrailRead

router = APIRouter(prefix="/runs", tags=["audit"])


@router.get("/{run_id}/audit", response_model=AuditTrailRead)
def get_run_audit(run_id: UUID) -> dict:
    row = run_query_one(
        "SELECT * FROM run_audits WHERE run_id = %s",
        [run_id],
    )
    if not row:
        raise HTTPException(404, "Audit-Trail nicht gefunden.")
    return row
