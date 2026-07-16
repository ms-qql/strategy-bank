"""PROJ-6 Pine-v5-Generator — übersetzt Strategie-JSONB-Snapshot in validen
Pine-Script-v5-Quellcode.

Architektur:
  - `generate(snapshot, parameters, config)` → vollständiger Pine-v5-Quelltext
  - Rule-Parser tokenisiert natürlichesprachige Entry-/Exit-Regeln
  - Pattern-Matcher erkennt Indikator-Terme (RSI, SMA, EMA, MACD, etc.)
  - Parameter-Substitution ersetzt parametrisierte Werte
  - Direction-Filter (long-only, short-only, kombiniert)

Nicht abgedeckte Regeln führen zu einem `PineGenerationError` — der Worker
markiert solche Runs als fehlgeschlagen mit verständlichem Fehlergrund.
"""

from __future__ import annotations

import re
from typing import Any

from ..constants import CATEGORIES, DIRECTIONS, SYSTEM_DEFAULT_EXIT_BARS, SYSTEM_DEFAULT_EXIT_RULE


class PineGenerationError(Exception):
    pass


PINEPARAM = str


def _p(name: str) -> PINEPARAM:
    """Erzeugt einen eindeutigen input()-Parameternamen."""
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_").lower()
    if safe and safe[0].isdigit():
        safe = "_" + safe
    return safe or "_unknown"


