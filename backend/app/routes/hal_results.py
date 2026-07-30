"""PROJ-21: HAL-Import — Dateien entgegennehmen, parsen, zuweisen."""

import hashlib
import io
import json
import os.path
import zipfile
from uuid import UUID, uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..db import run_command, run_query, run_query_one, transaction
from ..schemas.hal_import import (
    HalAssignRequest,
    HalImportFileResult,
    HalImportResponse,
    HalImportRunRead,
    HalImportedFileRow,
    HalResultRead,
    HalUnassignedRead,
)
from ..services.hal_parser import parse_hal_backtest

router = APIRouter(prefix="/hal-results", tags=["hal-results"])

ZIP_MAX_UNCOMPRESSED_MB = 100
MAX_ITEMS_PER_UPLOAD = 500


def _normalize_origin_path(path: str, *, is_zip: bool) -> str:
    """Normalisiert Dateinamen: entfernt führende Pfadtrenner, normalisiert Slashes."""
    if is_zip:
        path = path.replace("\\", "/")
        path = "/".join(part for part in path.split("/") if part)
    return os.path.normpath(path).lstrip("/")


def _safe_zip_path(path: str) -> bool:
    """Schützt vor Zip-Slip: Pfad darf das Archiv nicht verlassen."""
    normalized = os.path.normpath(path.lstrip("/"))
    return not normalized.startswith("..") and not os.path.isabs(normalized)


def _extract_files_from_request(files: list[UploadFile]) -> list[tuple[str, bytes, bool]]:
    """Extrahiert .md-Dateien aus direktem Upload oder ZIP-Archiv."""
    results: list[tuple[str, bytes, bool]] = []

    if len(files) == 0:
        return results

    first = files[0]
    first_bytes = first.file.read()  # type: ignore[union-attr]
    first_name = first.filename or ""

    if first_name.lower().endswith(".zip"):
        if len(files) > 1:
            raise HTTPException(400, "ZIP-Upload akzeptiert immer genau eine Datei.")
        return _extract_from_zip(first_bytes)

    if not all(f.filename and f.filename.lower().endswith(".md") for f in files):
        raise HTTPException(400, "Nur .md- oder .zip-Dateien werden unterstützt.")

    results.append((_normalize_origin_path(first_name, is_zip=False), first_bytes, False))
    for f in files[1:]:
        content = f.file.read()  # type: ignore[union-attr]
        results.append((_normalize_origin_path(f.filename or "", is_zip=False), content, False))

    return results


def _extract_from_zip(zip_bytes: bytes) -> list[tuple[str, bytes, bool]]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        total_size = sum(info.file_size for info in zf.infolist())
        if total_size > ZIP_MAX_UNCOMPRESSED_MB * 1024 * 1024:
            raise HTTPException(400, f"ZIP-Archiv überschreitet {ZIP_MAX_UNCOMPRESSED_MB} MB unkomprimiert.")

        items: list[tuple[str, bytes, bool]] = []
        for info in zf.infolist():
            if info.is_dir():
                continue
            path = _normalize_origin_path(info.filename, is_zip=True)
            if not _safe_zip_path(info.filename):
                items.append((path, b"", True))
                continue
            if not path.lower().endswith(".md"):
                items.append((path, b"", True))
                continue
            if len(items) >= MAX_ITEMS_PER_UPLOAD:
                break
            data = zf.read(info)
            items.append((path, data, False))
    return items


@router.post("/import", response_model=HalImportResponse, status_code=201)
async def import_hal_results(files: list[UploadFile] = File(...)) -> dict:
    if not files:
        raise HTTPException(400, "Keine Dateien ausgewählt.")

    items = _extract_files_from_request(files)

    # Wenn NUR abgelehnte Einträge vorhanden sind, lehnen wir den gesamten
    # Upload ab (z.B. ZIP nur mit PDFs).
    valid_items = [
        (path, data, rejected)
        for path, data, rejected in items
        if not rejected or path.lower().endswith(".md")
    ]
    if not items or not valid_items:
        raise HTTPException(400, "Keine gültigen .md-Dateien gefunden.")

    run_id = uuid4()
    results: list[HalImportFileResult] = []
    status_counts = {"importiert": 0, "unverändert": 0, "aktualisiert": 0, "fehlerhaft": 0}

    with transaction() as cur:
        cur.execute(
            "INSERT INTO hal_import_runs (id, total_files) VALUES (%s, %s)",
            [run_id, len(items)],
        )

        for origin_path, raw_bytes, is_rejected in items:
            content_hash = hashlib.sha256(raw_bytes).hexdigest()
            file_result = _process_one_file(
                cur, run_id, origin_path, content_hash, raw_bytes, is_rejected
            )
            results.append(file_result)
            status_counts[file_result["status"]] += 1

        cur.execute(
            """UPDATE hal_import_runs SET
               status_imported = %s, status_unchanged = %s,
               status_updated = %s, status_failed = %s
               WHERE id = %s""",
            [
                status_counts["importiert"],
                status_counts["unverändert"],
                status_counts["aktualisiert"],
                status_counts["fehlerhaft"],
                run_id,
            ],
        )

    return {"import_run_id": run_id, "total": len(results), "files": results}


