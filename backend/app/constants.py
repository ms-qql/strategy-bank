"""Feste MVP-Kategorienliste (PROJ-2 Edge Cases) — im MVP nicht erweiterbar."""

CATEGORIES: list[str] = [
    "Trendfolge",
    "Mean Reversion",
    "Breakout",
    "Volatilität",
    "Momentum",
    "Saison/Zeit",
    "Preis-/Candlestick-Muster",
    "Hybrid",
    "Sonstige",
]

FALLBACK_CATEGORY = "Sonstige"

DIRECTIONS: list[str] = ["kombiniert", "long-only", "short-only"]

# PROJ-4: Richtungsmodi je Batch-Run — dieselben Werte wie DIRECTIONS.
DIRECTION_MODES: list[str] = DIRECTIONS

RUN_KINDS: list[str] = ["standard", "holdout", "forward_test"]

DEFAULT_INSTRUMENTS: list[dict[str, str]] = [
    {"provider_symbol": "BYBIT:BTCUSDT.P", "label": "BTC"},
]

DEFAULT_TIMEFRAME = "4h"
DEFAULT_PERIOD_START = "2021-01-01"
DEFAULT_PERIOD_END = "2024-12-31"
HOLDOUT_PERIOD_START = "2025-01-01"

# PROJ-10: Positions-, Exit- und Crypto-MTS-Kompatibilitätsmodell

POSITION_MODES: list[str] = ["signal_reversal", "entry_exit"]

EXIT_RULE_ORIGINS: list[str] = ["source", "system_default", "user"]

MTS_COMPATIBILITIES: list[str] = ["continuous", "discrete", "unclear"]

SYSTEM_DEFAULT_EXIT_RULE = "Exit nach 10 vollständig vergangenen Bars"

SYSTEM_DEFAULT_EXIT_BARS = 10