def generate(
    snapshot: dict[str, Any],
    params: list[dict[str, Any]] | None = None,
    *,
    timeframe: str = "1h",
    direction: str | None = None,
    initial_capital: float = 10_000,
    commission_pct: float = 0.06,
    slippage_ticks: int = 2,
    pyramiding: int = 0,
) -> str:
    """Haupteinstieg: erzeugt vollständigen Pine-v5-Quelltext."""
    direction = direction or snapshot.get("direction", "kombiniert")
    if direction not in DIRECTIONS:
        direction = "kombiniert"

    entry_rule = (snapshot.get("entry_rule") or "").strip()
    exit_rule = (snapshot.get("exit_rule") or "").strip()
    position_mode = snapshot.get("position_mode", "entry_exit") or "entry_exit"
    params = params or snapshot.get("parameters") or []

    if not entry_rule:
        raise PineGenerationError("Entry-Regel fehlt — Pine-Script kann nicht generiert werden.")

    context = _build_context(params)

    entry_expr = _translate_rule(entry_rule, context)
    exit_expr = _translate_exit_rule(exit_rule, position_mode, entry_rule, context)

    lines: list[str] = [
        "// strategy-bank — generated Pine Script v5",
        f"// @version=5",
        f"// entry: {entry_rule}",
    ]
    if exit_rule:
        lines.append(f"// exit: {exit_rule}")
    lines.append("")
    lines.append(
        f"strategy(\"Strategy Bank\", overlay=true, initial_capital={initial_capital}, "
        f"commission_type=strategy.commission.percent, commission_value={commission_pct}, "
        f"slippage={slippage_ticks}, pyramiding={pyramiding})"
    )
    lines.append("")

    param_lines = _build_param_declarations(context)
    if param_lines:
        lines.extend(param_lines)
        lines.append("")

    lines.append("var int _barSinceEntry = 0")

    if direction != "kombiniert":
        lines.append("var bool _hasActivePosition = false")
        lines.append("")

    width = 80
    lines.append("// ── entry / exit ──")
    lines.append(f"bool _entry = {entry_expr}")
    lines.append(f"bool _exit = {exit_expr}")

    if direction != "kombiniert":
        dir_filter = "true"
        if direction == "long-only":
            dir_filter = "not _hasActivePosition"
        elif direction == "short-only":
            dir_filter = "not _hasActivePosition"
        lines.append(f"bool _dirOk = {dir_filter}")

    lines.append("")
    lines.append("// ── bar tracking ──")
    lines.append("if strategy.position_size == 0")
    lines.append("    _barSinceEntry := 0")
    lines.append("else")
    lines.append("    _barSinceEntry += 1")
    lines.append("")

    lines.append("// ── position ──")
    entry_cond = "_entry"
    exit_cond = "_exit"
    if direction != "kombiniert":
        entry_cond = f"_entry and _dirOk"

    lines.append(f"if {entry_cond}")
    lines.append("    strategy.entry(\"E\", strategy.long)")

    if direction == "short-only":
        lines[-1] = f"if {entry_cond}"
        lines.append("    strategy.entry(\"E\", strategy.short)")

    if direction == "kombiniert":
        lines.append("")
        lines.append(f"if _entry and strategy.position_size > 0")
        lines.append("    strategy.entry(\"E_S\", strategy.short)")
        lines.append(f"if {exit_cond}")
        lines.append("    strategy.close_all()")
    else:
        lines.append(f"if {exit_cond}")
        lines.append("    strategy.close(\"E\")")

    if position_mode == "signal_reversal":
        lines.append("")
        lines.append("// ── signal reversal ──")
        lines.append(f"if {entry_cond} and strategy.position_size < 0")
        lines.append("    strategy.close(\"E_S\")")
        lines.append(f"if {entry_cond} and strategy.position_size < 0")
        lines.append("    strategy.entry(\"E\", strategy.long)")

    if direction == "long-only":
        lines.append("")
        lines.append("if _entry")
        lines.append("    _hasActivePosition := true")

    lines.append("")
    lines.append("// ── bar-count fail-safe ──")
    lines.append(f"if _barSinceEntry > {max(SYSTEM_DEFAULT_EXIT_BARS * 2, 50)}")
    lines.append("    strategy.close_all()")

    lines.append("")
    lines.append("// ── indicator plot (debug) ──")
    for name, cinfo in sorted(context.items()):
        pn = cinfo.get("_pine_var")
        if pn:
            lines.append(f"plot({pn}, title=\"{cinfo['label']}\", display=display.none)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Parameter Extraction
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, str, str]] = [
    ("rsi", r"rsi(?:\s*(?:periode|period|length))?\s*(?:<|>|<=|>=|cross(?:es)?\s*(?:above|below))\s*(\d+)", "ta.rsi"),
    ("rsi_param", r"(?:rsi.*?)(?:periode|period|length)?\s*=\s*(\d+)", "ta.rsi"),

    ("sma", r"sma(?:\s*\(?\s*(\d+)\s*\)?)?|simple moving average\s*(?:of\s*)?\s*(\d+)", "ta.sma"),
    ("ema", r"ema(?:\s*\(?\s*(\d+)\s*\)?)?|exponential moving average\s*(?:of\s*)?\s*(\d+)", "ta.ema"),
    ("macd", r"macd", "ta.macd"),

    ("bb", r"bollinger\s*(?:bands?)?|bollinger|bb", "ta.bb"),

    ("volume", r"volume\s*(?:cross(?:es)?\s*(?:above|below)\s*(?:its\s*)?)?(?:\d+-?(?:bar|periode|period))?", "ta.sma"),
    ("volume_ma", r"volume.*?(?:sma|ema|ma|average|mittel)\s*(?:\(?\s*(\d+)\s*\)?)?", "ta.sma"),

    ("atr", r"atr(?:\s*\(?\s*(\d+)\s*\)?)?", "ta.atr"),

    ("stochastic", r"stochastic|stoch", "ta.stoch"),

    ("supertrend", r"supertrend", "ta.supertrend"),

    ("vwap", r"vwap", "ta.vwap"),

    ("mfi", r"mfi|money\s*flow\s*index", "ta.mfi"),

    ("crossover", r"(cross(?:es)?\s*(?:above|below))", "ta.crossover"),
]