def _process_one_file(
    cur,
    run_id: UUID,
    origin_path: str,
    content_hash: str,
    raw_bytes: bytes,
    is_rejected: bool,
) -> dict:
    if is_rejected:
        return _reject_file(cur, run_id, origin_path, content_hash, "Dateityp wird nicht unterstützt.")

    # Dedup: gleicher Pfad + gleicher Hash → unverändert (kein neuer Insert)
    existing = run_query(
        """SELECT id, content_hash, import_version FROM hal_imported_files
           WHERE origin_path = %s AND content_hash = %s
           ORDER BY import_version DESC LIMIT 1""",
        [origin_path, content_hash],
    )
    if existing:
        return {"origin_path": origin_path, "content_hash": content_hash, "status": "unverändert"}

    # Gleicher Pfad, anderer Hash → neue Importversion
    current = run_query_one(
        "SELECT id, import_version FROM hal_imported_files WHERE origin_path = %s AND is_current = true",
        [origin_path],
    )
    if current:
        return _updated_file(cur, run_id, current["id"], origin_path, content_hash, raw_bytes)

    # Neuimport
    return _import_file(cur, run_id, origin_path, content_hash, raw_bytes)


def _updated_file(cur, run_id: UUID, existing_id: UUID, origin_path: str, content_hash: str, raw_bytes: bytes) -> dict:
    old_version = run_query_one(
        "SELECT import_version, content_hash FROM hal_imported_files WHERE id = %s",
        [existing_id],
    )
    new_version = (old_version["import_version"] + 1) if old_version else 1

    cur.execute(
        "UPDATE hal_imported_files SET is_current = false WHERE origin_path = %s AND is_current = true",
        [origin_path],
    )

    new_id = uuid4()
    cur.execute(
        """INSERT INTO hal_imported_files (id, import_run_id, origin_path, content_hash,
           import_version, is_current, processing_status)
           VALUES (%s, %s, %s, %s, %s, true, 'aktualisiert')""",
        [new_id, run_id, origin_path, content_hash, new_version],
    )

    text = raw_bytes.decode("utf-8", errors="replace")
    parsed = parse_hal_backtest(text)
    if parsed.is_valid:
        _insert_hal_result(cur, new_id, parsed, content_hash, new_version)

    result: dict = {"origin_path": origin_path, "content_hash": content_hash, "status": "aktualisiert"}
    if parsed.error:
        result["error_message"] = parsed.error
    else:
        result["strategy_name"] = parsed.strategy_name
    return result


def _reject_file(cur, run_id: UUID, origin_path: str, content_hash: str, reason: str) -> dict:
    cur.execute(
        """INSERT INTO hal_imported_files (id, import_run_id, origin_path, content_hash,
           import_version, is_current, processing_status, error_message)
           VALUES (%s, %s, %s, %s, 1, false, 'fehlerhaft', %s)""",
        [uuid4(), run_id, origin_path, content_hash, reason],
    )
    return {"origin_path": origin_path, "content_hash": content_hash, "status": "fehlerhaft", "error_message": reason}


def _import_file(cur, run_id: UUID, origin_path: str, content_hash: str, raw_bytes: bytes) -> dict:
    text = raw_bytes.decode("utf-8", errors="replace")
    parsed = parse_hal_backtest(text)

    file_id = uuid4()
    if parsed.is_valid:
        cur.execute(
            """INSERT INTO hal_imported_files (id, import_run_id, origin_path, content_hash,
               import_version, is_current, processing_status)
               VALUES (%s, %s, %s, %s, 1, true, 'importiert')""",
            [file_id, run_id, origin_path, content_hash],
        )
        _insert_hal_result(cur, file_id, parsed, content_hash, 1)
        return {"origin_path": origin_path, "content_hash": content_hash, "status": "importiert", "strategy_name": parsed.strategy_name}
    else:
        cur.execute(
            """INSERT INTO hal_imported_files (id, import_run_id, origin_path, content_hash,
               import_version, is_current, processing_status, error_message)
               VALUES (%s, %s, %s, %s, 1, false, 'fehlerhaft', %s)""",
            [file_id, run_id, origin_path, content_hash, parsed.error],
        )
        return {"origin_path": origin_path, "content_hash": content_hash, "status": "fehlerhaft", "error_message": parsed.error}


