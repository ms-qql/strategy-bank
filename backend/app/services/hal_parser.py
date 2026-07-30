"""Deterministischer Parser für Hal-Backtest-Markdown-Dateien.

Unterstützt das ausführliche Tabellenformat (trade-backtest-tradedev)
und das kompakte KPI-Format. Keine KI — regelbasiert, reproduzierbar.

Minimalvertrag (muss-Angaben):
  Strategiename, Asset (Provider-Symbol), Timeframe, Beginn, Ende,
  Net Return, Max Drawdown, Trade-Anzahl.

Optionale Angaben:
  Sortino Ratio, Report-Link, Parameter, Long/Short-Breakdown,
  Pine-Code, Richtung, Vergleichsprofil (Gebühren, Slippage, Sizing).
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class ParsedResult:
    strategy_name: str
    asset: str
    timeframe: str
    period_start: date
    period_end: date | None
    net_return_pct: float
    max_drawdown_pct: float
    trade_count: int

    sortino_ratio: float | None = None
    profit_factor: float | None = None
    sharpe_ratio: float | None = None
    win_rate_pct: float | None = None
    cagr_pct: float | None = None
    report_link: str | None = None
    parameters: list[dict] = field(default_factory=list)
    long_short_breakdown: dict | None = None
    pine_code: str | None = None
    direction: str | None = None
    fee_pct: float | None = None
    slippage_ticks: float | None = None
    sizing_model: str | None = None
    source_link: str | None = None
    strategy_version_id: str | None = None

    error: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.error is None


_KPI_LABELS: dict[str, str] = {
    "Net Return": "net_return_pct",
    "Profit Factor": "profit_factor",
    "Win Rate": "win_rate_pct",
    "Sharpe Ratio": "sharpe_ratio",
    "Sortino Ratio": "sortino_ratio",
    "Max Drawdown": "max_drawdown_pct",
    "Total Trades": "trade_count",
}

_DIRECTION_PATTERN = re.compile(r"\*\*Richtung:\*\*\s*(kombiniert|long.only|short.only)", re.IGNORECASE)
_HEADING_PATTERN = re.compile(r"^#\s+(?:Backtest:\s*)?(.+)$", re.MULTILINE)
_SOURCE_PATTERN = re.compile(r"\*\*Quelle:\*\*\s*\[.+\]\((.+)\)")
_STRATEGY_VERSION_PATTERN = re.compile(
    r"\*\*(?:Strategieversion|Strategy[- ]Version)(?:-ID| ID)?:\*\*\s*"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})",
    re.IGNORECASE,
)
_COMMISSION_PATTERN = re.compile(
    r"(?:Commission|Kommission)(?:\s+auf)?\s+([0-9]+(?:[.,][0-9]+)?)\s*%",
    re.IGNORECASE,
)
_SLIPPAGE_PATTERN = re.compile(
    r"Slippage(?:\s*[:=]|\s+auf)?\s*([0-9]+(?:[.,][0-9]+)?)",
    re.IGNORECASE,
)
_SIZING_PATTERN = re.compile(
    r"Sizing(?:\s+auf)?\s+([^,\n—]+)",
    re.IGNORECASE,
)

_TABLE_ROW_PATTERN = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")


def _parse_percentage(raw: str) -> float | None:
    """Liest Dezimalzahlen mit deutschem oder englischem Dezimaltrenner."""
    match = re.search(r"[-+]?\d[\d.,]*", raw.strip().replace("−", "-"))
    if not match:
        return None
    raw = match.group(0)
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def _parse_int(raw: str) -> int | None:
    raw = raw.strip().replace(",", "").replace(".0", "").replace("*", "")
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _read_table_section(text: str, section_heading: str) -> list[dict[str, str]]:
    """Findet eine Markdown-Überschrift und liest die folgende Tabelle."""
    pattern = re.compile(rf"^##\s+{re.escape(section_heading)}\s*$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return []
    pos = m.end()
    lines = text[pos:].split("\n")
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    in_table = False
    for line in lines:
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line[1:-1].split("|")]
            if not in_table:
                if all(c and c.strip(":- ") for c in cells):
                    headers = cells
                    in_table = True
                continue
            if cells == headers:
                continue
            if len(cells) == len(headers):
                rows.append(dict(zip(headers, cells)))
        elif in_table and not line.startswith("|"):
            break
    return rows


def _read_table_by_key(text: str, section_heading: str) -> dict[str, str]:
    """Liest Key-Value-Tabelle unter einer Überschrift."""
    rows = _read_table_section(text, section_heading)
    result: dict[str, str] = {}
    for row in rows:
        val = list(row.values())
        if len(val) >= 2:
            key = val[0].strip().replace("*", "").strip()
            result[key] = val[1].strip()
    return result


def _read_subsection_table(text: str, section_heading: str, subsection_heading: str) -> list[dict[str, str]]:
    """Findet eine Sub-Überschrift innerhalb einer Section und liest deren Tabelle."""
    pattern = re.compile(rf"^##\s+{re.escape(section_heading)}\s*$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return []
    section_start = m.end()
    sub_pattern = re.compile(rf"^###\s+{re.escape(subsection_heading)}\s*$", re.MULTILINE)
    sm = sub_pattern.search(text, pos=section_start)
    if not sm:
        return []
    pos = sm.end()
    lines = text[pos:].split("\n")
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    in_table = False
    for line in lines:
        line = line.strip()
        if line.startswith("#"):
            break
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line[1:-1].split("|")]
            if not in_table:
                if all(c and c.strip(":- ") for c in cells):
                    headers = cells
                    in_table = True
                continue
            if cells == headers:
                continue
            if len(cells) == len(headers):
                rows.append(dict(zip(headers, cells)))
        elif in_table and not line.startswith("|"):
            break
    return rows


def _extract_pine_code(text: str) -> str | None:
    m = re.search(r"```pinescript\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return None


def _extract_report_link(text: str) -> str | None:
    m = re.search(r"^##\s+Report\s*$\n+(https?://\S+)", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def _parse_direction(text: str) -> str | None:
    m = _DIRECTION_PATTERN.search(text)
    if m:
        d = m.group(1).lower()
        if "kombiniert" in d:
            return "kombiniert"
        if "long" in d and "short" in d:
            return "kombiniert"
        if "long" in d:
            return "long-only"
        if "short" in d:
            return "short-only"
    return None


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace("  ", " ")


def _parse_bool_like(raw: str) -> bool | None:
    v = raw.strip().lower()
    if v in ("true", "ja", "yes"):
        return True
    if v in ("false", "nein", "no"):
        return False
    return None


def parse_hal_backtest(markdown: str) -> ParsedResult:
    """Parst eine Hal-Backtest-Markdown-Datei.

    Extrahiert den Minimalvertrag (Pflichtangaben) und alle optionalen Felder.
    Bei fehlenden Pflichtangaben wird result.error gesetzt.
    """
    errors: list[str] = []

    name_match = _HEADING_PATTERN.search(markdown)
    strategy_name = name_match.group(1).strip() if name_match else None
    if not strategy_name:
        errors.append("Strategiename fehlt.")
        strategy_name = ""

    source_match = _SOURCE_PATTERN.search(markdown)
    source_link = source_match.group(1).strip() if source_match else None
    version_match = _STRATEGY_VERSION_PATTERN.search(markdown)
    strategy_version_id = version_match.group(1) if version_match else None

    # Faktoren-Tabelle (Asset, Timeframe, Periode, Bars)
    faktoren = _read_table_by_key(markdown, "Faktoren")
    asset_raw = faktoren.get("Asset", "")
    asset_parts = [part.strip() for part in re.split(r"[()]", asset_raw) if part.strip()]
    asset = next((part for part in asset_parts if ":" in part), asset_parts[0] if asset_parts else "")
    if not asset:
        errors.append("Asset fehlt.")

    timeframe_raw = faktoren.get("Timeframe", "")
    timeframe = timeframe_raw.strip()
    if not timeframe:
        errors.append("Timeframe fehlt.")

    period_str = faktoren.get("Periode", "")
    period_start: date | None = None
    period_end: date | None = None
    period_parts = re.split(r"\s+[–—]\s+", period_str)
    if len(period_parts) >= 2:
        period_start = _parse_date(period_parts[0].strip())
        period_end = _parse_date(period_parts[1].strip())
    if period_start is None:
        period_start = _parse_date(period_str)
    if not period_start:
        errors.append("Beginn des Testzeitraums fehlt.")
    if not period_end:
        errors.append("Ende des Testzeitraums fehlt.")

    # Input-Parameter (optional)
    params_table = _read_table_section(markdown, "Input-Parameter")

    # KPIs
    kpis = _read_table_by_key(markdown, "Ergebnis KPIs")
    net_return = _parse_percentage(kpis.get("Net Return", ""))
    mdd = _parse_percentage(kpis.get("Max Drawdown", ""))
    trade_count = _parse_int(kpis.get("Total Trades", ""))

    if net_return is None:
        errors.append("Net Return fehlt.")
    if mdd is None:
        errors.append("Max Drawdown fehlt.")
    if trade_count is None:
        errors.append("Trade-Anzahl fehlt.")

    # Versuche kompakte Alternative (eine Zeile mit mehreren KPIs)
    if net_return is None or mdd is None or trade_count is None:
        alt = _read_table_section(markdown, "Ergebnis KPIs")
        for row in alt:
            vals = list(row.values())
            for k in vals:
                kpct = _parse_percentage(k)
                kint = _parse_int(k)
                if kpct is not None and net_return is None:
                    net_return = kpct
                elif kpct is not None and mdd is None:
                    mdd = kpct
                if kint is not None and trade_count is None:
                    trade_count = kint

    if errors:
        return ParsedResult(
            strategy_name=strategy_name or "",
            asset=asset,
            timeframe=timeframe,
            period_start=period_start or date.today(),
            period_end=period_end,
            net_return_pct=net_return or 0,
            max_drawdown_pct=mdd or 0,
            trade_count=trade_count or 0,
            error="; ".join(errors),
        )

    sortino = _parse_percentage(kpis.get("Sortino Ratio", ""))
    profit_factor = _parse_percentage(kpis.get("Profit Factor", "")) or None
    sharpe = _parse_percentage(kpis.get("Sharpe Ratio", ""))
    win_rate = _parse_percentage(kpis.get("Win Rate", ""))

    report_link = _extract_report_link(markdown)

    # Long/Short-Breakdown
    breakdown_rows = _read_subsection_table(markdown, "Ergebnis KPIs", "Long/Short-Breakdown")
    long_short: dict | None = None
    if breakdown_rows:
        long_short = {_normalize_key(list(r.keys())[0]): r for r in breakdown_rows}

    pine_code = _extract_pine_code(markdown)
    direction = _parse_direction(markdown)

    normalized_factors = {_normalize_key(k): v.strip() for k, v in faktoren.items()}
    fee_raw = normalized_factors.get("gebühren") or normalized_factors.get("gebühr") or normalized_factors.get("fee")
    slippage_raw = normalized_factors.get("slippage") or normalized_factors.get("slippage ticks")
    sizing_model = (
        normalized_factors.get("sizing-modell")
        or normalized_factors.get("sizing modell")
        or normalized_factors.get("sizing model")
        or normalized_factors.get("position sizing")
    )
    fee_pct = _parse_percentage(fee_raw) if fee_raw else None
    slippage_ticks = _parse_percentage(slippage_raw) if slippage_raw else None
    if fee_pct is None:
        match = _COMMISSION_PATTERN.search(markdown)
        fee_pct = _parse_percentage(match.group(1)) if match else None
    if slippage_ticks is None:
        match = _SLIPPAGE_PATTERN.search(markdown)
        slippage_ticks = _parse_percentage(match.group(1)) if match else None
    if sizing_model is None:
        match = _SIZING_PATTERN.search(markdown)
        sizing_model = match.group(1).strip() if match else None

    return ParsedResult(
        strategy_name=strategy_name,
        asset=asset,
        timeframe=timeframe,
        period_start=period_start or date.today(),
        period_end=period_end,
        net_return_pct=net_return,
        max_drawdown_pct=mdd,
        trade_count=trade_count,
        sortino_ratio=sortino,
        profit_factor=profit_factor,
        sharpe_ratio=sharpe,
        win_rate_pct=win_rate,
        report_link=report_link,
        parameters=params_table,
        long_short_breakdown=long_short,
        pine_code=pine_code,
        direction=direction,
        fee_pct=fee_pct,
        slippage_ticks=slippage_ticks,
        sizing_model=sizing_model,
        source_link=source_link,
        strategy_version_id=strategy_version_id,
    )
