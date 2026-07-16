"""PROJ-12 Worker — Dauerhaft laufender Dienst, verarbeitet bestätigte Runs
aus der PostgreSQL-Queue.

Aufgabe:
  1. Heartbeat schreiben (PostgreSQL, alle ~30s)
  2. Offene bestätigte Runs abfragen (SELECT ... WHERE status = 'bestätigt' FOR UPDATE SKIP LOCKED)
  3. Bestehende, noch nicht terminale Backtests wieder aufnehmen
  4. Idempotency-Key aus Run-Parametern bauen
  5. Existierende backtest_execution finden oder neue anlegen
  6. Pine-v5-Übersetzung aus strategy_versions.snapshot generieren
  7. run_backtest via OpenCode/trader.dev MCP starten
  8. get_backtest_result pollen
  9. Ergebnis in backtest_executions speichern, Run-Status aktualisieren

Der Worker läuft als separater Prozess (nicht im FastAPI-Server). Kein
HTTP-Timeout-Problem bei minutenlangen Backtests.
"""

import json
import logging
import subprocess
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from ..config import settings
from .pine_generator import PineGenerationError, generate as generate_pine

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30
HEARTBEAT_INTERVAL_SECONDS = 30
MCP_TIMEOUT_SECONDS = 60
RUN_LIMIT = 5

WORKER_ID = "strategy-bank-worker-v1"


def run_worker() -> None:
    """Blockierender Hauptloop — läuft bis zum Prozessende."""
    logger.info("Worker gestartet — %s", WORKER_ID)
    last_heartbeat = _epoch()
    while True:
        now = _epoch()
        if (now - last_heartbeat).total_seconds() >= HEARTBEAT_INTERVAL_SECONDS:
            _heartbeat()
            last_heartbeat = now
        _recover_in_flight()
        _process_pending()
        time.sleep(POLL_INTERVAL_SECONDS)


def _epoch() -> datetime:
    return datetime.now(timezone.utc)


def _heartbeat() -> None:
    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE worker_heartbeat SET last_heartbeat = %s WHERE worker_id = %s",
                [_epoch(), WORKER_ID],
            )
            conn.commit()
    except Exception:
        logger.exception("Heartbeat-Schreiben fehlgeschlagen")


def _recover_in_flight() -> None:
    """Startet in-flight Runs wieder auf, deren provider_status noch
    submitted/running ist — z. B. nach Worker-Neustart."""
    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.*, be.id AS exec_id, be.external_job_id, be.provider_status
                FROM runs r
                JOIN backtest_executions be ON be.id = r.backtest_execution_id
                WHERE r.status = 'läuft' AND be.provider_status IN ('submitted', 'running')
                ORDER BY r.created_at ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED
                """,
                [RUN_LIMIT],
            )
            in_flight = cur.fetchall()
            for run in in_flight:
                exec_row = _exec_row_from_run(run)
                try:
                    _check_existing_job(cur, run["id"], exec_row)
                except Exception:
                    logger.exception("Run %s Wiederaufnahme fehlgeschlagen", run["id"])
            conn.commit()
    except Exception:
        logger.exception("Recovery-Loop Fehler")


def _process_pending() -> None:
    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM runs
                WHERE status = 'bestätigt'
                ORDER BY created_at ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED
                """,
                [RUN_LIMIT],
            )
            pending = cur.fetchall()
            for run in pending:
                try:
                    _process_one_run(cur, run)
                except PineGenerationError as e:
                    logger.warning("Run %s Pine-Übersetzung fehlgeschlagen: %s", run["id"], e)
                    cur.execute(
                        "UPDATE runs SET status = 'fehlgeschlagen', error_message = %s, error_category = %s, completed_at = %s WHERE id = %s",
                        [
                            f"Regel nicht automatisch zuverlässig in Pine übersetzbar: {e}",
                            "pine_generation",
                            _epoch(),
                            run["id"],
                        ],
                    )
                except Exception:
                    logger.exception("Run %s fehlgeschlagen", run["id"])
                    cur.execute(
                        "UPDATE runs SET status = 'fehlgeschlagen', error_message = %s, error_category = %s, completed_at = %s WHERE id = %s",
                        ["Interner Worker-Fehler.", "worker_internal", _epoch(), run["id"]],
                    )
            conn.commit()
    except Exception:
        logger.exception("Process-Loop Fehler")


