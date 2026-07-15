import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException

from ..constants import CATEGORIES, DIRECTIONS
from ..db import run_command, run_query, run_query_one, transaction
from ..schemas.drafts import (
    DraftUpdate,
    MarkUntestableRequest,
    VersionListItem,
    VersionParameterRead,
    VersionRead,
    VersionSummary,
)

router = APIRouter(tags=["drafts"])

_FIELD_NAMES = [
    "name", "thesis", "category", "direction",
    "entry_rule", "exit_rule", "warmup_requirement",
    "simultaneous_entry_exit_behavior", "reversal_behavior",
]


def _compute_user_diff(original_snapshot: dict | None, version_snapshot: dict) -> list[dict]:
    if not original_snapshot:
        return []
    diff: list[dict] = []
    for field in _FIELD_NAMES:
        old_val = str(original_snapshot.get(field) or "")
        new_val = str(version_snapshot.get(field) or "")
        if old_val != new_val:
            diff.append({"field": field, "from": original_snapshot.get(field), "to": version_snapshot.get(field)})
    orig_params = {p["name"]: p.get("value", "") for p in original_snapshot.get("parameters") or []}
    ver_params = {p["name"]: p.get("value", "") for p in version_snapshot.get("parameters") or []}
    all_names = set(orig_params) | set(ver_params)
    for name in sorted(all_names):
        if orig_params.get(name) != ver_params.get(name):
            diff.append({"field": f"parameter:{name}", "from": orig_params.get(name), "to": ver_params.get(name)})
    return diff


@router.patch("/drafts/{draft_id}")
def update_draft(draft_id: UUID, body: DraftUpdate) -> dict:
    draft = run_query_one("SELECT id, status FROM strategy_drafts WHERE id = %s", [draft_id])
    if not draft:
        raise HTTPException(404, "Entwurf nicht gefunden.")
    if draft["status"] in ("freigegeben",):
        raise HTTPException(422, "Bereits freigegebene Entwürfe können nicht bearbeitet werden.")

    update_fields: dict[str, object] = {}
    for field in _FIELD_NAMES:
        val = getattr(body, field, None)
        if val is not None:
            if field == "category" and val not in CATEGORIES:
                raise HTTPException(422, f"Ungültige Kategorie: {val}")
            if field == "direction" and val not in DIRECTIONS:
                raise HTTPException(422, f"Ungültige Richtung: {val}")
            update_fields[field] = val
    if body.status_reason is not None:
        update_fields["status_reason"] = body.status_reason

    if update_fields:
        set_clause = ", ".join(f"{k} = %s" for k in update_fields)
        run_command(
            f"UPDATE strategy_drafts SET {set_clause} WHERE id = %s",
            [*update_fields.values(), draft_id],
        )

    if body.parameters is not None:
        with transaction() as cur:
            cur.execute("DELETE FROM draft_parameters WHERE draft_id = %s", [draft_id])
            for p in body.parameters:
                cur.execute(
                    """
                    INSERT INTO draft_parameters (draft_id, name, value, unit, allowed_range, is_proposal)
                    VALUES (%s, %s, %s, %s, %s, false)
                    """,
                    [draft_id, p.name, p.value, p.unit, p.allowed_range],
                )

    return _load_draft(draft_id)


@router.delete("/drafts/{draft_id}/open-questions/{question_id}", status_code=204)
def close_open_question(draft_id: UUID, question_id: UUID) -> None:
    draft = run_query_one("SELECT id FROM strategy_drafts WHERE id = %s", [draft_id])
    if not draft:
        raise HTTPException(404, "Entwurf nicht gefunden.")
    row = run_query_one(
        "SELECT id FROM draft_open_questions WHERE id = %s AND draft_id = %s",
        [question_id, draft_id],
    )
    if not row:
        raise HTTPException(404, "Unklarheit nicht gefunden.")
    run_command("DELETE FROM draft_open_questions WHERE id = %s", [question_id])


