"""PROJ-9: Markdown-Export — erzeugt eine .md-Datei der gesamten Strategiefamilie."""

import json
import re
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ..db import run_query, run_query_one

router = APIRouter(tags=["export"])


def _escape_md(text: str | None) -> str:
    if not text:
        return ""
    t = str(text).replace("|", "\\|")
    t = t.replace("\n", "<br>")
    return t


def _fmt_num(val) -> str:
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


def _safe_filename(name: str) -> str:
    safe = re.sub(r"[^\w\s-]", "", name)
    safe = re.sub(r"\s+", "_", safe)
    return safe.strip("_") or "strategy"


def _metrics(bt: dict | None, period_start, period_end) -> dict[str, object]:
    result: dict[str, object] = {
        "net_profit_pct": None,
        "cagr_pct": None,
        "trade_count": None,
        "max_drawdown_pct": None,
        "sharpe_ratio": None,
        "profit_factor": None,
        "calmar_ratio": None,
    }
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
    elif net is not None and period_start and period_end:
        days = (period_end - period_start).days
        if days > 0:
            years = days / 365.25
            terminal = 1 + net / 100
            if terminal > 0:
                result["cagr_pct"] = (terminal ** (1 / years) - 1) * 100

    cagr_val = result["cagr_pct"]
    if cagr_val is not None and mdd is not None and mdd != 0:
        result["calmar_ratio"] = cagr_val / abs(mdd)

    return result


_PM_LABELS: dict[str | None, str] = {
    "signal_reversal": "Signal-Reversal",
    "entry_exit": "Entry-/Exit-Regel",
}

_EO_LABELS: dict[str | None, str] = {
    "source": "Quelle",
    "system_default": "System-Default",
    "user": "Benutzer",
}

_MTS_LABELS: dict[str | None, str] = {
    "continuous": "Kontinuierlich",
    "discrete": "Diskret",
    "unclear": "Unklar",
}

STATUS_LABELS: dict[str, str] = {
    "Entwurf": "Entwurf",
    "nicht testbar": "Nicht testbar",
    "gesperrt (unvollständig)": "Gesperrt (unvollständig)",
    "freigegeben": "Freigegeben",
    "geplant": "Geplant",
    "bestätigt": "Bestätigt",
    "in_queue": "In Queue",
    "läuft": "Läuft",
    "erfolgreich": "Erfolgreich",
    "fehlgeschlagen": "Fehlgeschlagen",
    "abgebrochen": "Abgebrochen",
}

_DETAIL_FIELDS: list[tuple[str, str]] = [
    ("Name", "name"),
    ("These", "thesis"),
    ("Kategorie", "category"),
    ("Richtung", "direction"),
    ("Entry-Regel", "entry_rule"),
    ("Exit-Regel", "exit_rule"),
    ("Warm-up", "warmup_requirement"),
    ("Simultan-Ein-/Ausstieg", "simultaneous_entry_exit_behavior"),
    ("Umkehrverhalten", "reversal_behavior"),
]


def _version_detail_table(snap: dict) -> list[str]:
    lines: list[str] = []
    lines.append("| Eigenschaft | Wert |")
    lines.append("|-------------|------|")
    for label, key in _DETAIL_FIELDS:
        val = snap.get(key)
        lines.append(f"| {label} | {_escape_md(val) or '—'} |")

    pm = snap.get("position_mode")
    pm_str = _PM_LABELS.get(pm, str(pm) if pm else _legacy_or_dash(pm, snap))
    eo = snap.get("exit_rule_origin")
    eo_str = _EO_LABELS.get(eo, str(eo) if eo else _legacy_or_dash(eo, snap))
    mts = snap.get("mts_compatibility")
    mts_str = _MTS_LABELS.get(mts, str(mts) if mts else _legacy_or_dash(mts, snap))

    lines.append(f"| Positionsmodus | {pm_str} |")
    lines.append(f"| Exit-Herkunft | {eo_str} |")
    lines.append(f"| Crypto-MTS | {mts_str} |")
    lines.append("")
    return lines


def _legacy_or_dash(val, snap: dict) -> str:
    """PROJ-10 fields that are null for legacy versions: label as unavailable."""
    has_proj10 = any(
        snap.get(k) is not None
        for k in ("position_mode", "exit_rule_origin", "mts_compatibility")
    )
    if has_proj10:
        return "—"
    return "Nicht verfügbar — Legacy-Version"


