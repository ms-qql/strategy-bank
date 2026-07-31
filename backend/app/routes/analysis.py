"""PROJ-23: Erfolgsfaktorenanalyse — Analyseläufe und Kohortenberechnung."""

import json
import statistics
from collections import Counter
from datetime import date
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from ..db import run_command, run_query, run_query_one, transaction
from ..schemas.analysis import (
    AnalysisRunDetailRead,
    AnalysisRunRead,
    CohortRow,
)
from ..schemas.hal_import import (
    SUCCESS_GROUP_CALMAR_MIN,
    SUCCESS_GROUP_MIN_TRADES_PER_YEAR,
    SUCCESS_GROUP_SORTINO_MIN,
)
from ..services.pine_features import extract_pine_features

router = APIRouter(prefix="/analysis/runs", tags=["analysis"])

AXIS_FIELDS = {
    "indicator",
    "indicator_count",
    "parameter_count",
    "entry_archetype",
    "exit_archetype",
    "category",
    "direction",
    "mts_compatibility",
}


def _compute_calmar(cagr_pct: float | None, mdd: float | None) -> float | None:
    if cagr_pct is not None and mdd is not None and mdd != 0:
        return float(cagr_pct) / float(abs(mdd))
    return None


def _compute_cagr(net_return_pct: float | None, ps: date | None, pe: date | None) -> float | None:
    if net_return_pct is None or not ps or not pe:
        return None
    days = (pe - ps).days
    if days <= 0:
        return None
    years = days / 365.25
    terminal = 1 + float(net_return_pct) / 100
    if terminal <= 0:
        return None
    return (terminal ** (1 / years) - 1) * 100


def _compute_trades_per_year(trade_count: int | None, ps: date | None, pe: date | None) -> float | None:
    if trade_count is None or not ps or not pe:
        return None
    days = (pe - ps).days
    if days <= 0:
        return None
    years = days / 365.25
    return trade_count / years


def _build_comparison_group(row: dict) -> str:
    return (
        f"{row['asset']} · {row['timeframe']} · "
        f"{row['period_start']}–{row['period_end']} · "
        f"Fee {float(row['fee_pct']):g}% · Slip {float(row['slippage_ticks']):g} · "
        f"{row['sizing_model']}"
    )