def _process_one_run(cur, run: dict) -> None:
    run_id: UUID = run["id"]

    cur.execute(
        "UPDATE runs SET status = 'in_queue', started_at = %s WHERE id = %s",
        [_epoch(), run_id],
    )

    identity_key = _build_idempotency_key(run)
    exec_row = _find_or_create_execution(cur, run, identity_key)

    if exec_row["provider_status"] == "completed":
        _store_result(cur, run_id, exec_row)
        return

    if exec_row["provider_status"] in ("submitted", "running"):
        _check_existing_job(cur, run_id, exec_row)
        return

    _submit_backtest(cur, run_id, exec_row)


def _build_idempotency_key(run: dict) -> str:
    return "|".join([
        str(run["strategy_version_id"]),
        run["provider_symbol"],
        str(run.get("direction_mode", "")),
        str(run.get("run_kind", "")),
    ])


def _exec_row_from_run(run: dict) -> dict:
    return {
        "id": run.get("exec_id") or run.get("backtest_execution_id"),
        "external_job_id": run.get("external_job_id"),
        "provider_status": run.get("provider_status", "pending"),
    }


def _find_or_create_execution(cur, run: dict, identity_key: str) -> dict:
    cur.execute(
        "SELECT * FROM backtest_executions WHERE idempotency_key = %s",
        [identity_key],
    )
    existing = cur.fetchone()
    if existing:
        cur.execute(
            "UPDATE runs SET backtest_execution_id = %s WHERE id = %s",
            [existing["id"], run["id"]],
        )
        return existing

    strategy = _load_strategy_details(cur, run["strategy_version_id"])
    if strategy.get("_pine_error"):
        raise PineGenerationError(strategy["_pine_error"])

    pine_source = strategy.get("pine_source", "// Pine source TBD")

    cur.execute(
        """
        INSERT INTO backtest_executions (
            idempotency_key, strategy_version_id, provider_symbol, timeframe,
            period_start, period_end, direction_mode, backtest_profile_version_id,
            evaluation_type, pine_source, executor_fingerprint
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        [
            identity_key, run["strategy_version_id"], run["provider_symbol"],
            strategy.get("timeframe", "1h"), strategy.get("period_start", "2021-01-01"),
            strategy.get("period_end"), run["direction_mode"],
            strategy["backtest_profile_id"],
            run.get("run_kind", "standard"),
            pine_source,
            WORKER_ID,
        ],
    )
    new_exec = cur.fetchone()
    cur.execute(
        "UPDATE runs SET backtest_execution_id = %s WHERE id = %s",
        [new_exec["id"], run["id"]],
    )
    return new_exec


def _submit_backtest(cur, run_id: UUID, exec_row: dict) -> None:
    cur.execute("UPDATE runs SET status = 'läuft' WHERE id = %s", [run_id])
    cur.execute(
        "UPDATE backtest_executions SET provider_status = 'submitted', started_at = %s WHERE id = %s",
        [_epoch(), exec_row["id"]],
    )

    prompt = _build_run_prompt(exec_row)
    try:
        result = subprocess.run(
            [
                settings.opencode_binary, "run", prompt,
                "--format", "json", "-m", settings.extraction_model,
            ],
            capture_output=True, text=True, timeout=MCP_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        _mark_failed(cur, run_id, exec_row, "trader.dev-Aufruf: Timeout (60s).", "trader_dev_timeout")
        return

    if result.returncode != 0:
        _mark_failed(cur, run_id, exec_row, f"OpenCode Exit {result.returncode}.", "opencode_error")
        return

    output = _parse_json_output(result.stdout)
    if output.get("error"):
        _mark_failed(cur, run_id, exec_row, output["error"], "backtest_error")
        return

    job_id = output.get("jobId") or output.get("job_id")
    if job_id:
        cur.execute(
            "UPDATE backtest_executions SET external_job_id = %s, provider_status = 'running' WHERE id = %s",
            [str(job_id), exec_row["id"]],
        )


def _check_existing_job(cur, run_id: UUID, exec_row: dict) -> None:
    if not exec_row.get("external_job_id"):
        return
    cur.execute("UPDATE runs SET status = 'läuft' WHERE id = %s", [run_id])
    prompt = (
        f"Call the trader_dev_get_backtest_result tool with jobId={exec_row['external_job_id']}. "
        "Output ONLY the raw JSON result inside a ```json code block. No commentary."
    )
    try:
        result = subprocess.run(
            [
                settings.opencode_binary, "run", prompt,
                "--format", "json", "-m", settings.extraction_model,
            ],
            capture_output=True, text=True, timeout=MCP_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return

    if result.returncode != 0:
        return

    output = _parse_json_output(result.stdout)
    if output.get("status") == "completed" and output.get("result"):
        cur.execute(
            "UPDATE backtest_executions SET backtest_result = %s, provider_status = 'completed', completed_at = %s WHERE id = %s",
            [json.dumps(output["result"]), _epoch(), exec_row["id"]],
        )
        cur.execute(
            "UPDATE runs SET status = 'erfolgreich', completed_at = %s WHERE id = %s",
            [_epoch(), run_id],
        )


def _store_result(cur, run_id: UUID, exec_row: dict) -> None:
    cur.execute(
        "UPDATE runs SET status = 'erfolgreich', completed_at = %s WHERE id = %s",
        [_epoch(), run_id],
    )


def _mark_failed(cur, run_id: UUID, exec_row: dict, message: str, category: str) -> None:
    cur.execute(
        "UPDATE runs SET status = 'fehlgeschlagen', error_message = %s, error_category = %s, completed_at = %s WHERE id = %s",
        [message, category, _epoch(), run_id],
    )
    cur.execute(
        "UPDATE backtest_executions SET provider_status = 'failed', completed_at = %s WHERE id = %s",
        [_epoch(), exec_row["id"]],
    )
    try:
        cur.execute(
            "UPDATE worker_heartbeat SET last_error_category = %s, last_error_at = %s WHERE worker_id = %s",
            [category, _epoch(), WORKER_ID],
        )
    except Exception:
        pass


def _build_run_prompt(exec_row: dict) -> str:
    return (
        f"Call the trader_dev_quick_backtest tool with:\n"
        f"- pineSource (full Pine Script v5):\n```pinescript\n{exec_row['pine_source']}\n```\n"
        f"- symbol: {exec_row['provider_symbol']}\n"
        f"- timeframe: {exec_row['timeframe']}\n"
        f"- from: {exec_row['period_start']}\n"
        f"{'- to: ' + str(exec_row['period_end']) if exec_row.get('period_end') else ''}\n"
        f"Output ONLY the raw JSON result inside a ```json code block. No commentary."
    )


def _parse_json_output(stdout: str) -> dict[str, Any]:
    parts: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "error":
            msg = event.get("error", {}).get("data", {}).get("message", "Unbekannt")
            return {"error": msg}
        part = event.get("part") or {}
        if part.get("type") == "text" and part.get("text"):
            parts.append(part["text"])
    text = "\n".join(parts)
    import re
    fence = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
    m = fence.findall(text)
    candidate = m[-1].strip() if m else text.strip()
    if candidate.startswith("{"):
        end = candidate.rfind("}")
        if end != -1:
            candidate = candidate[:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {}


def _load_strategy_details(cur, version_id: UUID) -> dict:
    cur.execute(
        """SELECT sv.*, b.timeframe, b.period_start, b.period_end, b.backtest_profile_id
           FROM strategy_versions sv
           JOIN runs r ON r.strategy_version_id = sv.id
           JOIN batches b ON b.id = r.batch_id
           WHERE sv.id = %s LIMIT 1""",
        [version_id],
    )
    row = cur.fetchone()
    if not row:
        return {}

    snapshot = row.get("snapshot") or {}
    if isinstance(snapshot, str):
        import json as _json
        snapshot = _json.loads(snapshot)

    try:
        pine_source = generate_pine(
            snapshot,
            params=snapshot.get("parameters"),
            timeframe=row.get("timeframe", "1h"),
            direction=row.get("direction_mode"),
        )
        row["pine_source"] = pine_source
    except PineGenerationError as e:
        row["_pine_error"] = str(e)

    return row
