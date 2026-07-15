"""PROJ-7: Ergebnisvergleich — liefert alle Runs als vergleichsfertige Zeilen."""

from uuid import UUID

from fastapi import APIRouter

from ..db import run_query
from ..schemas.results import ResultRow

router = APIRouter(prefix="/results", tags=["results"])

DEFAULT_LOW_ACTIVITY_THRESHOLD = 24


def _extract_and_compute_metrics(row: dict) -> dict:
    """Extrahiert Metriken aus backtest_result JSONB, berechnet CAGR-Fallback und
    Calmar, setzt Kennzeichen incomplete/low_activity."""
    result: dict = {
        "net_profit_pct": None,
        "cagr_pct": None,
        "trade_count": None,
        "max_drawdown_pct": None,
        "sharpe_ratio": None,
        "profit_factor": None,
        "calmar_ratio": None,
        "incomplete": False,
        "low_activity": False,
    }

    bt = row.get("backtest_result")
    if not isinstance(bt, dict):
        return result

    net = bt.get("netProfitPct")
    cagr = bt.get("cagrPct") or bt.get("cagr")
    trade_count = bt.get("tradeCount")
    mdd = bt.get("maxDrawdownPct")
    sharpe = bt.get("sharpeRatio")
    profit_factor = bt.get("profitFactor")

    result["net_profit_pct"] = net
    result["trade_count"] = trade_count
    result["max_drawdown_pct"] = mdd
    result["sharpe_ratio"] = sharpe
    result["profit_factor"] = profit_factor

    if cagr is not None:
        result["cagr_pct"] = cagr
    elif net is not None and row.get("period_start") and row.get("period_end"):
        days = (row["period_end"] - row["period_start"]).days
        if days > 0:
            years = days / 365.25
            terminal = 1 + net / 100
            if terminal > 0:
                result["cagr_pct"] = (terminal ** (1 / years) - 1) * 100

    cagr_val = result["cagr_pct"]
    if cagr_val is not None and mdd is not None and mdd != 0:
        result["calmar_ratio"] = cagr_val / abs(mdd)

    if not row.get("report_link"):
        result["incomplete"] = True

    if trade_count is not None and trade_count < DEFAULT_LOW_ACTIVITY_THRESHOLD:
        result["low_activity"] = True

    return result


@router.get("", response_model=list[ResultRow])
def list_results() -> list[dict]:
    rows = run_query("""
        SELECT
            r.id AS run_id,
            r.strategy_version_id AS strategy_id,
            r.provider_symbol AS instrument,
            r.direction_mode AS direction,
            r.run_kind AS result_type,
            r.status,
            r.error_message,
            r.created_at,
            r.started_at,
            r.completed_at,
            sv.version_number AS strategy_version_number,
            sv.family_id AS strategy_family_id,
            sv.snapshot->>'name' AS strategy_name,
            sv.snapshot->>'category' AS category,
            bp.id AS profile_id,
            bp.family_id AS profile_family_id,
            bp.version_number AS profile_version_number,
            bp.name AS profile_name,
            b.timeframe,
            b.period_start,
            b.period_end,
            be.backtest_result,
            be.report_link,
            be.external_job_id
        FROM runs r
        JOIN strategy_versions sv ON r.strategy_version_id = sv.id
        JOIN batches b ON r.batch_id = b.id
        JOIN backtest_profiles bp ON b.backtest_profile_id = bp.id
        LEFT JOIN backtest_executions be ON r.backtest_execution_id = be.id
        ORDER BY r.created_at DESC
    """)
    out = []
    for r in rows:
        metrics = _extract_and_compute_metrics(r)
        out.append({
            "run_id": r["run_id"],
            "strategy_id": r["strategy_id"],
            "strategy_name": r["strategy_name"],
            "strategy_version_number": r["strategy_version_number"],
            "strategy_family_id": r["strategy_family_id"],
            "category": r["category"],
            "instrument": r["instrument"],
            "direction": r["direction"],
            "result_type": r["result_type"],
            "status": r["status"],
            "error_message": r.get("error_message"),
            "profile_id": r["profile_id"],
            "profile_name": r["profile_name"],
            "profile_version_number": r["profile_version_number"],
            "profile_family_id": r["profile_family_id"],
            "timeframe": r["timeframe"],
            "period_start": r["period_start"],
            "period_end": r.get("period_end"),
            "report_link": r.get("report_link"),
            "created_at": r["created_at"],
            "started_at": r.get("started_at"),
            "completed_at": r.get("completed_at"),
            **metrics,
        })
    return out
