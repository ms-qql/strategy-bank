"""PROJ-22: Regime-Analyse — Modellversionen, Zeitreihen, Kursdaten, Trades, Auswertungen."""

from __future__ import annotations

import bisect
import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from ..db import run_command, run_query, run_query_one, transaction
from ..schemas.hal_import import HalResultRead
from ..schemas.regime import (
    FetchTradesResponse,
    RegimeEvaluationRead,
    RegimeImportRequest,
    RegimeImportResponse,
    RegimeModelVersionCreate,
    RegimeModelVersionRead,
    RegimeSeriesDetailRead,
    RegimeSeriesRead,
    ResultTradeRead,
)
from ..services.bybit_client import fetch_klines
from ..services.regime_calculator import compute_regime_bars
from ..services.trader_dev import get_trades as trader_get_trades

router = APIRouter(prefix="/regime", tags=["regime"])

_REPORT_ID_RE = re.compile(r"/backtest/([\w-]+)")


def _extract_result_id(report_link: str | None) -> str | None:
    if not report_link:
        return None
    match = _REPORT_ID_RE.search(report_link)
    return match.group(1) if match else None


# ── Modellversionen ────────────────────────────────────────────────────────


@router.get("/models", response_model=list[RegimeModelVersionRead])
def list_models() -> list[dict]:
    return run_query("SELECT * FROM regime_model_versions ORDER BY created_at DESC")


@router.post("/models", response_model=RegimeModelVersionRead, status_code=201)
def create_model(body: RegimeModelVersionCreate) -> dict:
    if body.lower_threshold >= body.upper_threshold:
        raise HTTPException(422, "Die untere Schwelle muss kleiner als die obere Schwelle sein.")

    return run_command(
        """INSERT INTO regime_model_versions
           (id, name, course_source, zscore_length, hma_length, confirmation_candles, upper_threshold, lower_threshold)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING *""",
        [
            uuid4(), body.name, body.course_source, body.zscore_length, body.hma_length,
            body.confirmation_candles, body.upper_threshold, body.lower_threshold,
        ],
        returning=True,
    )


# ── Zeitreihen ─────────────────────────────────────────────────────────────


def _series_query() -> str:
    return """
        SELECT rs.*, rmv.name AS model_version_name,
               (SELECT COUNT(*) FROM regime_bars rb WHERE rb.series_id = rs.id) AS bar_count,
               (SELECT COUNT(*) FROM regime_bars rb WHERE rb.series_id = rs.id AND rb.regime = 'nicht verfügbar') AS unavailable_count
        FROM regime_series rs
        JOIN regime_model_versions rmv ON rmv.id = rs.model_version_id
    """


@router.get("/series", response_model=list[RegimeSeriesRead])
def list_series(asset: str | None = None, timeframe: str | None = None) -> list[dict]:
    sql = _series_query()
    params: list = []
    clauses: list[str] = []

    if asset:
        clauses.append("rs.asset = %s")
        params.append(asset)
    if timeframe:
        clauses.append("rs.timeframe = %s")
        params.append(timeframe)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)

    sql += " ORDER BY rs.created_at DESC"
    return run_query(sql, params)


@router.get("/series/{series_id}", response_model=RegimeSeriesDetailRead)
def get_series(series_id: UUID) -> dict:
    row = run_query_one(
        _series_query() + " WHERE rs.id = %s",
        [series_id],
    )
    if not row:
        raise HTTPException(404, "Zeitreihe nicht gefunden.")

    bars = run_query(
        "SELECT bar_time, regime FROM regime_bars WHERE series_id = %s ORDER BY bar_time",
        [series_id],
    )

    coverage_issues = _detect_coverage_issues(series_id, row)
    return {**row, "bars": bars, "coverage_issues": coverage_issues}


def _detect_coverage_issues(series_id: UUID, series: dict) -> list[dict]:
    issues: list[dict] = []
    bars = run_query(
        "SELECT bar_time FROM regime_bars WHERE series_id = %s ORDER BY bar_time",
        [series_id],
    )
    if not bars:
        return issues

    timeframe = series.get("timeframe", "4h")
    interval_seconds = _timeframe_seconds(timeframe)

    prev = bars[0]["bar_time"]
    for b in bars[1:]:
        expected = prev + timedelta(seconds=interval_seconds)
        diff = (b["bar_time"] - prev).total_seconds()
        if diff > interval_seconds * 1.5:
            issues.append({
                "issue_type": "gap",
                "detail": f"Lücke zwischen {prev.isoformat()} und {b['bar_time'].isoformat()} ({int(diff / interval_seconds)} Bars fehlen)",
            })
        elif diff < interval_seconds * 0.5:
            issues.append({
                "issue_type": "timeframe_mismatch",
                "detail": f"Zeitstempel zu nah: {prev.isoformat()} → {b['bar_time'].isoformat()} ({diff:.0f}s)",
            })
        prev = b["bar_time"]

    return issues


