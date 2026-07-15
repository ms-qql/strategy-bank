from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..config import settings
from ..constants import CATEGORIES
from ..db import run_command, run_query, run_query_one
from ..schemas.extractions import (
    CategoryList,
    CitationRead,
    DraftRead,
    ExtractionRunDetail,
    ExtractionRunListItem,
    OpenQuestionRead,
    ParameterRead,
)
from ..services.opencode_extraction import execute_extraction

router = APIRouter(tags=["extractions"])


def _load_draft(draft: dict) -> dict:
    draft_id = draft["id"]
    parameters = run_query(
        "SELECT name, value, unit, allowed_range, is_proposal FROM draft_parameters WHERE draft_id = %s",
        [draft_id],
    )
    citations = run_query(
        "SELECT rule_field, excerpt, line_reference FROM draft_source_citations WHERE draft_id = %s",
        [draft_id],
    )
    open_questions = run_query(
        "SELECT description, reasoning FROM draft_open_questions WHERE draft_id = %s",
        [draft_id],
    )
    return {
        **draft,
        "parameters": [ParameterRead(**p) for p in parameters],
        "citations": [CitationRead(**c) for c in citations],
        "open_questions": [OpenQuestionRead(**q) for q in open_questions],
    }


@router.post("/sources/{source_id}/extractions", response_model=ExtractionRunListItem, status_code=201)
def start_extraction(source_id: UUID, background_tasks: BackgroundTasks) -> dict:
    source = run_query_one("SELECT id, content, source_hash FROM sources WHERE id = %s", [source_id])
    if not source:
        raise HTTPException(404, "Quelle nicht gefunden.")

    run = run_command(
        """
        INSERT INTO extraction_runs (source_id, status, model, prompt_version)
        VALUES (%s, 'läuft', %s, %s)
        RETURNING id, source_id, status, model, prompt_version, started_at, finished_at, error_message
        """,
        [source_id, settings.extraction_model, settings.extraction_prompt_version],
        returning=True,
    )
    run_command(
        "UPDATE sources SET extraction_status = 'wird extrahiert' WHERE id = %s",
        [source_id],
    )

    background_tasks.add_task(
        execute_extraction, run["id"], source_id, source["content"], source["source_hash"]
    )
    return run  # type: ignore[return-value]


@router.get("/sources/{source_id}/extractions", response_model=list[ExtractionRunListItem])
def list_extractions(source_id: UUID) -> list[dict]:
    return run_query(
        """
        SELECT id, source_id, status, model, prompt_version, started_at, finished_at, error_message
        FROM extraction_runs WHERE source_id = %s ORDER BY started_at DESC
        """,
        [source_id],
    )


@router.get("/extractions/{run_id}", response_model=ExtractionRunDetail)
def get_extraction(run_id: UUID) -> dict:
    run = run_query_one(
        """
        SELECT id, source_id, status, model, prompt_version, started_at, finished_at, error_message
        FROM extraction_runs WHERE id = %s
        """,
        [run_id],
    )
    if not run:
        raise HTTPException(404, "Extraktionslauf nicht gefunden.")

    drafts = run_query(
        """
        SELECT id, extraction_run_id, source_hash, name, thesis, category, direction,
               entry_rule, exit_rule, warmup_requirement, simultaneous_entry_exit_behavior,
               reversal_behavior, status, status_reason, created_at
        FROM strategy_drafts WHERE extraction_run_id = %s ORDER BY created_at
        """,
        [run_id],
    )
    return {**run, "drafts": [DraftRead(**_load_draft(d)) for d in drafts]}


@router.get("/drafts/{draft_id}", response_model=DraftRead)
def get_draft(draft_id: UUID) -> dict:
    draft = run_query_one(
        """
        SELECT id, extraction_run_id, source_hash, name, thesis, category, direction,
               entry_rule, exit_rule, warmup_requirement, simultaneous_entry_exit_behavior,
               reversal_behavior, status, status_reason, created_at
        FROM strategy_drafts WHERE id = %s
        """,
        [draft_id],
    )
    if not draft:
        raise HTTPException(404, "Entwurf nicht gefunden.")
    return _load_draft(draft)


@router.get("/categories", response_model=CategoryList)
def get_categories() -> dict:
    return {"categories": CATEGORIES}
