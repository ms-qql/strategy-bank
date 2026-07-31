"""Bybit Public API — OHLCV-Daten abrufen (PROJ-22)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

_BASE_URL = "https://api.bybit.com"
_INTERVAL_MAP: dict[str, int] = {"1h": 60, "4h": 240, "1d": "D"}


def fetch_klines(
    symbol: str,
    timeframe: str,
    start_ms: int,
    end_ms: int,
    *,
    base_url: str = _BASE_URL,
) -> list[dict]:
    """Alle Kerzen im Zeitfenster abrufen (paginiert, max 1000 je Seite).

    Bybit liefert `/v5/market/kline` absteigend sortiert (neueste Kerze zuerst).
    Deshalb wird rückwärts paginiert: `end` wandert je Seite auf die älteste
    bisher gesehene Kerze zurück, bis `start_ms` erreicht ist.
    """
    interval = _INTERVAL_MAP.get(timeframe, 60)
    all_rows: list[dict] = []
    cursor_end = end_ms

    while cursor_end > start_ms:
        url = (
            f"{base_url}/v5/market/kline"
            f"?category=linear&symbol={symbol}&interval={interval}"
            f"&start={start_ms}&end={cursor_end}&limit=1000"
        )
        request = Request(url, headers={"User-Agent": "strategy-bank/1.0"})
        try:
            with urlopen(request, timeout=30) as resp:
                data = json.load(resp)
        except (OSError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Bybit-API nicht erreichbar: {exc}") from exc

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit-API-Fehler: {data.get('retMsg', 'Unbekannt')}")

        rows = data.get("result", {}).get("list", [])
        if not rows:
            break

        for row in rows:
            bar_time = int(row[0])
            if bar_time < start_ms or bar_time >= end_ms:
                continue
            all_rows.append({
                "bar_time": datetime.fromtimestamp(bar_time / 1000, tz=timezone.utc),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
            })

        oldest_ts = int(rows[-1][0])
        if oldest_ts >= cursor_end:
            break  # keine Fortschritt mehr moeglich, Schleife sicher beenden
        cursor_end = oldest_ts
        if len(rows) < 1000:
            break
        time.sleep(0.1)  # Rate-Limit-Schonung

    all_rows.sort(key=lambda r: r["bar_time"])
    return all_rows
