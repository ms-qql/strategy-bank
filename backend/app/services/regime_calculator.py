"""Regime-Berechnung: Z-Score + HMA-Glättung + Bestätigungslogik (PROJ-22)."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

Regime = Literal["bullish", "bearish", "sideways", "nicht verfügbar"]


def _wma(values: list[float], period: int) -> float:
    """Weighted Moving Average: weight proportional to position (1..period)."""
    total_weight = period * (period + 1) / 2
    weighted = sum(values[-period + j] * (j + 1) for j in range(period))
    return weighted / total_weight


def _hma(signal: list[float], i: int, period: int) -> float:
    """Hull Moving Average at index i over the signal series."""
    half = period // 2
    sqrt_p = int(math.sqrt(period))
    if half < 1:
        half = 1
    if sqrt_p < 1:
        sqrt_p = 1

    wma_half = _wma(signal[: i + 1], half)
    wma_full = _wma(signal[: i + 1], period)
    raw = 2 * wma_half - wma_full

    raw_vals = [raw]
    for idx in range(i - sqrt_p + 1, i):
        if idx < 0:
            continue
        half2 = _wma(signal[: idx + 1], half)
        full2 = _wma(signal[: idx + 1], period)
        raw_vals.insert(0, 2 * half2 - full2)

    return sum(raw_vals) / len(raw_vals) if raw_vals else raw


def compute_regime_bars(
    closes: list[float],
    bar_times: list[datetime],
    *,
    zscore_length: int,
    hma_length: int,
    confirmation_candles: int,
    upper_threshold: float,
    lower_threshold: float,
) -> list[dict]:
    """Berechnet Regime-Bars aus einer Schlusskursreihe.

    Returns: list of {"bar_time": datetime, "regime": str}
    """
    n = len(closes)
    result: list[dict] = []

    z_scores: list[float | None] = [None] * n
    for i in range(n):
        if i < zscore_length - 1:
            continue
        window = closes[i - zscore_length + 1 : i + 1]
        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std = math.sqrt(variance)
        if std == 0:
            continue
        z_scores[i] = (closes[i] - mean) / std

    smoothed: list[float | None] = [None] * n
    min_hma_idx = zscore_length + hma_length - 2
    for i in range(min_hma_idx, n):
        if z_scores[i] is None:
            continue
        z_vals: list[float] = []
        for j in range(i - hma_length + 1, i + 1):
            val = z_scores[j]
            if val is None:
                break
            z_vals.append(val)
        else:
            smoothed[i] = _hma(z_vals, len(z_vals) - 1, hma_length)

    candidate: Regime | None = None
    count = 0
    for i in range(n):
        bar_time = bar_times[i]
        hma_val = smoothed[i]

        if hma_val is None:
            candidate = None
            count = 0
            result.append({"bar_time": bar_time, "regime": "nicht verfügbar"})
            continue

        if hma_val > upper_threshold:
            new_candidate: Regime = "bullish"
        elif hma_val < lower_threshold:
            new_candidate = "bearish"
        else:
            new_candidate = "sideways"

        if new_candidate == candidate:
            count += 1
        else:
            candidate = new_candidate
            count = 1

        if count >= confirmation_candles:
            result.append({"bar_time": bar_time, "regime": candidate})
        elif result and result[-1]["regime"] != "nicht verfügbar":
            result.append({"bar_time": bar_time, "regime": result[-1]["regime"]})
        else:
            result.append({"bar_time": bar_time, "regime": "nicht verfügbar"})

    return result


if __name__ == "__main__":
    import random
    from datetime import datetime, timedelta, timezone

    random.seed(42)
    n = 500
    base = datetime(2021, 1, 1, tzinfo=timezone.utc)
    times = [base + timedelta(hours=4 * i) for i in range(n)]

    # Test 1: strong uptrend → mostly bullish
    closes_up = [100.0 + 0.3 * i + random.gauss(0, 3) for i in range(n)]
    rows = compute_regime_bars(closes_up, times, zscore_length=75, hma_length=2,
                                confirmation_candles=2, upper_threshold=0.75, lower_threshold=-0.75)
    regimes = {}
    for r in rows:
        regimes[r["regime"]] = regimes.get(r["regime"], 0) + 1
    print(f"Uptrend: {regimes}")

    # Test 2: downtrend → mostly bearish
    closes_down = [100.0 - 0.3 * i + random.gauss(0, 3) for i in range(n)]
    rows = compute_regime_bars(closes_down, times, zscore_length=75, hma_length=2,
                                confirmation_candles=2, upper_threshold=0.75, lower_threshold=-0.75)
    regimes = {}
    for r in rows:
        regimes[r["regime"]] = regimes.get(r["regime"], 0) + 1
    print(f"Downtrend: {regimes}")

    # Test 3: flat → mostly sideways
    closes_flat = [100.0 + random.gauss(0, 2) for _ in range(n)]
    rows = compute_regime_bars(closes_flat, times, zscore_length=75, hma_length=2,
                                confirmation_candles=2, upper_threshold=0.75, lower_threshold=-0.75)
    regimes = {}
    for r in rows:
        regimes[r["regime"]] = regimes.get(r["regime"], 0) + 1
    print(f"Flat: {regimes}")
