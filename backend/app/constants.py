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
