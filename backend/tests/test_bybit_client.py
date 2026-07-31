"""PROJ-22: Unit-Tests fuer die Bybit-Pagination (Bug 1 — absteigende Sortierung)."""

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from app.services.bybit_client import fetch_klines


def _make_fake_urlopen(all_bars_ms: list[int]):
    """Simuliert Bybit: liefert je Request bis zu `limit` Kerzen absteigend
    sortiert aus [start, end), wie die echte API es tut."""

    def fake_urlopen(request, timeout=30):
        qs = parse_qs(urlparse(request.full_url).query)
        start = int(qs["start"][0])
        end = int(qs["end"][0])
        limit = int(qs["limit"][0])
        window = sorted([t for t in all_bars_ms if start <= t < end], reverse=True)
        page = window[:limit]
        rows = [[str(t), "1", "1", "1", "1", "1", "1"] for t in page]

        class FakeResponse:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False

            def read(self_inner):
                import json
                return json.dumps({"retCode": 0, "retMsg": "OK", "result": {"list": rows}}).encode()

        return FakeResponse()

    return fake_urlopen


def test_fetch_klines_paginates_through_descending_pages():
    """Bybit liefert neueste Kerzen zuerst — Pagination muss trotzdem die
    gesamte Historie zurueck bis start_ms abdecken (Regressionstest fuer Bug 1)."""
    interval_ms = 240 * 60 * 1000  # 4h
    start_ms = 0
    n = 2500  # > 1000 (Seitengroesse) → erzwingt mehrere Pages
    all_bars_ms = [start_ms + i * interval_ms for i in range(n)]
    end_ms = all_bars_ms[-1] + interval_ms

    fake_urlopen = _make_fake_urlopen(all_bars_ms)
    with patch("app.services.bybit_client.urlopen", side_effect=fake_urlopen):
        rows = fetch_klines("BTCUSDT", "4h", start_ms, end_ms)

    assert len(rows) == n
    returned_ms = [int(r["bar_time"].timestamp() * 1000) for r in rows]
    assert returned_ms == all_bars_ms  # vollstaendig UND aufsteigend sortiert
