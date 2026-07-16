"""PROJ-6: Run-spezifische Endpunkte (cancel, retry, detail)."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from ..db import run_command, run_query, run_query_one, transaction
from ..schemas.batches import (
    BacktestMetrics,
    RetryCreditCheckResponse,
    RunRead,
)
from ..services.trader_dev import CreditServiceError, get_credits

router = APIRouter(prefix="/runs", tags=["runs"])


PENDING_STATUSES = {"geplant", "bestätigt", "in_queue", "läuft"}
TERMINAL_STATUSES = {"erfolgreich", "fehlgeschlagen", "abgebrochen"}


def _load_run(run_id: UUID) -> dict:
    row = run_query_one("SELECT * FROM runs WHERE id = %s", [run_id])
    if not row:
        raise HTTPException(404, "Run nicht gefunden.")
    return _enrich_run(row)


def _enrich_run(row: dict) -> dict:
    """Reichert eine DB-Run-Zeile mit Backtest-Metriken und Job-ID an."""
    result: dict = {**row}
    exec_id = row.get("backtest_execution_id")
    if exec_id:
        be = run_query_one(
            "SELECT external_job_id, external_result_id, backtest_result FROM backtest_executions WHERE id = %s",
            [exec_id],
        )
        if be:
            if be.get("external_job_id"):
                result["backtest_job_id"] = be["external_job_id"]
            if be.get("backtest_result") and isinstance(be["backtest_result"], dict):
                result["backtest_metrics"] = _extract_metrics(be["backtest_result"])
    return result


def _extract_metrics(raw: dict) -> dict:
    """Extrahiert standardisierte Backtest-Kennzahlen aus der trader.dev-Antwort."""
    return {
        "net_profit_pct": raw.get("netProfitPct"),
        "profit_factor": raw.get("profitFactor"),
        "sharpe_ratio": raw.get("sharpeRatio"),
        "sortino_ratio": raw.get("sortinoRatio"),
        "max_drawdown_pct": raw.get("maxDrawdownPct"),
        "win_rate_pct": raw.get("winRatePct"),
        "trade_count": raw.get("tradeCount"),
    }


@router.get("/{run_id}", response_model=RunRead)
def get_run(run_id: UUID) -> dict:
    return _load_run(run_id)


@router.post("/{run_id}/cancel", response_model=RunRead)
def cancel_run(run_id: UUID) -> dict:
    row = run_query_one("SELECT * FROM runs WHERE id = %s", [run_id])
    if not row:
        raise HTTPException(404, "Run nicht gefunden.")
    if row["status"] not in {"geplant", "bestätigt"}:
        raise HTTPException(422, "Nur geplante oder bestätigte Runs können abgebrochen werden.")
    run_command(
        "UPDATE runs SET status = 'abgebrochen', completed_at = %s WHERE id = %s",
        [datetime.now(timezone.utc), run_id],
    )
    return _load_run(run_id)


@router.get("/{run_id}/retry-credit-check", response_model=RetryCreditCheckResponse)
def retry_credit_check(run_id: UUID) -> dict:
    row = run_query_one("SELECT * FROM runs WHERE id = %s", [run_id])
    if not row:
        raise HTTPException(404, "Run nicht gefunden.")
    if row["status"] != "fehlgeschlagen":
        return {"ok": False, "reason": "Nur fehlgeschlagene Runs können wiederholt werden."}
    try:
        credits = get_credits()
    except CreditServiceError as exc:
        raise HTTPException(502, f"Credit-Prüfung fehlgeschlagen: {exc}")
    balance = int(credits["balance"])
    if balance < 1:
        return {"ok": False, "reason": "Keine Credits verfügbar."}
    return {"ok": True}


@router.post("/{run_id}/retry", status_code=201)
def retry_run(run_id: UUID) -> dict:
    row = run_query_one("SELECT * FROM runs WHERE id = %s", [run_id])
    if not row:
        raise HTTPException(404, "Run nicht gefunden.")
    if row["status"] != "fehlgeschlagen":
        raise HTTPException(422, "Nur fehlgeschlagene Runs können wiederholt werden.")

    try:
        credits = get_credits()
    except CreditServiceError as exc:
        raise HTTPException(502, f"Credit-Prüfung fehlgeschlagen: {exc}")
    balance = int(credits["balance"])
    if balance < 1:
        raise HTTPException(422, "Keine Credits verfügbar — Retry nicht möglich.")

    batch = run_query_one("SELECT * FROM batches WHERE id = %s", [row["batch_id"]])
    if not batch:
        raise HTTPException(404, "Batch nicht gefunden.")

    new_id = uuid4()
    now = datetime.now(timezone.utc)
    run_command(
        """
        INSERT INTO runs (id, batch_id, strategy_version_id, provider_symbol,
                          direction_mode, run_kind, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, 'bestätigt', %s)
        """,
        [new_id, row["batch_id"], row["strategy_version_id"], row["provider_symbol"],
         row["direction_mode"], row["run_kind"], now],
    )
    return {"run_id": new_id}


@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: UUID) -> None:
    row = run_query_one("SELECT batch_id, status, backtest_execution_id FROM runs WHERE id = %s", [run_id])
    if not row:
        raise HTTPException(404, "Run nicht gefunden.")
    if row["status"] == "läuft":
        raise HTTPException(422, "Laufende Runs können nicht gelöscht werden.")

    with transaction() as cur:
        cur.execute("DELETE FROM run_audits WHERE run_id = %s", [run_id])
        cur.execute("DELETE FROM runs WHERE id = %s", [run_id])
        if row["backtest_execution_id"]:
            cur.execute(
                "DELETE FROM backtest_executions WHERE id = %s AND NOT EXISTS (SELECT 1 FROM runs WHERE backtest_execution_id = %s)",
                [row["backtest_execution_id"], row["backtest_execution_id"]],
            )
        # War das der letzte Run des Batches, bleibt er sonst dauerhaft in
        # 'bestätigt'/'in_ausfuehrung' hängen — Konfiguration wäre für immer
        # gesperrt (isConfirmed) und ein neuer Start unmöglich (0 Runs).
        cur.execute("SELECT COUNT(*) AS cnt FROM runs WHERE batch_id = %s", [row["batch_id"]])
        if cur.fetchone()["cnt"] == 0:
            cur.execute(
                """
                UPDATE batches SET
                    status = 'entwurf', confirmed_at = NULL,
                    credit_max = NULL, credit_balance = NULL, credit_remaining = NULL,
                    credit_tier = NULL, credit_reset = NULL, credit_checked_at = NULL
                WHERE id = %s
                """,
                [row["batch_id"]],
            )


def _build_run_summary(batch_id: UUID) -> dict:
    rows = run_query("SELECT status, COUNT(*) AS cnt FROM runs WHERE batch_id = %s GROUP BY status", [batch_id])
    summary = {"total": 0, "erfolgreich": 0, "fehlgeschlagen": 0, "offen": 0, "abgebrochen": 0}
    for r in rows:
        cnt = int(r["cnt"])
        summary["total"] += cnt
        if r["status"] == "erfolgreich":
            summary["erfolgreich"] = cnt
        elif r["status"] == "fehlgeschlagen":
            summary["fehlgeschlagen"] = cnt
        elif r["status"] == "abgebrochen":
            summary["abgebrochen"] = cnt
        elif r["status"] in PENDING_STATUSES:
            summary["offen"] += cnt
    return summary