def _insert_hal_result(cur, file_id: UUID, parsed, content_hash: str, import_version: int) -> None:
    # auto-assign: check for strategy version identifier from file
    # first try exact name match
    sv_id = None
    assignment_origin = None

    match = run_query_one(
        "SELECT id FROM strategy_versions WHERE snapshot->>'name' = %s ORDER BY version_number DESC LIMIT 1",
        [parsed.strategy_name],
    )
    if match:
        sv_id = match["id"]
        assignment_origin = "suggestion_accepted"

    cur.execute(
        """INSERT INTO hal_results (id, imported_file_id, strategy_name, asset, timeframe,
           period_start, period_end, net_return_pct, max_drawdown_pct, trade_count,
           sortino_ratio, profit_factor, sharpe_ratio, win_rate_pct, report_link,
           parameters, long_short_breakdown, pine_code, direction,
           fee_pct, slippage_ticks, sizing_model,
           strategy_version_id, assignment_origin, import_version)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        [
            uuid4(), file_id, parsed.strategy_name, parsed.asset, parsed.timeframe,
            parsed.period_start, parsed.period_end, parsed.net_return_pct, parsed.max_drawdown_pct, parsed.trade_count,
            parsed.sortino_ratio, parsed.profit_factor, parsed.sharpe_ratio, parsed.win_rate_pct, parsed.report_link,
            json.dumps(parsed.parameters) if parsed.parameters else None,
            json.dumps(parsed.long_short_breakdown) if parsed.long_short_breakdown else None,
            parsed.pine_code, parsed.direction,
            parsed.fee_pct, parsed.slippage_ticks, parsed.sizing_model,
            sv_id, assignment_origin, import_version,
        ],
    )


@router.get("/imports", response_model=list[HalImportRunRead])
def list_import_runs(limit: int = 20) -> list[dict]:
    limit = min(max(limit, 1), 100)
    return run_query(
        "SELECT * FROM hal_import_runs ORDER BY created_at DESC LIMIT %s",
        [limit],
    )


@router.get("/imports/{run_id}/files", response_model=list[HalImportedFileRow])
def list_imported_files(run_id: UUID) -> list[dict]:
    return run_query(
        "SELECT * FROM hal_imported_files WHERE import_run_id = %s ORDER BY created_at",
        [run_id],
    )


@router.get("/unassigned", response_model=list[HalUnassignedRead])
def list_unassigned() -> list[dict]:
    rows = run_query("""
        SELECT hr.*, hif.origin_path AS import_origin_path
        FROM hal_results hr
        JOIN hal_imported_files hif ON hif.id = hr.imported_file_id
        WHERE hr.strategy_version_id IS NULL AND hif.is_current = true
        ORDER BY hr.created_at DESC
    """)
    out = []
    for r in rows:
        suggested = _suggest_version(r) or {}
        out.append({
            **r,
            "suggested_version_id": suggested.get("id"),
            "suggested_version_name": suggested.get("name"),
        })
    return out


def _suggest_version(result: dict) -> dict | None:
    name = result.get("strategy_name", "")
    match = run_query_one(
        "SELECT id, snapshot->>'name' AS name FROM strategy_versions WHERE snapshot->>'name' = %s ORDER BY version_number DESC LIMIT 1",
        [name],
    )
    if match:
        return match
    return None


@router.get("/{result_id}", response_model=HalResultRead)
def get_hal_result(result_id: UUID) -> dict:
    row = run_query_one(
        "SELECT * FROM hal_results WHERE id = %s",
        [result_id],
    )
    if not row:
        raise HTTPException(404, "HAL-Ergebnis nicht gefunden.")
    return row


@router.post("/{result_id}/assign", response_model=HalResultRead)
def assign_result(result_id: UUID, body: HalAssignRequest) -> dict:
    row = run_query_one("SELECT * FROM hal_results WHERE id = %s", [result_id])
    if not row:
        raise HTTPException(404, "HAL-Ergebnis nicht gefunden.")

    sv_id = body.strategy_version_id
    if sv_id is not None:
        sv = run_query_one("SELECT id FROM strategy_versions WHERE id = %s", [sv_id])
        if not sv:
            raise HTTPException(404, "Strategieversion nicht gefunden.")
        assignment_origin = "manual"
    else:
        assignment_origin = None

    run_command(
        "UPDATE hal_results SET strategy_version_id = %s, assignment_origin = %s WHERE id = %s",
        [sv_id, assignment_origin, result_id],
    )
    return run_query_one("SELECT * FROM hal_results WHERE id = %s", [result_id])