@router.post("/drafts/{draft_id}/freeze", response_model=VersionRead, status_code=201)
def freeze_draft(draft_id: UUID) -> dict:
    draft = run_query_one(
        """
        SELECT id, family_id, status, entry_rule, exit_rule, warmup_requirement
        FROM strategy_drafts WHERE id = %s
        """,
        [draft_id],
    )
    if not draft:
        raise HTTPException(404, "Entwurf nicht gefunden.")
    if draft["status"] != "Entwurf":
        raise HTTPException(422, f"Freigabe nicht möglich — Status ist '{draft['status']}'.")

    open_count = run_query_one(
        "SELECT count(*)::int AS cnt FROM draft_open_questions WHERE draft_id = %s",
        [draft_id],
    )
    if open_count and open_count["cnt"] > 0:
        raise HTTPException(422, "Freigabe nicht möglich — es existieren noch offene Unklarheiten.")

    if not (draft.get("entry_rule") and str(draft["entry_rule"]).strip()):
        raise HTTPException(422, "Freigabe nicht möglich — Entry-Regel fehlt.")
    if not (draft.get("exit_rule") and str(draft["exit_rule"]).strip()):
        raise HTTPException(422, "Freigabe nicht möglich — Exit-Regel fehlt.")
    if draft.get("warmup_requirement") is None:
        raise HTTPException(422, "Freigabe nicht möglich — Warm-up-Anforderung muss explizit gesetzt sein.")

    family_id = draft["family_id"]

    full = run_query_one(
        """
        SELECT sd.id, sd.family_id, sd.name, sd.thesis, sd.category, sd.direction,
               sd.entry_rule, sd.exit_rule, sd.warmup_requirement,
               sd.simultaneous_entry_exit_behavior, sd.reversal_behavior,
               sd.status, sd.status_reason, sd.original_snapshot,
               er.source_id, sd.source_hash, er.model, er.prompt_version
        FROM strategy_drafts sd
        JOIN extraction_runs er ON er.id = sd.extraction_run_id
        WHERE sd.id = %s
        """,
        [draft_id],
    )
    assert full is not None

    max_n = run_query_one(
        "SELECT COALESCE(MAX(version_number), 0) + 1 AS next FROM strategy_versions WHERE family_id = %s",
        [family_id],
    )
    version_number = max_n["next"] if max_n else 1

    snapshot = {
        "name": full["name"],
        "thesis": full["thesis"],
        "category": full["category"],
        "direction": full["direction"],
        "entry_rule": full["entry_rule"],
        "exit_rule": full["exit_rule"],
        "warmup_requirement": full["warmup_requirement"],
        "simultaneous_entry_exit_behavior": full["simultaneous_entry_exit_behavior"],
        "reversal_behavior": full["reversal_behavior"],
    }
    parameters = run_query(
        "SELECT name, value, unit, allowed_range FROM draft_parameters WHERE draft_id = %s",
        [draft_id],
    )
    snapshot["parameters"] = parameters

    now = datetime.now(timezone.utc)

    with transaction() as cur:
        cur.execute(
            """
            INSERT INTO strategy_versions
                (draft_id, family_id, version_number, source_id, source_hash,
                 extraction_model, prompt_version, snapshot, frozen_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
            """,
            [
                draft_id, family_id, version_number,
                full["source_id"], full["source_hash"],
                full["model"], full["prompt_version"],
                json.dumps(snapshot, ensure_ascii=False),
                now,
            ],
        )
        version_row = cur.fetchone()
        version_id = version_row["id"]

        for p in parameters:
            cur.execute(
                """
                INSERT INTO version_parameters (version_id, name, value, unit, allowed_range)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [version_id, p["name"], p["value"], p.get("unit"), p.get("allowed_range")],
            )

        cur.execute(
            "UPDATE strategy_drafts SET status = 'freigegeben', frozen_at = %s WHERE id = %s",
            [now, draft_id],
        )

    user_diff = _compute_user_diff(full["original_snapshot"], snapshot)
    return {
        "id": version_id,
        "draft_id": draft_id,
        "family_id": family_id,
        "version_number": version_number,
        "source_id": full["source_id"],
        "source_hash": full["source_hash"],
        "extraction_model": full["model"],
        "prompt_version": full["prompt_version"],
        "snapshot": snapshot,
        "frozen_at": now.isoformat(),
        "created_at": version_row["created_at"].isoformat(),
        "parameters": [VersionParameterRead(**p) for p in parameters],
        "user_diff": user_diff,
    }


@router.post("/drafts/{draft_id}/mark-untestable", status_code=204)
def mark_untestable(draft_id: UUID, body: MarkUntestableRequest) -> None:
    draft = run_query_one("SELECT id, status FROM strategy_drafts WHERE id = %s", [draft_id])
    if not draft:
        raise HTTPException(404, "Entwurf nicht gefunden.")
    if draft["status"] in ("freigegeben",):
        raise HTTPException(422, "Bereits freigegebene Entwürfe können nicht geändert werden.")
    run_command(
        "UPDATE strategy_drafts SET status = 'nicht testbar', status_reason = %s WHERE id = %s",
        [body.reason, draft_id],
    )


@router.post("/versions/{version_id}/new-draft", response_model=dict, status_code=201)
def new_draft_from_version(version_id: UUID) -> dict:
    version = run_query_one(
        """
        SELECT sv.id, sv.draft_id, sv.family_id, sv.snapshot,
               sv.source_hash, sd.extraction_run_id
        FROM strategy_versions sv
        JOIN strategy_drafts sd ON sd.id = sv.draft_id
        WHERE sv.id = %s
        """,
        [version_id],
    )
    if not version:
        raise HTTPException(404, "Version nicht gefunden.")

    snap = version["snapshot"]
    if isinstance(snap, str):
        snap = json.loads(snap)

    import uuid as _uuid
    new_id = _uuid.uuid4()

    run_command(
        """
        INSERT INTO strategy_drafts (
            id, family_id, extraction_run_id, source_hash, version, parent_version_id,
            name, thesis, category, direction,
            entry_rule, exit_rule, warmup_requirement,
            simultaneous_entry_exit_behavior, reversal_behavior,
            status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            new_id,
            version["family_id"],
            version["extraction_run_id"],
            version["source_hash"],
            1,
            version_id,
            snap.get("name", ""),
            snap.get("thesis", ""),
            snap.get("category", "Sonstige"),
            snap.get("direction", "kombiniert"),
            snap.get("entry_rule"),
            snap.get("exit_rule"),
            snap.get("warmup_requirement"),
            snap.get("simultaneous_entry_exit_behavior"),
            snap.get("reversal_behavior"),
            "Entwurf",
        ],
    )

    for p in snap.get("parameters") or []:
        run_command(
            """
            INSERT INTO draft_parameters (draft_id, name, value, unit, allowed_range, is_proposal)
            VALUES (%s, %s, %s, %s, %s, false)
            """,
            [new_id, p["name"], p["value"], p.get("unit"), p.get("allowed_range")],
        )

    return _load_draft(new_id)


