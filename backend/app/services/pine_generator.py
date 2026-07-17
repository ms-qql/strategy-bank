"""PROJ-6 Pine-v5-Generator — übersetzt Strategie-JSONB-Snapshot in validen
Pine-Script-v5-Quellcode.

Ursprünglich ein selbstgebauter Regex-Übersetzer (~20 Patterns) für die
natürlichsprachigen Entry-/Exit-Regeln. Der Regex-Ansatz scheiterte an jeder
nicht vorgesehenen Formulierung (`PineGenerationError`), der Worker markierte
den Run als fehlgeschlagen — das führte zu den vielen erfolglosen Versuchen,
die ein einfacher Terminal-Test (Claude schreibt das Pine-Script selbst in
einem LLM-Schritt und übergibt es an trader.dev) in Sekunden löst.

Dieses Modul ersetzt den Regex-Übersetzer durch genau diesen LLM-Schritt:
`generate()` baut aus dem Snapshot (These, Entry-/Exit-Regel, Parameter,
Richtung, Positions-Modus) einen Prompt und lässt die bereits konfigurierte
OpenCode-Runtime (siehe `opencode_extraction.py`) das vollständige Pine-v5-
Script schreiben. Öffentliches API (`generate`, `PineGenerationError`)
bleibt unverändert — `worker.py` braucht keine Anpassung.
"""

from __future__ import annotations

import re
from typing import Any

from .opencode_extraction import run_opencode

_PINE_FENCE_RE = re.compile(r"```(?:pine|pinescript)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_VERSION_TAG_RE = re.compile(r"^//\s*@version\s*=\s*5")
_INVALID_STRATEGY_MEMBER_RE = re.compile(r"\bstrategy\s*\.\s*(?:signal_reversal|entry_exit)\b")
_INVALID_TA_BUILTIN_RE = re.compile(r"\bta\s*\.\s*(?:adx|kama)\s*\(")


class PineGenerationError(Exception):
    pass


def build_prompt(
    snapshot: dict[str, Any],
    *,
    params: list[dict[str, Any]],
    timeframe: str,
    direction: str,
    initial_capital: float,
    commission_pct: float,
    slippage_ticks: int,
    pyramiding: int,
    previous_error: str | None = None,
) -> str:
    entry_rule = (snapshot.get("entry_rule") or "").strip()
    exit_rule = (snapshot.get("exit_rule") or "").strip()
    position_mode = snapshot.get("position_mode") or "entry_exit"
    position_mode_description = (
        "Gegensignal schließt die bestehende Position und eröffnet sofort die Gegenposition"
        if position_mode == "signal_reversal"
        else "Entry und Exit werden durch getrennte Regeln gesteuert"
    )
    thesis = (snapshot.get("thesis") or "").strip()
    category = snapshot.get("category") or "Sonstige"
    warmup = (snapshot.get("warmup_requirement") or "").strip()

    param_lines = "\n".join(
        f"  - {p.get('name')}: default={p.get('value')} ({p.get('unit') or 'ohne Einheit'})"
        for p in params
    ) or "  (keine — sinnvolle Standardwerte selbst wählen und als input.* deklarieren)"

    previous_error_block = (
        f"""
WICHTIG: Der vorherige Generierungsversuch wurde vom Pine-Compiler/Provider mit
folgendem Fehler abgelehnt:
  {previous_error}
Vermeide genau dieses Problem — nutze KEIN Built-in, das in diesem Fehler als
ungültig/nicht existent genannt wird, und wähle eine valide Pine-v5-Alternative.
"""
        if previous_error
        else ""
    )

    return f"""Schreib ein vollständiges, lauffähiges Pine Script v5 für folgende Trading-Strategie.

These: {thesis or "(nicht angegeben)"}
Kategorie: {category}
Richtung: {direction}
Positionsverwaltung: {position_mode_description}
Entry-Regel: {entry_rule}
Exit-Regel: {exit_rule or "(keine explizite Regel — sinnvollen Systemdefault wählen, z.B. Exit nach 10 vollständig vergangenen Bars)"}
Warmup-Anforderung: {warmup or "(keine Angabe)"}
Parameter:
{param_lines}

Timeframe: {timeframe}
Initial Capital: {initial_capital}
Commission: {commission_pct}% (percent)
Slippage: {slippage_ticks} ticks
Pyramiding: {pyramiding}

Anforderungen an das Script:
- `strategy(...)`-Header mit obigen Capital/Commission/Slippage/Pyramiding-Werten.
- Jeder Parameter als `input.int`/`input.float` deklariert (kein Hardcoding).
- Entry-/Exit-Logik EDGE-GETRIGGERT (nicht auf jeder Bar `strategy.close()` feuern, wenn
  die Bedingung wahr bleibt — sonst zahlt jede Bar erneut Commission/Slippage).
- Richtung `long-only`/`short-only` nur in die jeweilige Richtung eröffnen; `kombiniert`
  darf beide Richtungen nehmen.
- Bei fehlender Exit-Regel: sauberer Bar-Count-Failsafe statt endlos offener Position.
- `ta.adx(...)` existiert NICHT als Pine-Built-in — für ADX `[diplus, diminus, adx] = ta.dmi(diLength, adxLength)` verwenden.
- `ta.kama(...)` existiert NICHT als Pine-Built-in — KAMA (Kaufman Adaptive Moving Average) selbst
  aus `ta.change`/`ta.cum`/rekursivem `var float` berechnen, kein Built-in dafür nutzen.
{previous_error_block}
Antworte AUSSCHLIESSLICH mit einem einzigen ```pine-Codeblock (kein Text davor/danach),
der mit `//@version=5` beginnt."""


def _extract_pine(raw_text: str) -> str:
    matches = _PINE_FENCE_RE.findall(raw_text)
    candidate = matches[-1].strip() if matches else raw_text.strip()
    if (
        not _VERSION_TAG_RE.search(candidate)
        or _INVALID_STRATEGY_MEMBER_RE.search(candidate)
        or _INVALID_TA_BUILTIN_RE.search(candidate)
    ):
        return ""
    return candidate


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
    previous_error: str | None = None,
) -> str:
    """Haupteinstieg: erzeugt vollständigen Pine-v5-Quelltext via LLM.

    `previous_error` ist der Provider-/Compiler-Fehler eines vorherigen Versuchs
    für dieselbe Execution (Retry) — wird in den Prompt zurückgespeist, damit die
    KI sich selbst korrigiert, statt jede halluzinierte Funktion einzeln per
    Blacklist abfangen zu müssen.
    """
    direction = direction or snapshot.get("direction") or "kombiniert"
    entry_rule = (snapshot.get("entry_rule") or "").strip()
    if not entry_rule:
        raise PineGenerationError("Entry-Regel fehlt — Pine-Script kann nicht generiert werden.")

    params = params or snapshot.get("parameters") or []
    prompt = build_prompt(
        snapshot,
        params=params,
        timeframe=timeframe,
        direction=direction,
        initial_capital=initial_capital,
        commission_pct=commission_pct,
        slippage_ticks=slippage_ticks,
        pyramiding=pyramiding,
        previous_error=previous_error,
    )

    try:
        raw = run_opencode(prompt)
    except Exception as exc:  # Provider-Fehler/Timeout — kein stiller Retry, klarer Fehlergrund.
        raise PineGenerationError(f"Pine-Generierung über OpenCode fehlgeschlagen: {exc}") from exc

    pine_source = _extract_pine(raw)
    if not pine_source:
        raise PineGenerationError("OpenCode-Antwort enthielt kein gültiges Pine-v5-Script.")
    return pine_source
