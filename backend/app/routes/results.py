"""PROJ-7+21: Ergebnisvergleich — liefert interne Runs UND HAL-Importe."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter

from ..db import run_query
from ..schemas.hal_import import (
    SUCCESS_GROUP_CALMAR_MIN,
    SUCCESS_GROUP_MIN_TRADES_PER_YEAR,
    SUCCESS_GROUP_SORTINO_MIN,
)
from ..schemas.results import ResultRow

router = APIRouter(prefix="/results", tags=["results"])


def _compute_calmar(cagr_pct: float | None, mdd: float | None) -> float | None:
    if cagr_pct is not None and mdd is not None and mdd != 0:
        return float(cagr_pct) / float(abs(mdd))
    return None


def _compute_cagr(net_return_pct: float | None, period_start: date | None, period_end: date | None) -> float | None:
    if net_return_pct is None or not period_start or not period_end:
        return None
    days = (period_end - period_start).days
    if days <= 0:
        return None
    years = days / 365.25
    terminal = 1 + float(net_return_pct) / 100
    if terminal <= 0:
        return None
    return (terminal ** (1 / years) - 1) * 100


def _compute_trades_per_year(trade_count: int | None, period_start: date | None, period_end: date | None) -> float | None:
    if trade_count is None or not period_start or not period_end:
        return None
    days = (period_end - period_start).days
    if days <= 0:
        return None
    years = days / 365.25
    return trade_count / years


def _extract_and_compute_metrics(row: dict) -> dict:
    """Extrahiert Metriken aus backtest_result JSONB, berechnet CAGR-Fallback und
    Calmar, setzt Kennzeichen incomplete/low_activity."""
    result: dict = {
        "net_profit_pct": None,
        "cagr_pct": None,
        "trade_count": None,
        "max_drawdown_pct": None,
        "sharpe_ratio": None,
        "sortino_ratio": None,
        "profit_factor": None,
        "calmar_ratio": None,
        "trades_per_year": None,
        "incomplete": False,
        "low_activity": False,
        "is_comparable": True,
        "success_group": False,
        "shortlisted": False,
    }

    bt = row.get("backtest_result")
    if not isinstance(bt, dict):
        return result

    net = bt.get("netProfitPct")
    cagr = bt.get("cagrPct") or bt.get("cagr")
    trade_count = bt.get("tradeCount")
    mdd = bt.get("maxDrawdownPct")
    sharpe = bt.get("sharpeRatio")
    sortino = bt.get("sortinoRatio")
    profit_factor = bt.get("profitFactor")

    result["net_profit_pct"] = net
    result["trade_count"] = trade_count
    result["max_drawdown_pct"] = mdd
    result["sharpe_ratio"] = sharpe
    result["sortino_ratio"] = sortino
    result["profit_factor"] = profit_factor

    if cagr is not None:
        result["cagr_pct"] = cagr
    else:
        result["cagr_pct"] = _compute_cagr(net, row.get("period_start"), row.get("period_end"))

    result["calmar_ratio"] = _compute_calmar(result["cagr_pct"], mdd)
    result["trades_per_year"] = _compute_trades_per_year(
        trade_count, row.get("period_start"), row.get("period_end")
    )

    if not row.get("report_link"):
        result["incomplete"] = True

    tp = result["trades_per_year"]
    if tp is not None and tp < SUCCESS_GROUP_MIN_TRADES_PER_YEAR:
        result["low_activity"] = True

    if (
        result["is_comparable"]
        and result["calmar_ratio"] is not None and result["calmar_ratio"] >= SUCCESS_GROUP_CALMAR_MIN
        and result["sortino_ratio"] is not None and result["sortino_ratio"] >= SUCCESS_GROUP_SORTINO_MIN
        and tp is not None and tp >= SUCCESS_GROUP_MIN_TRADES_PER_YEAR
    ):
        result["success_group"] = True

    return result


def _build_run_row(r: dict) -> dict:
    metrics = _extract_and_compute_metrics(r)
    sv = r.get("strategy_version_id")
    is_shortlisted = False
    if sv:
        sl = run_query("SELECT 1 FROM shortlist WHERE strategy_version_id = %s", [sv])
        is_shortlisted = bool(sl)

    return {
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
        "shortlisted": is_shortlisted,
        **metrics,
    }


@router.get("", response_model=list[ResultRow])
def list_results() -> list[dict]:
    run_rows = run_query("""
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
    """)

    hal_rows = run_query("""
        SELECT
            hr.id AS run_id,
            hr.strategy_version_id AS strategy_id,
            hr.asset AS instrument,
            hr.direction,
            'HAL-Import' AS result_type,
            NULL AS status,
            NULL AS error_message,
            hr.created_at,
            NULL::TIMESTAMPTZ AS started_at,
            NULL::TIMESTAMPTZ AS completed_at,
            CAST(NULL AS INT) AS strategy_version_number,
            CAST(NULL AS UUID) AS strategy_family_id,
            hr.strategy_name,
            CAST(NULL AS TEXT) AS category,
            CAST(NULL AS UUID) AS profile_id,
            CAST(NULL AS UUID) AS profile_family_id,
            CAST(NULL AS INT) AS profile_version_number,
            CAST(NULL AS TEXT) AS profile_name,
            hr.timeframe,
            hr.period_start,
            hr.period_end,
            NULL::JSONB AS backtest_result,
            hr.report_link,
            CAST(NULL AS TEXT) AS external_job_id,
            hr.sortino_ratio,
            hr.sharpe_ratio,
            hr.profit_factor,
            hr.net_return_pct,
            hr.max_drawdown_pct,
            hr.trade_count,
            hr.fee_pct,
            hr.slippage_ticks,
            hr.sizing_model,
            hif.origin_path,
            hif.content_hash,
            hif.import_version,
            hif.created_at AS import_created_at
        FROM hal_results hr
        JOIN hal_imported_files hif ON hif.id = hr.imported_file_id
        WHERE hif.is_current = true
    """)

    out = []

    for r in run_rows:
        out.append(_build_run_row(r))

    for r in hal_rows:
        out.append(_build_hal_result_row(r))

    out.sort(key=lambda x: x["created_at"], reverse=True)
    return out


def _build_hal_result_row(r: dict) -> dict:
    net = r.get("net_return_pct")
    mdd_raw = r.get("max_drawdown_pct")
    mdd = float(mdd_raw) if mdd_raw is not None else None
    tc = r.get("trade_count")

    cagr = r.get("cagr_pct")
    if cagr is None:
        cagr = _compute_cagr(net, r.get("period_start"), r.get("period_end"))

    calmar = _compute_calmar(cagr if cagr is not None else r.get("cagr_pct"), mdd)
    tp = _compute_trades_per_year(tc, r.get("period_start"), r.get("period_end"))

    is_comparable = bool(
        r.get("fee_pct") is not None
        and r.get("slippage_ticks") is not None
        and r.get("sizing_model") is not None
    )
    low_activity = tp is not None and tp < SUCCESS_GROUP_MIN_TRADES_PER_YEAR
    success_group = (
        is_comparable
        and calmar is not None and calmar >= SUCCESS_GROUP_CALMAR_MIN
        and r.get("sortino_ratio") is not None and r["sortino_ratio"] >= SUCCESS_GROUP_SORTINO_MIN
        and tp is not None and tp >= SUCCESS_GROUP_MIN_TRADES_PER_YEAR
    )

    sv_id = r.get("strategy_id")
    shortlisted = False
    strategy_version_status = None
    if sv_id:
        sl = run_query("SELECT 1 FROM shortlist WHERE strategy_version_id = %s", [sv_id])
        shortlisted = bool(sl)
        sv = run_query("SELECT id FROM strategy_versions WHERE id = %s", [sv_id])
        if not sv:
            strategy_version_status = "Strategieversion nicht verfügbar"

    return {
        "run_id": r["run_id"],
        "strategy_id": r.get("strategy_id"),
        "strategy_name": r.get("strategy_name", ""),
        "strategy_version_number": r.get("strategy_version_number"),
        "strategy_family_id": r.get("strategy_family_id"),
        "category": r.get("category"),
        "instrument": r.get("instrument", ""),
        "direction": r.get("direction"),
        "result_type": r.get("result_type", "HAL-Import"),
        "status": r.get("status"),
        "error_message": r.get("error_message"),
        "profile_id": r.get("profile_id"),
        "profile_name": r.get("profile_name"),
        "profile_version_number": r.get("profile_version_number"),
        "profile_family_id": r.get("profile_family_id"),
        "timeframe": r.get("timeframe", ""),
        "period_start": r.get("period_start"),
        "period_end": r.get("period_end"),
        "net_profit_pct": float(net) if net is not None else None,
        "cagr_pct": float(cagr) if cagr is not None else None,
        "trade_count": int(tc) if tc is not None else None,
        "max_drawdown_pct": mdd,
        "sharpe_ratio": float(r["sharpe_ratio"]) if r.get("sharpe_ratio") is not None else None,
        "sortino_ratio": float(r["sortino_ratio"]) if r.get("sortino_ratio") is not None else None,
        "profit_factor": float(r["profit_factor"]) if r.get("profit_factor") is not None else None,
        "calmar_ratio": calmar,
        "trades_per_year": tp,
        "is_comparable": is_comparable,
        "success_group": success_group,
        "shortlisted": shortlisted,
        "report_link": r.get("report_link"),
        "incomplete": not r.get("report_link"),
        "low_activity": low_activity or (tc is not None and tc == 0),
        "import_origin_path": r.get("origin_path"),
        "import_hash": r.get("content_hash"),
        "import_version": r.get("import_version"),
        "import_created_at": r.get("import_created_at"),
        "strategy_version_status": strategy_version_status,
        "source_name": None,
        "mts_compatibility": None,
        "robustness_status": None,
        "created_at": r.get("created_at"),
        "started_at": r.get("started_at"),
        "completed_at": r.get("completed_at"),
    }