@router.get("/versions", response_model=list[VersionSummary])
def list_all_versions() -> list[dict]:
    """Alle freigegebenen Strategieversionen — für die Batch-Konfiguration (PROJ-4),
    um Strategieversionen familienübergreifend auswählbar zu machen."""
    return run_query(
        """
        SELECT id, family_id, version_number, snapshot->>'name' AS name, frozen_at
        FROM strategy_versions ORDER BY frozen_at DESC
        """
    )


@router.get("/drafts/{draft_id}/versions", response_model=list[VersionListItem])
def list_versions(draft_id: UUID) -> list[dict]:
    draft = run_query_one("SELECT id, family_id FROM strategy_drafts WHERE id = %s", [draft_id])
    if not draft:
        raise HTTPException(404, "Entwurf nicht gefunden.")
    return run_query(
        """
        SELECT id, draft_id, version_number, frozen_at, created_at
        FROM strategy_versions WHERE family_id = %s ORDER BY version_number
        """,
        [draft["family_id"]],
    )


@router.get("/versions/{version_id}", response_model=VersionRead)
def get_version(version_id: UUID) -> dict:
    row = run_query_one(
        """
        SELECT sv.id, sv.draft_id, sv.family_id, sv.version_number,
               sv.source_id, sv.source_hash, sv.extraction_model, sv.prompt_version,
               sv.snapshot, sv.frozen_at, sv.created_at,
               sd.original_snapshot
        FROM strategy_versions sv
        JOIN strategy_drafts sd ON sd.id = sv.draft_id
        WHERE sv.id = %s
        """,
        [version_id],
    )
    if not row:
        raise HTTPException(404, "Version nicht gefunden.")

    snapshot = row["snapshot"]
    if isinstance(snapshot, str):
        snapshot = json.loads(snapshot)

    parameters = run_query(
        "SELECT name, value, unit, allowed_range FROM version_parameters WHERE version_id = %s",
        [version_id],
    )

    user_diff = _compute_user_diff(row["original_snapshot"], snapshot)

    return {
        "id": row["id"],
        "draft_id": row["draft_id"],
        "family_id": row["family_id"],
        "version_number": row["version_number"],
        "source_id": row["source_id"],
        "source_hash": row["source_hash"],
        "extraction_model": row["extraction_model"],
        "prompt_version": row["prompt_version"],
        "snapshot": snapshot,
        "frozen_at": row["frozen_at"],
        "created_at": row["created_at"],
        "parameters": [VersionParameterRead(**p) for p in parameters],
        "user_diff": user_diff,
    }


def _load_draft(draft_id: UUID) -> dict:
    draft = run_query_one(
        """
        SELECT id, extraction_run_id, source_hash, version, name, thesis, category, direction,
               entry_rule, exit_rule, warmup_requirement, simultaneous_entry_exit_behavior,
               reversal_behavior, status, status_reason, created_at, family_id, parent_version_id
        FROM strategy_drafts WHERE id = %s
        """,
        [draft_id],
    )
    assert draft is not None
    parameters = run_query(
        "SELECT name, value, unit, allowed_range, is_proposal FROM draft_parameters WHERE draft_id = %s",
        [draft_id],
    )
    citations = run_query(
        "SELECT rule_field, excerpt, line_reference FROM draft_source_citations WHERE draft_id = %s",
        [draft_id],
    )
    open_questions = run_query(
        "SELECT id, description, reasoning FROM draft_open_questions WHERE draft_id = %s",
        [draft_id],
    )
    from ..schemas.extractions import CitationRead, OpenQuestionRead, ParameterRead  # noqa: PLC0415

    return {
        **draft,
        "parameters": [ParameterRead(**p) for p in parameters],
        "citations": [CitationRead(**c) for c in citations],
        "open_questions": [OpenQuestionRead(**q) for q in open_questions],
    }