@router.post("", response_model=AnalysisRunRead, status_code=201)
def create_analysis_run() -> dict:
    comparable = run_query("""
        SELECT
            hr.id AS hal_result_id,
            hr.strategy_name,
            hr.strategy_version_id,
            hr.pine_code,
            hr.net_return_pct,
            hr.max_drawdown_pct,
            hr.cagr_pct,
            hr.sortino_ratio,
            hr.trade_count,
            hr.period_start,
            hr.period_end,
            hr.asset,
            hr.timeframe,
            hr.fee_pct,
            hr.slippage_ticks,
            hr.sizing_model,
            hr.direction,
            hr.created_at,
            sv.snapshot->>'category' AS category,
            sv.snapshot->>'mts_compatibility' AS mts_compatibility
        FROM hal_results hr
        JOIN hal_imported_files hif ON hif.id = hr.imported_file_id
        LEFT JOIN strategy_versions sv ON sv.id = hr.strategy_version_id
        WHERE hif.is_current = true
          AND hr.pine_code IS NOT NULL
          AND hr.pine_code != ''
          AND hr.fee_pct IS NOT NULL
          AND hr.slippage_ticks IS NOT NULL
          AND hr.sizing_model IS NOT NULL
        ORDER BY hr.created_at DESC
    """)

    excluded_no_pine = run_query_one(
        """SELECT COUNT(*)::int AS cnt
           FROM hal_results hr
           JOIN hal_imported_files hif ON hif.id = hr.imported_file_id
           WHERE hif.is_current = true
             AND (hr.pine_code IS NULL OR hr.pine_code = '')"""
    )
    excluded_no_profile = run_query_one(
        """SELECT COUNT(*)::int AS cnt
           FROM hal_results hr
           JOIN hal_imported_files hif ON hif.id = hr.imported_file_id
           WHERE hif.is_current = true
             AND hr.pine_code IS NOT NULL AND hr.pine_code != ''
             AND (hr.fee_pct IS NULL OR hr.slippage_ticks IS NULL OR hr.sizing_model IS NULL)"""
    )

    excluded_reasons = {}
    if excluded_no_pine and excluded_no_pine["cnt"]:
        excluded_reasons["ohne Pine-Code"] = excluded_no_pine["cnt"]
    if excluded_no_profile and excluded_no_profile["cnt"]:
        excluded_reasons["nicht vergleichbar"] = excluded_no_profile["cnt"]

    if not comparable:
        raise HTTPException(400, "Keine vergleichbaren Ergebnisse mit Pine-Code gefunden.")

    groups: dict[str, list[dict]] = {}
    for row in comparable:
        cg = _build_comparison_group(row)
        groups.setdefault(cg, []).append(row)

    main_group = max(groups, key=lambda g: len(groups[g]))
    candidates = groups[main_group]

    # `comparable` is ORDER BY created_at DESC, so first occurrence per version = newest import.
    seen_sv: set[UUID] = set()
    deduped: list[dict] = []
    for row in candidates:
        sv_id = row["strategy_version_id"]
        if sv_id is not None:
            if sv_id in seen_sv:
                continue
            seen_sv.add(sv_id)
        deduped.append(row)

    excluded_reasons["andere Vergleichsgruppe"] = sum(
        len(rows) for g, rows in groups.items() if g != main_group
    )

    run_id = uuid4()
    success_definition = {
        "calmar_min": SUCCESS_GROUP_CALMAR_MIN,
        "sortino_min": SUCCESS_GROUP_SORTINO_MIN,
        "min_trades_per_year": SUCCESS_GROUP_MIN_TRADES_PER_YEAR,
    }

    with transaction() as cur:
        cur.execute(
            """INSERT INTO analysis_runs (id, comparison_group, success_definition,
               total_analyzed, total_excluded, excluded_reasons)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [
                run_id,
                main_group,
                json.dumps(success_definition),
                len(deduped),
                sum(excluded_reasons.values()),
                json.dumps(excluded_reasons),
            ],
        )

        for row in deduped:
            features = extract_pine_features(row["pine_code"])

            cagr = row.get("cagr_pct")
            if cagr is None:
                cagr = _compute_cagr(
                    row["net_return_pct"],
                    row["period_start"],
                    row["period_end"],
                )
            calmar = _compute_calmar(cagr, row["max_drawdown_pct"])
            tp = _compute_trades_per_year(
                row["trade_count"],
                row["period_start"],
                row["period_end"],
            )

            is_success = (
                calmar is not None
                and calmar >= SUCCESS_GROUP_CALMAR_MIN
                and row["sortino_ratio"] is not None
                and row["sortino_ratio"] >= SUCCESS_GROUP_SORTINO_MIN
                and tp is not None
                and tp >= SUCCESS_GROUP_MIN_TRADES_PER_YEAR
            )

            cur.execute(
                """INSERT INTO analysis_run_rows (
                   id, analysis_run_id, hal_result_id, strategy_name,
                   strategy_version_id, calmar_ratio, sortino_ratio,
                   trades_per_year, is_success, indicators, indicator_count,
                   parameter_count, entry_archetype, exit_archetype,
                   category, direction, mts_compatibility
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                [
                    uuid4(),
                    run_id,
                    row["hal_result_id"],
                    row["strategy_name"],
                    row["strategy_version_id"],
                    calmar,
                    row["sortino_ratio"],
                    tp,
                    is_success,
                    json.dumps(features.indicators),
                    features.indicator_count,
                    features.parameter_count,
                    features.entry_archetype,
                    features.exit_archetype,
                    row.get("category"),
                    row.get("direction"),
                    row.get("mts_compatibility"),
                ],
            )

    result = run_query_one("SELECT * FROM analysis_runs WHERE id = %s", [run_id])
    return result


@router.get("", response_model=list[AnalysisRunRead])
def list_analysis_runs(limit: int = 20) -> list[dict]:
    limit = min(max(limit, 1), 100)
    return run_query(
        "SELECT * FROM analysis_runs ORDER BY created_at DESC LIMIT %s",
        [limit],
    )


@router.get("/{run_id}", response_model=AnalysisRunDetailRead)
def get_analysis_run(run_id: UUID, axis: str = "indicator") -> dict:
    valid_axes = AXIS_FIELDS
    if axis not in valid_axes:
        raise HTTPException(400, f"Ungültige Achse. Gültig: {', '.join(sorted(valid_axes))}")

    run = run_query_one("SELECT * FROM analysis_runs WHERE id = %s", [run_id])
    if not run:
        raise HTTPException(404, "Analyselauf nicht gefunden.")

    rows_raw = run_query(
        "SELECT * FROM analysis_run_rows WHERE analysis_run_id = %s ORDER BY strategy_name",
        [run_id],
    )

    rows: list[dict] = []
    for r in rows_raw:
        rows.append({
            **r,
            "indicators": r["indicators"] if isinstance(r["indicators"], list) else json.loads(r["indicators"] or "[]"),
        })

    cohort = _build_cohort(rows, axis)

    return {
        **run,
        "excluded_reasons": run["excluded_reasons"] if isinstance(run["excluded_reasons"], dict) else json.loads(run["excluded_reasons"] or "{}"),
        "success_definition": run["success_definition"] if isinstance(run["success_definition"], dict) else json.loads(run["success_definition"] or "{}"),
        "rows": rows,
        "cohort": cohort,
    }


def _build_cohort(rows: list[dict], axis: str) -> list[dict]:
    total_all = len(rows)
    total_success = sum(1 for r in rows if r["is_success"])

    if axis == "indicator":
        return _build_indicator_cohort(rows, total_all, total_success)
    return _build_field_cohort(rows, axis, total_all, total_success)


def _build_indicator_cohort(rows: list[dict], total_all: int, total_success: int) -> list[dict]:
    indicator_success: Counter[str] = Counter()
    indicator_total: Counter[str] = Counter()
    indicator_calmar: dict[str, list[float]] = {}

    for r in rows:
        indicators = r.get("indicators", []) or []
        for ind in indicators:
            indicator_total[ind] += 1
            if r["is_success"]:
                indicator_success[ind] += 1
            if r.get("calmar_ratio") is not None:
                indicator_calmar.setdefault(ind, []).append(r["calmar_ratio"])

    result: list[dict] = []
    for ind in sorted(indicator_total.keys()):
        success = indicator_success.get(ind, 0)
        total = indicator_total[ind]
        result.append(_cohort_row(ind, success, total, total_all, total_success, indicator_calmar.get(ind)))
    return result


def _build_field_cohort(rows: list[dict], axis: str, total_all: int, total_success: int) -> list[dict]:
    field_success: Counter[str] = Counter()
    field_total: Counter[str] = Counter()
    field_calmar: dict[str, list[float]] = {}

    for r in rows:
        val = r.get(axis)
        if isinstance(val, (int, float)):
            val = str(val)
        if val is None:
            val = "nicht verfügbar"
        field_total[val] += 1
        if r["is_success"]:
            field_success[val] += 1
        if r.get("calmar_ratio") is not None:
            field_calmar.setdefault(val, []).append(r["calmar_ratio"])

    result: list[dict] = []
    for val in sorted(field_total.keys()):
        success = field_success.get(val, 0)
        total = field_total[val]
        result.append(_cohort_row(val, success, total, total_all, total_success, field_calmar.get(val)))
    return result


def _cohort_row(
    value: str,
    success: int,
    total: int,
    total_all: int,
    total_success: int,
    calmar_values: list[float] | None,
) -> dict:
    quote = None
    lift = None
    median_calmar = None

    if total > 0:
        quote = success / total

    if total_success > 0 and total_all > 0:
        feature_success_share = success / total_success if total_success > 0 else 0
        feature_total_share = total / total_all
        if feature_total_share > 0:
            lift = feature_success_share / feature_total_share

    if calmar_values:
        median_calmar = statistics.median(calmar_values)

    return {
        "value": value,
        "success": success,
        "total": total,
        "success_quote": quote,
        "lift": lift,
        "median_calmar": median_calmar,
    }


@router.delete("/{run_id}", status_code=204)
def delete_analysis_run(run_id: UUID) -> None:
    existing = run_query_one("SELECT 1 FROM analysis_runs WHERE id = %s", [run_id])
    if not existing:
        raise HTTPException(404, "Analyselauf nicht gefunden.")
    run_command("DELETE FROM analysis_runs WHERE id = %s", [run_id])