def _draft_detail_table(d: dict) -> list[str]:
    lines: list[str] = []
    lines.append("| Eigenschaft | Wert |")
    lines.append("|-------------|------|")
    for label, key in _DETAIL_FIELDS:
        val = d.get(key)
        lines.append(f"| {label} | {_escape_md(val) or '—'} |")

    pm = d.get("position_mode")
    pm_str = _PM_LABELS.get(pm, str(pm) if pm else "—")
    eo = d.get("exit_rule_origin")
    eo_str = _EO_LABELS.get(eo, str(eo) if eo else "—")
    mts = d.get("mts_compatibility")
    mts_str = _MTS_LABELS.get(mts, str(mts) if mts else "—")

    lines.append(f"| Positionsmodus | {pm_str} |")
    lines.append(f"| Exit-Herkunft | {eo_str} |")
    lines.append(f"| Crypto-MTS | {mts_str} |")
    lines.append("")
    return lines


@router.get("/drafts/{draft_id}/export.md", response_class=PlainTextResponse)
def export_markdown(draft_id: UUID) -> PlainTextResponse:
    draft = run_query_one(
        "SELECT id, family_id, name FROM strategy_drafts WHERE id = %s",
        [draft_id],
    )
    if not draft:
        raise HTTPException(404, "Entwurf nicht gefunden.")

    family_id = draft["family_id"]
    strategy_name = draft["name"] or "Unbenannte Strategie"

    versions = run_query(
        """
        SELECT sv.id, sv.version_number, sv.source_id, sv.source_hash,
               sv.extraction_model, sv.prompt_version, sv.snapshot, sv.frozen_at, sv.created_at
        FROM strategy_versions sv
        WHERE sv.family_id = %s
        ORDER BY sv.version_number
        """,
        [family_id],
    )

    drafts = run_query(
        """
        SELECT id, name, thesis, category, direction,
               entry_rule, exit_rule, warmup_requirement,
               simultaneous_entry_exit_behavior, reversal_behavior,
               status, status_reason, created_at,
               position_mode, exit_rule_origin, mts_compatibility,
               source_hash
        FROM strategy_drafts
        WHERE family_id = %s AND status != 'freigegeben'
        ORDER BY created_at
        """,
        [family_id],
    )

    lines: list[str] = []
    lines.append(f"# {_escape_md(strategy_name)}")
    lines.append("")
    lines.append(f"**Family-ID:** `{family_id}`")
    lines.append(f"**Exportierte Versionen:** {len(versions)}")
    lines.append("")

    for sv in versions:
        snap = sv["snapshot"]
        if isinstance(snap, str):
            snap = json.loads(snap)

        lines.append("---")
        lines.append("")
        frozen_str = sv["frozen_at"].isoformat() if sv.get("frozen_at") else "—"
        lines.append(f"## Version {sv['version_number']} — Freigegeben am {frozen_str}")
        lines.append("")

        lines.extend(_version_detail_table(snap))

        version_params = snap.get("parameters") or []
        if version_params:
            lines.append("### Parameter")
            lines.append("")
            lines.append("| Name | Wert | Einheit | Bereich |")
            lines.append("|------|------|---------|---------|")
            for p in version_params:
                name = _escape_md(p.get("name"))
                value = _escape_md(p.get("value"))
                unit = _escape_md(p.get("unit")) or "—"
                arange = _escape_md(p.get("allowed_range")) or "—"
                lines.append(f"| {name} | {value} | {unit} | {arange} |")
            lines.append("")

        lines.append("### Quellangaben")
        lines.append("")
        lines.append("| Feld | Wert |")
        lines.append("|------|------|")
        lines.append(f"| Quell-ID | `{sv['source_id']}` |")
        lines.append(f"| Quell-Hash | `{sv['source_hash']}` |")
        lines.append(f"| Extraktionsmodell | {_escape_md(sv['extraction_model'])} |")
        lines.append(f"| Prompt-Version | {_escape_md(sv['prompt_version'])} |")
        lines.append(f"| Eingefroren am | {frozen_str} |")
        lines.append("")

        runs_rows = run_query(
            """
            SELECT r.id, r.status, r.provider_symbol, r.direction_mode, r.run_kind,
                   r.created_at, r.started_at, r.completed_at, r.error_message,
                   b.timeframe, b.period_start, b.period_end,
                   be.backtest_result, be.report_link,
                   ra.raw_response_available
            FROM runs r
            JOIN batches b ON r.batch_id = b.id
            LEFT JOIN backtest_executions be ON r.backtest_execution_id = be.id
            LEFT JOIN run_audits ra ON ra.run_id = r.id
            WHERE r.strategy_version_id = %s
            ORDER BY r.created_at, r.id
            """,
            [sv["id"]],
        )

        lines.append("### Runs")
        lines.append("")

        if not runs_rows:
            lines.append("*Keine Runs vorhanden.*")
            lines.append("")
        else:
            lines.append(
                "| # | Instrument | Richtung | Typ | Timeframe | Zeitraum | Status | "
                "Net P&L % | CAGR % | Trades | Max DD % | Sharpe | PF | Calmar | Report |"
            )
            lines.append(
                "|---|-----------|----------|-----|-----------|----------|--------|"
                "-----------|--------|--------|----------|--------|-----|--------|--------|"
            )
            for idx, r in enumerate(runs_rows, 1):
                m = _metrics(r.get("backtest_result"), r.get("period_start"), r.get("period_end"))
                period = (
                    f"{r['period_start']} – {r['period_end']}"
                    if r.get("period_end")
                    else str(r["period_start"])
                )
                status = STATUS_LABELS.get(r["status"], r["status"])

                report_link = r.get("report_link")
                incomplete_parts: list[str] = []
                if not report_link:
                    incomplete_parts.append("unvollständig")
                elif r.get("raw_response_available") is False:
                    incomplete_parts.append("unvollständig")

                status_display = status
                if incomplete_parts:
                    status_display = f"{status} ({', '.join(incomplete_parts)})"

                report_cell = f"[Link]({report_link})" if report_link else "—"

                lines.append(
                    f"| {idx} | {r['provider_symbol']} | {r['direction_mode']} | {r['run_kind']} | "
                    f"{r['timeframe']} | {period} | {status_display} | "
                    f"{_fmt_num(m['net_profit_pct'])} | {_fmt_num(m['cagr_pct'])} | "
                    f"{_fmt_num(m['trade_count'])} | {_fmt_num(m['max_drawdown_pct'])} | "
                    f"{_fmt_num(m['sharpe_ratio'])} | {_fmt_num(m['profit_factor'])} | "
                    f"{_fmt_num(m['calmar_ratio'])} | {report_cell} |"
                )
            lines.append("")

    for d in drafts:
        lines.append("---")
        lines.append("")
        status_label = STATUS_LABELS.get(d["status"], d["status"])
        lines.append(f"## Entwurf: {_escape_md(d['name']) or 'Unbenannt'} — {status_label}")
        if d.get("status_reason"):
            lines.append(f"**Begründung:** {_escape_md(d['status_reason'])}")
        lines.append("")

        lines.extend(_draft_detail_table(d))

        draft_params = run_query(
            "SELECT name, value, unit, allowed_range FROM draft_parameters WHERE draft_id = %s",
            [d["id"]],
        )
        if draft_params:
            lines.append("### Parameter")
            lines.append("")
            lines.append("| Name | Wert | Einheit | Bereich |")
            lines.append("|------|------|---------|---------|")
            for p in draft_params:
                name = _escape_md(p.get("name"))
                value = _escape_md(p.get("value"))
                unit = _escape_md(p.get("unit")) or "—"
                arange = _escape_md(p.get("allowed_range")) or "—"
                lines.append(f"| {name} | {value} | {unit} | {arange} |")
            lines.append("")

        lines.append("### Quellangaben")
        lines.append("")
        lines.append("| Feld | Wert |")
        lines.append("|------|------|")
        lines.append(f"| Quell-Hash | `{d.get('source_hash', '—')}` |")
        lines.append(f"| Erstellt am | {d['created_at'].isoformat()} |")
        lines.append("")

        lines.append("*Noch nicht eingefroren — keine Runs verfügbar.*")
        lines.append("")

    content = "\n".join(lines) + "\n"
    filename = f"{_safe_filename(strategy_name)}_{family_id}.md"
    return PlainTextResponse(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
