"""PROJ-21: Shortlist — manuelle Auswahl von Strategieversionen."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from ..db import run_command, run_query, run_query_one
from ..schemas.hal_import import ShortlistEntry

router = APIRouter(prefix="/shortlist", tags=["shortlist"])


@router.get("", response_model=list[ShortlistEntry])
def list_shortlist() -> list[dict]:
    return run_query(
        "SELECT * FROM shortlist ORDER BY created_at DESC",
    )


@router.put("/{strategy_version_id}", response_model=ShortlistEntry)
def add_to_shortlist(strategy_version_id: UUID) -> dict:
    sv = run_query_one("SELECT id FROM strategy_versions WHERE id = %s", [strategy_version_id])
    if not sv:
        raise HTTPException(404, "Strategieversion nicht gefunden.")

    existing = run_query_one("SELECT * FROM shortlist WHERE strategy_version_id = %s", [strategy_version_id])
    if existing:
        return existing

    run_command(
        "INSERT INTO shortlist (strategy_version_id) VALUES (%s) ON CONFLICT DO NOTHING",
        [strategy_version_id],
    )
    return run_query_one("SELECT * FROM shortlist WHERE strategy_version_id = %s", [strategy_version_id])


@router.delete("/{strategy_version_id}", status_code=204)
def remove_from_shortlist(strategy_version_id: UUID) -> None:
    run_command("DELETE FROM shortlist WHERE strategy_version_id = %s", [strategy_version_id])