def _timeframe_seconds(tf: str) -> int:
    if tf == "1h":
        return 3600
    if tf == "4h":
        return 14400
    if tf == "1d":
        return 86400
    return 14400


def _compute_coverage_pct(
    bar_times: list[datetime],
    bar_regimes: list[str],
    period_start: datetime | None,
    period_end: datetime | None,
    interval_seconds: int,
) -> float:
    """Anteil des Backtest-Zeitraums mit verfuegbarem Regime (nicht der ganzen Serie)."""
    if period_start is not None and not isinstance(period_start, datetime):
        period_start = datetime.combine(period_start, datetime.min.time(), tzinfo=timezone.utc)
    if period_end is not None and not isinstance(period_end, datetime):
        period_end = datetime.combine(period_end, datetime.min.time(), tzinfo=timezone.utc)

    if not period_start or not period_end or period_end <= period_start:
        valid = sum(1 for r in bar_regimes if r != "nicht verfügbar")
        return round(valid / max(len(bar_regimes), 1) * 100, 2)

    expected_total = int((period_end - period_start).total_seconds() // interval_seconds) + 1
    lo = bisect.bisect_left(bar_times, period_start)
    hi = bisect.bisect_right(bar_times, period_end)
    valid_in_period = sum(1 for r in bar_regimes[lo:hi] if r != "nicht verfügbar")
    return round(valid_in_period / max(expected_total, 1) * 100, 2)


@router.post("/series/import", response_model=RegimeImportResponse, status_code=201)
def import_series(body: RegimeImportRequest) -> dict:
    mv = run_query_one("SELECT id FROM regime_model_versions WHERE id = %s", [body.model_version_id])
    if not mv:
        raise HTTPException(404, "Modellversion nicht gefunden.")

    series_id = _ensure_series(body.asset, body.timeframe, body.model_version_id, "BYBIT:BTCUSDT.P")

    inserted = 0
    skipped = 0
    for bar in body.bars:
        existing = run_query_one(
            "SELECT id FROM regime_bars WHERE series_id = %s AND bar_time = %s",
            [series_id, bar.bar_time],
        )
        if existing:
            skipped += 1
            continue
        run_command(
            "INSERT INTO regime_bars (id, series_id, bar_time, regime) VALUES (%s, %s, %s, %s)",
            [uuid4(), series_id, bar.bar_time, bar.regime],
        )
        inserted += 1

    _update_series_period(series_id)
    return {"series_id": series_id, "bars_inserted": inserted, "bars_skipped": skipped}


@router.post("/series/{series_id}/refresh", response_model=RegimeSeriesDetailRead)
def refresh_series(series_id: UUID, period_start: str | None = None, period_end: str | None = None) -> dict:
    series = run_query_one(
        "SELECT rs.* FROM regime_series rs WHERE rs.id = %s",
        [series_id],
    )
    if not series:
        raise HTTPException(404, "Zeitreihe nicht gefunden.")

    mv = run_query_one(
        "SELECT * FROM regime_model_versions WHERE id = %s",
        [series["model_version_id"]],
    )
    if not mv:
        raise HTTPException(404, "Modellversion nicht gefunden.")

    asset = series["asset"]
    timeframe = series["timeframe"]

    p_start = period_start or "2021-01-01"
    p_end = period_end or "2024-12-31"

    start_ms = int(datetime.fromisoformat(p_start).timestamp() * 1000)
    end_ms = int(datetime.fromisoformat(p_end).timestamp() * 1000)

    symbol = _asset_to_bybit_symbol(asset)

    klines = fetch_klines(symbol, timeframe, start_ms, end_ms)

    with transaction() as cur:
        for k in klines:
            cur.execute(
                """INSERT INTO price_bars (id, asset, timeframe, bar_time, open, high, low, close)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (asset, timeframe, bar_time) DO NOTHING""",
                [uuid4(), asset, timeframe, k["bar_time"], k["open"], k["high"], k["low"], k["close"]],
            )

    pb_rows = run_query(
        "SELECT bar_time, close FROM price_bars WHERE asset = %s AND timeframe = %s AND bar_time >= %s AND bar_time <= %s ORDER BY bar_time",
        [asset, timeframe, datetime.fromisoformat(p_start), datetime.fromisoformat(p_end)],
    )

    closes = [float(r["close"]) for r in pb_rows]
    bar_times = [r["bar_time"] for r in pb_rows]

    regime_bars = compute_regime_bars(
        closes, bar_times,
        zscore_length=mv["zscore_length"],
        hma_length=mv["hma_length"],
        confirmation_candles=mv["confirmation_candles"],
        upper_threshold=float(mv["upper_threshold"]),
        lower_threshold=float(mv["lower_threshold"]),
    )

    run_command("DELETE FROM regime_bars WHERE series_id = %s", [series_id])
    for rb in regime_bars:
        run_command(
            "INSERT INTO regime_bars (id, series_id, bar_time, regime) VALUES (%s, %s, %s, %s)",
            [uuid4(), series_id, rb["bar_time"], rb["regime"]],
        )

    run_command(
        "UPDATE regime_series SET period_start = %s, period_end = %s, last_refreshed_at = %s WHERE id = %s",
        [datetime.fromisoformat(p_start), datetime.fromisoformat(p_end), datetime.now(timezone.utc), series_id],
    )

    return get_series(series_id)


# ── Trade-Nachladung ───────────────────────────────────────────────────────


@router.post("/hal-results/{result_id}/trades/fetch", response_model=FetchTradesResponse)
def fetch_trades(result_id: UUID) -> dict:
    hal = run_query_one("SELECT id, report_link FROM hal_results WHERE id = %s", [result_id])
    if not hal:
        raise HTTPException(404, "HAL-Ergebnis nicht gefunden.")

    if not hal["report_link"]:
        raise HTTPException(400, "Kein Report-Link vorhanden. Trades können nicht geladen werden.")

    td_result_id = _extract_result_id(hal["report_link"])
    if not td_result_id:
        raise HTTPException(400, "Konnte keine trader.dev-Result-ID aus dem Report-Link extrahieren.")

    trades = trader_get_trades(td_result_id)

    count = 0
    for t in trades:
        existing = run_query_one(
            """SELECT id FROM result_trades
               WHERE hal_result_id = %s AND direction = %s AND entry_time = %s AND exit_time = %s""",
            [result_id, t.get("direction", "long"), t.get("entryTime"), t.get("exitTime")],
        )
        if existing:
            continue
        run_command(
            """INSERT INTO result_trades (id, hal_result_id, direction, entry_time, exit_time, net_pnl, data_source)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            [
                uuid4(), result_id, t.get("direction", "long"),
                t.get("entryTime"), t.get("exitTime"),
                float(t.get("netPnl", 0)), "trader_dev",
            ],
        )
        count += 1

    return {"hal_result_id": result_id, "trades_count": count}


@router.get("/hal-results/{result_id}/trades", response_model=list[ResultTradeRead])
def list_trades(result_id: UUID) -> list[dict]:
    hal = run_query_one("SELECT id FROM hal_results WHERE id = %s", [result_id])
    if not hal:
        raise HTTPException(404, "HAL-Ergebnis nicht gefunden.")
    return run_query(
        "SELECT * FROM result_trades WHERE hal_result_id = %s ORDER BY entry_time",
        [result_id],
    )


# ── Regime-Auswertung ──────────────────────────────────────────────────────


@router.get("/hal-results/{result_id}/regime", response_model=RegimeEvaluationRead)
def get_regime_evaluation(result_id: UUID, model_version_id: UUID | None = None) -> dict:
    hal = run_query_one("SELECT * FROM hal_results WHERE id = %s", [result_id])
    if not hal:
        raise HTTPException(404, "HAL-Ergebnis nicht gefunden.")

    trades = run_query(
        "SELECT * FROM result_trades WHERE hal_result_id = %s ORDER BY entry_time",
        [result_id],
    )
    if not trades:
        raise HTTPException(400, "Regime-Auswertung nicht möglich: Zeitgestempelte Ergebnisdaten fehlen.")

    mv_id = model_version_id
    if mv_id is None:
        latest_mv = run_query_one("SELECT id FROM regime_model_versions ORDER BY created_at DESC LIMIT 1")
        if not latest_mv:
            raise HTTPException(404, "Keine Modellversion vorhanden.")
        mv_id = latest_mv["id"]

    mv = run_query_one("SELECT * FROM regime_model_versions WHERE id = %s", [mv_id])
    if not mv:
        raise HTTPException(404, "Modellversion nicht gefunden.")

    asset = hal["asset"]
    timeframe = hal["timeframe"]

    series = run_query_one(
        "SELECT id FROM regime_series WHERE asset = %s AND timeframe = %s AND model_version_id = %s",
        [asset, timeframe, mv_id],
    )
    if not series:
        raise HTTPException(404, f"Keine Regime-Zeitreihe für {asset} {timeframe} mit Modellversion {mv['name']}.")

    active_regime_bars = _compute_regime_eval(
        series["id"], hal["id"], mv_id, trades, timeframe, hal["period_start"], hal["period_end"],
    )
    return active_regime_bars


def _find_bar_regime(bar_times: list[datetime], bar_regimes: list[str], entry_time: datetime, interval_seconds: int) -> str:
    """Regime der Bar, die den Einstiegszeitpunkt umschliesst (groesste bar_time <= entry_time)."""
    idx = bisect.bisect_right(bar_times, entry_time) - 1
    if idx < 0:
        return "ohne Regimezuordnung"
    bar_time = bar_times[idx]
    if (entry_time - bar_time).total_seconds() >= interval_seconds:
        return "ohne Regimezuordnung"  # Luecke: naechste Bar zu weit entfernt
    return bar_regimes[idx]


def _compute_regime_eval(
    series_id: UUID,
    hal_result_id: UUID,
    mv_id: UUID,
    trades: list[dict],
    timeframe: str,
    period_start: datetime | None,
    period_end: datetime | None,
) -> dict:
    bars = run_query(
        "SELECT bar_time, regime FROM regime_bars WHERE series_id = %s ORDER BY bar_time",
        [series_id],
    )
    bar_times = [b["bar_time"] for b in bars]
    bar_regimes = [b["regime"] for b in bars]
    interval_seconds = _timeframe_seconds(timeframe)

    regime_pnl: dict[str, float] = {"bullish": 0.0, "bearish": 0.0, "sideways": 0.0, "ohne Regimezuordnung": 0.0}
    regime_count: dict[str, int] = {"bullish": 0, "bearish": 0, "sideways": 0, "ohne Regimezuordnung": 0}
    regime_equity: dict[str, list[float]] = {"bullish": [], "bearish": [], "sideways": [], "ohne Regimezuordnung": []}
    total_pnl = 0.0

    for t in trades:
        regime = _find_bar_regime(bar_times, bar_regimes, t["entry_time"], interval_seconds)
        if regime == "nicht verfügbar":
            regime = "ohne Regimezuordnung"
        pnl = float(t["net_pnl"])
        regime_pnl[regime] += pnl
        regime_count[regime] += 1
        total_pnl += pnl
        if regime != "ohne Regimezuordnung":
            regime_equity[regime].append(pnl)

    coverage_pct = _compute_coverage_pct(bar_times, bar_regimes, period_start, period_end, interval_seconds)
    is_incomplete = coverage_pct < 95

    # Build detail rows
    details = []
    for regime in ["bullish", "bearish", "sideways", "ohne Regimezuordnung"]:
        detail = _build_detail_row(regime, regime_pnl[regime], regime_count[regime], total_pnl, regime_equity.get(regime, []))
        details.append(detail)

    # Regime-Dominanz
    dominance = None
    if total_pnl > 0:
        positive_pnl = sum(max(v, 0) for v in regime_pnl.values())
        for regime in ["bullish", "bearish", "sideways"]:
            if regime_pnl[regime] > 0 and positive_pnl > 0:
                share = regime_pnl[regime] / positive_pnl
                if share > 0.7:
                    dominance = regime
                    break

    eval_id = uuid4()
    existing_eval = run_query_one(
        "SELECT id FROM regime_evaluations WHERE hal_result_id = %s AND model_version_id = %s",
        [hal_result_id, mv_id],
    )

    with transaction() as cur:
        if existing_eval:
            cur.execute("DELETE FROM regime_eval_details WHERE evaluation_id = %s", [existing_eval["id"]])
            cur.execute(
                """UPDATE regime_evaluations SET coverage_pct = %s, is_incomplete = %s,
                   total_result_pnl = %s WHERE id = %s""",
                [coverage_pct, is_incomplete, total_pnl, existing_eval["id"]],
            )
            eid = existing_eval["id"]
        else:
            cur.execute(
                """INSERT INTO regime_evaluations (id, hal_result_id, series_id, model_version_id, coverage_pct,
                   assignment_rule, is_incomplete, total_result_pnl)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                [eval_id, hal_result_id, series_id, mv_id, coverage_pct, "entry_bar_regime", is_incomplete, total_pnl],
            )
            eid = eval_id

        for d in details:
            cur.execute(
                """INSERT INTO regime_eval_details (id, evaluation_id, regime, trade_count, net_pnl,
                   max_drawdown_pct, pnl_share_pct, calmar_ratio, sortino_ratio, small_sample)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                [
                    uuid4(), eid, d["regime"], d["trade_count"], d["net_pnl"],
                    d["max_drawdown_pct"], d["pnl_share_pct"], d["calmar_ratio"], d["sortino_ratio"], d["small_sample"],
                ],
            )

    mv_row = run_query_one("SELECT name FROM regime_model_versions WHERE id = %s", [mv_id])
    return {
        "id": eid,
        "hal_result_id": hal_result_id,
        "series_id": series_id,
        "model_version_id": mv_id,
        "model_version_name": mv_row["name"] if mv_row else None,
        "coverage_pct": coverage_pct,
        "assignment_rule": "entry_bar_regime",
        "is_incomplete": is_incomplete,
        "total_result_pnl": round(total_pnl, 2),
        "regime_details": details,
        "regime_dominance": dominance,
        "created_at": datetime.now(timezone.utc),
    }


def _build_detail_row(regime: str, pnl: float, count: int, total_pnl: float, equities: list[float]) -> dict:
    pnl_share = round(pnl / total_pnl * 100, 2) if total_pnl != 0 else 0.0
    max_dd = _max_drawdown(equities) if equities and regime != "ohne Regimezuordnung" else None
    calmar = round(pnl / abs(max_dd), 2) if max_dd and abs(max_dd) > 0 else None
    sortino = _sortino(equities) if len(equities) >= 6 else None
    small_sample = count < 6

    return {
        "regime": regime,
        "trade_count": count,
        "net_pnl": round(pnl, 2),
        "max_drawdown_pct": round(max_dd, 2) if max_dd is not None else None,
        "pnl_share_pct": pnl_share,
        "calmar_ratio": calmar,
        "sortino_ratio": round(sortino, 2) if sortino is not None else None,
        "small_sample": small_sample,
    }


def _max_drawdown(equity_curve: list[float]) -> float:
    peak = 0.0
    dd = 0.0
    cumulative = 0.0
    for e in equity_curve:
        cumulative += e
        peak = max(peak, cumulative)
        dd = min(dd, cumulative - peak)
    return dd


def _sortino(returns: list[float]) -> float:
    mean = sum(returns) / len(returns)
    downside = [min(r - mean, 0) ** 2 for r in returns]
    downside_std = (sum(downside) / len(downside)) ** 0.5
    return mean / downside_std if downside_std > 0 else 0.0


# ── Hilfsfunktionen ────────────────────────────────────────────────────────


def _ensure_series(asset: str, timeframe: str, model_version_id: UUID, provider_symbol: str) -> UUID:
    existing = run_query_one(
        "SELECT id FROM regime_series WHERE provider_symbol = %s AND asset = %s AND timeframe = %s AND model_version_id = %s",
        [provider_symbol, asset, timeframe, model_version_id],
    )
    if existing:
        return UUID(str(existing["id"]))

    row = run_command(
        """INSERT INTO regime_series (id, provider_symbol, asset, timeframe, model_version_id)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        [uuid4(), provider_symbol, asset, timeframe, model_version_id],
        returning=True,
    )
    return UUID(str(row["id"]))


def _update_series_period(series_id: UUID) -> None:
    rows = run_query(
        "SELECT MIN(bar_time) AS period_start, MAX(bar_time) AS period_end FROM regime_bars WHERE series_id = %s",
        [series_id],
    )
    if rows and rows[0]["period_start"]:
        run_command(
            "UPDATE regime_series SET period_start = %s, period_end = %s WHERE id = %s",
            [rows[0]["period_start"], rows[0]["period_end"], series_id],
        )


def _asset_to_bybit_symbol(asset: str) -> str:
    if asset.upper() == "BTC":
        return "BTCUSDT"
    if asset.upper() == "ETH":
        return "ETHUSDT"
    return f"{asset.upper()}USDT"