def _build_context(params: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    ctx: dict[str, dict[str, Any]] = {}
    for p in params:
        name = p.get("name", "")
        ctx[_p(name)] = {
            "label": name,
            "value": p.get("value", ""),
            "unit": p.get("unit"),
            "_pine_var": None,
        }
    return ctx


def _build_param_declarations(ctx: dict[str, dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for name, cinfo in ctx.items():
        label = cinfo["label"]
        if name in seen:
            continue
        seen.add(name)
        raw = str(cinfo.get("value", "1"))
        try:
            default: float | str = float(raw) if raw.replace(".", "", 1).isdigit() else raw
        except ValueError:
            default = raw
        ptype = "float" if isinstance(default, (int, float)) else "string"
        if ptype == "float":
            lines.append(f"{name} = input.float({default}, title=\"{label}\", minval=0)")
        else:
            lines.append(f"{name} = input.string(\"{default}\", title=\"{label}\")")
    return lines


# ---------------------------------------------------------------------------
# Rule Translation
# ---------------------------------------------------------------------------

_RELATION_MAP: dict[str, str] = {"<": "<", ">": ">", "<=": "<=", ">=": ">=", "=": "==", "==": "=="}
_CROSS_MAP: dict[str, str] = {"crosses above": "ta.crossover", "crosses below": "ta.crossunder",
                                "cross above": "ta.crossover", "cross below": "ta.crossunder"}

_RSI_CROSS_RE = re.compile(
    r"rsi\s*(?:\(?\s*(?P<period>\d+)\s*\)?)?\s*cross(?:es)?\s*(?P<dir>above|below)\s*(?P<threshold>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_RSI_RE = re.compile(
    r"rsi\s*(?:\(?\s*(?P<period>\d+)\s*\)?)?\s*(?P<op>[<>]=?|==|=)\s*(?P<threshold>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SMA_RE = re.compile(
    r"(?:sma|simple moving average)\s*(?:\(?\s*(?P<period>\d+)\s*\)?)?\s*(?:close|price)?\s*(?P<op>[<>]=?|==|=)\s*(?P<series>close|high|low|open|hl2|hlc3|ohlc4|sma\s*\(?\s*\d+\s*\)?)",
    re.IGNORECASE,
)
_CLOSE_GT_SMA_RE = re.compile(
    r"(?:close|price)\s*>\s*sma\s*\(?\s*(?P<period>\d+)\s*\)?",
    re.IGNORECASE,
)
_CLOSE_REL_SMA_RE = re.compile(
    r"(?:close|price)\s*(?P<op>[<>]=?|==|=)\s*sma\s*\(?\s*(?P<period>\d+)\s*\)?",
    re.IGNORECASE,
)
_VOL_MA_RE = re.compile(
    r"volume\s*(?:cross(?:es)?\s*(?:above|below)\s*(?:its\s*)?)?(?P<period>\d+)(?:-?(?:bar|periode|period))?\s*(?:sma|ma|average|mittel)",
    re.IGNORECASE,
)
_VOL_SMA_RE = re.compile(
    r"volume\s*>\s*(?:(?:its\s*)?(?P<period>\d+)(?:-?(?:bar|periode|period))?\s*(?:sma|ma|average|mittel))",
    re.IGNORECASE,
)
_VOL_REL_SMA_RE = re.compile(
    r"volume\s*(?P<op>[<>]=?|==|=)\s*sma\s*\(?\s*(?P<period>\d+)\s*\)?",
    re.IGNORECASE,
)
_CLOSE_CROSS_SMA_RE = re.compile(
    r"(?:close|price)\s*cross(?:es)?\s*(?P<dir>above|below)\s*sma\s*\(?\s*(?P<period>\d+)\s*\)?",
    re.IGNORECASE,
)
_MACD_CROSS = re.compile(r"macd\s*(?:line\s*)?cross(?:es)?\s*(?P<dir>above|below)\s*(?:signal|zero)", re.IGNORECASE)
_MACD_HIST = re.compile(r"macd\s*histogram\s*(?P<op>[<>])\s*0", re.IGNORECASE)
_ATR_MULT = re.compile(
    r"atr\s*(?:\(?\s*(?P<period>\d+)\s*\)?)?\s*\*\s*(?P<mult>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_BREAKOUT = re.compile(
    r"(?:breakout|break\s*out)\s*(?:above|über)?\s*(?P<days>\d+)\s*-?\s*(?:day|tages?|periode|period).*?high",
    re.IGNORECASE,
)
_VOL_CROSS = re.compile(
    r"volume\s*cross(?:es)?\s*(?P<dir>above|below)",
    re.IGNORECASE,
)
_CLOSE_GT = re.compile(r"(?:close|price)\s*>\s*(?P<value>\d+(?:\.\d+)?)", re.IGNORECASE)
_CLOSE_LT = re.compile(r"(?:close|price)\s*<\s*(?P<value>\d+(?:\.\d+)?)", re.IGNORECASE)

PRICE_SOURCE = "close"


def _translate_rule(rule: str, ctx: dict[str, dict[str, Any]]) -> str:
    """Parsed die natürlichesprachige Regel und gibt einen Pine-Boolean-Ausdruck zurück."""
    rule = rule.strip()
    if not rule:
        raise PineGenerationError("Leere Regel — kann nicht übersetzt werden.")

    if _is_bar_count_exit(rule):
        return "true"

    parts = _split_and_or(rule)
    if len(parts) > 1:
        expr_parts: list[str] = []
        for p_part in parts:
            p_part = p_part.strip()
            if p_part.upper() == "AND":
                continue
            if p_part.upper() == "OR":
                continue
            expr_parts.append(_translate_simple(p_part.strip(), ctx))
        joiner = " and " if " AND " in rule.upper() or " UND " in rule.upper() else " or "
        joined = f" {joiner} ".join(expr_parts)
        return f"({joined})"
    else:
        return _translate_simple(rule, ctx)


def _translate_simple(rule: str, ctx: dict[str, dict[str, Any]]) -> str:
    rule = rule.strip()

    m = _RSI_CROSS_RE.match(rule)
    if m:
        return _build_rsi_cross(m, ctx)

    m = _RSI_RE.match(rule)
    if m:
        return _build_rsi(m, ctx)

    m = _CLOSE_CROSS_SMA_RE.match(rule)
    if m:
        return _build_close_cross_sma(m, ctx)

    m = _CLOSE_REL_SMA_RE.match(rule)
    if m:
        return _build_close_rel_sma(m, ctx)

    m = _CLOSE_GT_SMA_RE.match(rule)
    if m:
        return _build_close_rel_sma(m, ctx)

    m = _VOL_SMA_RE.match(rule)
    if m:
        return _build_vol_gt_sma(m)

    m = _VOL_REL_SMA_RE.match(rule)
    if m:
        return _build_vol_rel_sma(m)

    m = _VOL_CROSS.match(rule)
    if m:
        return _build_vol_cross(m)

    m = _MACD_CROSS.match(rule)
    if m:
        return _build_macd_cross(m)

    m = _MACD_HIST.match(rule)
    if m:
        return _build_macd_hist(m)

    m = _CLOSE_GT.match(rule)
    if m:
        return f"close > {m.group('value')}"

    m = _CLOSE_LT.match(rule)
    if m:
        return f"close < {m.group('value')}"

    norm = _normalize(rule)

    for name, cinfo in ctx.items():
        val = str(cinfo.get("value", ""))
        label_lower = cinfo["label"].lower().strip()
        norm_lower = norm.lower()
        if (
            name in norm_lower
            or label_lower in norm_lower
            or (val and val in norm_lower and label_lower in norm_lower)
        ):
            cinfo["_pine_var"] = name

    for name, cinfo in ctx.items():
        label = cinfo["label"].lower()
        if "rsi" in label and "rsi" in norm.lower():
            period = cinfo.get("value", "14")
            try:
                float(period)
            except ValueError:
                period = "14"
            cinfo["_pine_var"] = name
            rsi_var = f"ta.rsi(close, int({name}))" if name in norm else f"ta.rsi(close, {period})"
            # generischer RSI-Threshold-Match
            op_match = re.search(r"rsi\s*(?P<op>[<>]=?|==|=)\s*(?P<threshold>\d+(?:\.\d+)?)", norm, re.IGNORECASE)
            if op_match:
                op = op_match.group("op")
                thresh = op_match.group("threshold")
                return f"{rsi_var} {_RELATION_MAP.get(op, op)} {thresh}"
            return f"ta.crossover({rsi_var}, {period})"

    if "sma" in norm.lower() or "moving average" in norm.lower():
        if "volume" in norm.lower():
            raise PineGenerationError(
                f"Regel nicht automatisch zuverlässig in Pine übersetzbar: {rule} "
                f"(Volume-Regel nicht erkannt)"
            )
        period = "20"
        for name, cinfo in ctx.items():
            if "sma" in cinfo["label"].lower() or "moving" in cinfo["label"].lower():
                period = cinfo.get("value", "20")
                cinfo["_pine_var"] = name
                break
        sma_var = f"ta.sma(close, {period})"
        op_match = re.search(r"close\s*(?P<op>[<>]=?|==|=)\s*", norm, re.IGNORECASE)
        if op_match:
            return f"close {op_match.group('op')} {sma_var}"
        return f"close > {sma_var}"

    if "macd" in norm.lower():
        macd_line = "ta.macd(close, 12, 26, 9)"
        signal_line = "ta.macd(close, 12, 26, 9)[1]"
        return f"ta.crossover({macd_line}, {signal_line})"

    raise PineGenerationError(
        f"Regel nicht automatisch zuverlässig in Pine übersetzbar: {rule} "
        f"(Erkannte Parameter: {list(ctx.keys())})"
    )


def _translate_exit_rule(
    exit_rule: str,
    position_mode: str,
    entry_rule: str,
    ctx: dict[str, dict[str, Any]],
) -> str:
    e = (exit_rule or "").strip()

    if _is_bar_count_exit(e):
        return f"_barSinceEntry >= {SYSTEM_DEFAULT_EXIT_BARS}"

    if position_mode == "signal_reversal":
        try:
            entry_expr = _translate_rule(entry_rule, ctx)
            return f"not ({entry_expr})"
        except PineGenerationError:
            raise

    if e:
        try:
            return _translate_rule(e, ctx)
        except PineGenerationError:
            pass

    return f"_barSinceEntry >= {SYSTEM_DEFAULT_EXIT_BARS * 2}"


def _is_bar_count_exit(rule: str) -> bool:
    return bool(re.search(
        r"(?:\d+|zehn|zwanzig|fünfzig)\s*(?:vollständig\s*)?(?:vergangen\w*|abgelaufen\w*|completed|elapsed)\s*bar",
        rule, re.IGNORECASE,
    ))


def _build_rsi(m: re.Match, ctx: dict[str, dict[str, Any]]) -> str:
    period = m.group("period") or "14"
    op = m.group("op")
    threshold = m.group("threshold")
    for name, cinfo in ctx.items():
        if "rsi" in cinfo["label"].lower():
            period = name
            cinfo["_pine_var"] = name
            break
    else:
        try:
            period_int = int(period)
            period = str(period_int)
        except ValueError:
            period = "14"
    return f"ta.rsi(close, {period}) {_RELATION_MAP.get(op, op)} {threshold}"


def _build_rsi_cross(m: re.Match, ctx: dict[str, dict[str, Any]]) -> str:
    period = m.group("period") or "14"
    direction = m.group("dir")
    threshold = m.group("threshold")
    for name, cinfo in ctx.items():
        if "rsi" in cinfo["label"].lower():
            period = name
            cinfo["_pine_var"] = name
            break
    fn = "ta.crossover" if direction == "above" else "ta.crossunder"
    return f"{fn}(ta.rsi(close, {period}), {threshold})"


def _build_vol_rel_sma(m: re.Match) -> str:
    period = m.group("period")
    op = m.group("op")
    return f"volume {_RELATION_MAP.get(op, op)} ta.sma(volume, {period})"


def _build_close_cross_sma(m: re.Match, ctx: dict[str, dict[str, Any]]) -> str:
    period = m.group("period")
    direction = m.group("dir")
    fn = "ta.crossover" if direction == "above" else "ta.crossunder"
    return f"{fn}(close, ta.sma(close, {period}))"


def _build_close_rel_sma(m: re.Match, ctx: dict[str, dict[str, Any]]) -> str:
    period = m.group("period")
    op = m.groupdict().get("op", ">")
    return f"close {_RELATION_MAP.get(op, op)} ta.sma(close, {period})"


def _build_vol_gt_sma(m: re.Match) -> str:
    period = m.group("period")
    return f"volume > ta.sma(volume, {period})"


def _build_vol_cross(m: re.Match) -> str:
    direction = m.group("dir")
    fn = "ta.crossover" if direction == "above" else "ta.crossunder"
    return f"{fn}(volume, ta.sma(volume, 20))"


def _build_macd_cross(m: re.Match) -> str:
    direction = m.group("dir")
    fn = "ta.crossover" if direction == "above" else "ta.crossunder"
    return f"{fn}(ta.macd(close, 12, 26, 9), 0)"


def _build_macd_hist(m: re.Match) -> str:
    op = m.group("op")
    return f"ta.macd(close, 12, 26, 9) - ta.macd(close, 12, 26, 9)[1] {op} 0"


def _split_and_or(rule: str) -> list[str]:
    parts = re.split(r"\s+(?:AND|UND|and|und|&&)\s+", rule)
    if len(parts) > 1:
        result: list[str] = []
        for i, p in enumerate(parts):
            result.append(p)
            if i < len(parts) - 1:
                result.append("AND")
        return result
    parts = re.split(r"\s+(?:OR|ODER|or|oder|\|\|)\s+", rule)
    if len(parts) > 1:
        result = []
        for i, p in enumerate(parts):
            result.append(p)
            if i < len(parts) - 1:
                result.append("OR")
        return result
    return [rule]


def _normalize(rule: str) -> str:
    r = rule.lower()
    r = re.sub(r"\s+", " ", r)
    r = r.replace("(", "").replace(")", "")
    return r.strip()
