"""Deterministische Merkmalsableitung aus Pine Script Code.

Extrahiert Indikatoren, Zählwerte und Entry-/Exit-Archetypen
rein regelbasiert — kein KI-Aufruf, keine manuelle Bestätigung.
"""

import re
from dataclasses import dataclass, field


INDICATOR_PATTERNS = [
    (r"\bta\.ema\b", "EMA"),
    (r"\bta\.sma\b", "SMA"),
    (r"\bta\.hma\b", "HMA"),
    (r"\bta\.wma\b", "WMA"),
    (r"\bta\.vwma\b", "VWMA"),
    (r"\bta\.rma\b", "RMA"),
    (r"\bta\.alma\b", "ALMA"),
    (r"\bta\.rsi\b", "RSI"),
    (r"\bta\.stoch\b", "Stochastic"),
    (r"\bta\.macd\b", "MACD"),
    (r"\bta\.bb\b", "Bollinger"),
    (r"\bta\.atr\b", "ATR"),
    (r"\bta\.supertrend\b", "SuperTrend"),
    (r"\bta\.cci\b", "CCI"),
    (r"\bta\.mfi\b", "MFI"),
    (r"\bta\.adx\b", "ADX"),
    (r"\bta\.dmi\b", "DMI"),
    (r"\bta\.ao\b", "AO"),
    (r"\bta\.mom\b", "Momentum"),
    (r"\bta\.roc\b", "ROC"),
    (r"\bta\.willr\b", "WilliamsR"),
    (r"\bta\.psar\b", "ParabolicSAR"),
    (r"\bta\.donchian\b", "Donchian"),
    (r"\bta\.kc\b", "Keltner"),
    (r"\bta\.cmo\b", "CMO"),
    (r"\bta\.tsi\b", "TSI"),
    (r"\bta\.correlation\b", "Correlation"),
    (r"\bta\.linreg\b", "LinReg"),
    (r"\bta\.obv\b", "OBV"),
    (r"\bta\.vwap\b", "VWAP"),
    (r"\bta\.pivot\b", "Pivot"),
    (r"\bta\.zscore|zscore|z_score\b", "Z-Score"),
    (r"\bta\.cross\b", "Crossover"),  # ponytail: Crossover is a utility, not indicator. Track anyway.
]

ENTRY_PATTERNS = [
    (r"ta\.crossover\b", "Crossover"),
    (r"ta\.crossunder\b", "Crossunder"),
    (r"\bbreakout\b|break\s*out|break\s+above", "Breakout"),
    (r"\bbreakdown\b|break\s*down|break\s+below", "Breakdown"),
    (r"\bta\.highest\b|ta\.lowest\b", "Kanalausbruch"),
    (r"pullback|retracement|retest|bounce", "Pullback"),
    (r"overbought|oversold", "Überkauft/Überverkauft"),
]

EXIT_PATTERNS = [
    (r"strategy\.exit.*stop\s*=\s*", "Stop-Loss"),
    (r"strategy\.exit.*limit\s*=\s*", "Take-Profit"),
    (r"trailing\s*stop|strategy\.exit.*trail", "Trailing-Stop"),
    (r"ta\.crossover|ta\.crossunder|gegensignal|reverse\s*signal", "Gegensignal"),
    (r"time\s*stop|barssince|bars\s*since\s*entry", "Time-Stop"),
]

DIRECTION_INDICATORS = [
    (r"\bstrategy\.direction\.(long|short|all)\b", None),
]


@dataclass
class PineFeatures:
    indicators: list[str] = field(default_factory=list)
    indicator_count: int = 0
    parameter_count: int = 0
    entry_archetype: str = "nicht verfügbar"
    exit_archetype: str = "nicht verfügbar"


def extract_pine_features(pine_code: str) -> PineFeatures:
    if not pine_code:
        return PineFeatures()

    code_lower = pine_code.lower()

    indicators = _extract_indicators(code_lower)
    entry = _extract_archetype(code_lower, ENTRY_PATTERNS)
    exit_archetype = _extract_archetype(code_lower, EXIT_PATTERNS)
    param_count = _count_parameters(pine_code)

    return PineFeatures(
        indicators=sorted(indicators),
        indicator_count=len(indicators),
        parameter_count=param_count,
        entry_archetype=entry,
        exit_archetype=exit_archetype,
    )


def _extract_indicators(code_lower: str) -> list[str]:
    found: set[str] = set()
    for pattern, name in INDICATOR_PATTERNS:
        if re.search(pattern, code_lower):
            found.add(name)
    return sorted(found)


def _extract_archetype(code_lower: str, patterns: list[tuple[str, str]]) -> str:
    matches: list[str] = []
    for pattern, name in patterns:
        if re.search(pattern, code_lower):
            matches.append(name)

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return matches[0]  # first match wins; "nicht verfügbar" would imply nothing found
    return "nicht verfügbar"


def _count_parameters(pine_code: str) -> int:
    return len(re.findall(r"^\s*(\w+)\s*=\s*input\.", pine_code, re.MULTILINE))
