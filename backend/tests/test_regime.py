"""PROJ-22: Integrationstests für Regime-Analyse."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from app.db import run_command, run_query, run_query_one


def _make_hal_result(client, asset: str = "BTC", timeframe: str = "4h") -> dict:
    """Create HAL import run + file + result in test DB."""
    run_id = uuid4()
    file_id = uuid4()
    result_id = uuid4()
    run_command(
        "INSERT INTO hal_import_runs (id, total_files) VALUES (%s, 1)",
        [run_id],
    )
    run_command(
        """INSERT INTO hal_imported_files (id, import_run_id, origin_path, content_hash,
           import_version, is_current, processing_status)
           VALUES (%s, %s, %s, %s, 1, true, 'importiert')""",
        [file_id, run_id, "test.md", str(uuid4())],
    )
    run_command(
        """INSERT INTO hal_results (id, imported_file_id, strategy_name, asset, timeframe,
           period_start, period_end, net_return_pct, max_drawdown_pct, trade_count,
           report_link, import_version)
           VALUES (%s, %s, 'Test Strategy', %s, %s, '2021-01-01', '2024-12-31', 42.0, -15.0, 50,
           'https://mcp-api.trader.dev/backtest/test123', 1)""",
        [result_id, file_id, asset, timeframe],
    )
    return {"id": str(result_id), "asset": asset, "timeframe": timeframe}


class TestRegimeModels:
    """CRUD for regime model versions."""

    def test_create_model_minimal(self, client):
        resp = client.post("/regime/models", json={
            "name": "zscore-hma-v1",
            "upper_threshold": 0.75,
            "lower_threshold": -0.75,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "zscore-hma-v1"
        assert data["zscore_length"] == 75
        assert data["hma_length"] == 2
        assert data["confirmation_candles"] == 2
        assert data["upper_threshold"] == 0.75
        assert data["lower_threshold"] == -0.75

    def test_create_model_custom_params(self, client):
        resp = client.post("/regime/models", json={
            "name": "zscore-hma-v2",
            "zscore_length": 50,
            "hma_length": 5,
            "confirmation_candles": 3,
            "upper_threshold": 1.0,
            "lower_threshold": -1.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["zscore_length"] == 50
        assert data["hma_length"] == 5
        assert data["confirmation_candles"] == 3

    def test_create_model_invalid_thresholds(self, client):
        resp = client.post("/regime/models", json={
            "name": "bad",
            "upper_threshold": -0.5,
            "lower_threshold": 0.5,
        })
        assert resp.status_code == 422
        assert "untere Schwelle" in resp.json()["detail"]

    def test_create_model_equal_thresholds(self, client):
        resp = client.post("/regime/models", json={
            "name": "bad",
            "upper_threshold": 0.5,
            "lower_threshold": 0.5,
        })
        assert resp.status_code == 422

    def test_list_models(self, client):
        client.post("/regime/models", json={
            "name": "m1", "upper_threshold": 0.75, "lower_threshold": -0.75,
        })
        client.post("/regime/models", json={
            "name": "m2", "upper_threshold": 1.0, "lower_threshold": -1.0,
        })
        resp = client.get("/regime/models")
        assert resp.status_code == 200
        models = resp.json()
        assert len(models) == 2
        names = {m["name"] for m in models}
        assert names == {"m1", "m2"}


class TestRegimeSeries:
    """Time series CRUD and import."""

    def _create_model(self, client) -> dict:
        resp = client.post("/regime/models", json={
            "name": "zscore-hma-v1",
            "upper_threshold": 0.75,
            "lower_threshold": -0.75,
        })
        return resp.json()

    def test_list_series_empty(self, client):
        resp = client.get("/regime/series")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_import_series(self, client):
        mv = self._create_model(client)
        bars = [
            {"bar_time": "2021-01-01T00:00:00Z", "regime": "bullish"},
            {"bar_time": "2021-01-01T04:00:00Z", "regime": "sideways"},
        ]
        resp = client.post("/regime/series/import", json={
            "asset": "BTC",
            "timeframe": "4h",
            "model_version_id": mv["id"],
            "bars": bars,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["bars_inserted"] == 2
        assert data["bars_skipped"] == 0

    def test_import_series_dedup(self, client):
        mv = self._create_model(client)
        bars = [{"bar_time": "2021-01-01T00:00:00Z", "regime": "bullish"}]
        r1 = client.post("/regime/series/import", json={
            "asset": "BTC", "timeframe": "4h", "model_version_id": mv["id"], "bars": bars,
        })
        assert r1.json()["bars_inserted"] == 1
        r2 = client.post("/regime/series/import", json={
            "asset": "BTC", "timeframe": "4h", "model_version_id": mv["id"], "bars": bars,
        })
        assert r2.json()["bars_inserted"] == 0
        assert r2.json()["bars_skipped"] == 1

    def test_get_series_detail(self, client):
        mv = self._create_model(client)
        bars = [
            {"bar_time": "2021-01-01T00:00:00Z", "regime": "bullish"},
            {"bar_time": "2021-01-01T04:00:00Z", "regime": "sideways"},
        ]
        imp = client.post("/regime/series/import", json={
            "asset": "BTC", "timeframe": "4h", "model_version_id": mv["id"], "bars": bars,
        })
        resp = client.get("/regime/series")
        assert resp.status_code == 200
        series_list = resp.json()
        assert len(series_list) == 1
        assert series_list[0]["bar_count"] == 2
        assert series_list[0]["model_version_name"] == "zscore-hma-v1"

    def test_series_filter_by_asset(self, client):
        mv = self._create_model(client)
        client.post("/regime/series/import", json={
            "asset": "BTC", "timeframe": "4h", "model_version_id": mv["id"], "bars": [],
        })
        client.post("/regime/series/import", json={
            "asset": "ETH", "timeframe": "4h", "model_version_id": mv["id"], "bars": [],
        })
        resp = client.get("/regime/series?asset=BTC")
        assert len(resp.json()) == 1
        resp = client.get("/regime/series?timeframe=1h")
        assert len(resp.json()) == 0


class TestTradeFetch:
    """Trade-Nachladung endpoints."""

    def _create_model(self, client) -> dict:
        resp = client.post("/regime/models", json={
            "name": "zscore-hma-v1",
            "upper_threshold": 0.75, "lower_threshold": -0.75,
        })
        return resp.json()

    def test_fetch_no_report_link(self, client):
        result_id = str(uuid4())
        import_run_id = uuid4()
        run_command("INSERT INTO hal_import_runs (id, total_files) VALUES (%s, 1)", [import_run_id])
        file_id = uuid4()
        run_command(
            """INSERT INTO hal_imported_files (id, import_run_id, origin_path, content_hash,
               import_version, is_current, processing_status)
               VALUES (%s, %s, 'test', %s, 1, true, 'importiert')""",
            [file_id, import_run_id, str(uuid4())],
        )
        run_command(
            """INSERT INTO hal_results (id, imported_file_id, strategy_name, asset, timeframe,
               period_start, net_return_pct, max_drawdown_pct, trade_count, import_version)
               VALUES (%s, %s, 'Test', 'BTC', '4h', '2021-01-01', 10.0, -5.0, 10, 1)""",
            [result_id, file_id],
        )
        resp = client.post(f"/regime/hal-results/{result_id}/trades/fetch")
        assert resp.status_code == 400
        assert "Report-Link" in resp.json()["detail"]

    def test_list_trades_empty(self, client):
        hr = _make_hal_result(client)
        resp = client.get(f"/regime/hal-results/{hr['id']}/trades")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_trades_not_found(self, client):
        resp = client.get(f"/regime/hal-results/{uuid4()}/trades")
        assert resp.status_code == 404


class TestRegimeEvaluation:
    """Regime evaluation computation."""

    def test_no_trades(self, client):
        hr = _make_hal_result(client)
        resp = client.get(f"/regime/hal-results/{hr['id']}/regime")
        assert resp.status_code == 400
        assert "Zeitgestempelte Ergebnisdaten fehlen" in resp.json()["detail"]

    def test_no_model_version(self, client):
        hr = _make_hal_result(client)
        run_command(
            "INSERT INTO result_trades (id, hal_result_id, direction, entry_time, exit_time, net_pnl) "
            "VALUES (%s, %s, 'long', '2021-06-01T00:00:00Z', '2021-06-15T00:00:00Z', 100)",
            [uuid4(), hr["id"]],
        )
        resp = client.get(f"/regime/hal-results/{hr['id']}/regime")
        assert resp.status_code == 404
        assert "Modellversion" in resp.json()["detail"]

    def test_evaluation_happy_path(self, client):
        """Full flow: model → series → bars → trades → evaluation."""
        # Create model
        mv_resp = client.post("/regime/models", json={
            "name": "zscore-hma-v1", "upper_threshold": 0.75, "lower_threshold": -0.75,
        })
        mv = mv_resp.json()

        # Create HAL result
        result_id = uuid4()
        run_id = uuid4()
        run_command("INSERT INTO hal_import_runs (id, total_files) VALUES (%s, 1)", [run_id])
        file_id = uuid4()
        run_command(
            """INSERT INTO hal_imported_files (id, import_run_id, origin_path, content_hash,
               import_version, is_current, processing_status)
               VALUES (%s, %s, 'test', %s, 1, true, 'importiert')""",
            [file_id, run_id, str(uuid4())],
        )
        run_command(
            """INSERT INTO hal_results (id, imported_file_id, strategy_name, asset, timeframe,
               period_start, period_end, net_return_pct, max_drawdown_pct, trade_count,
               report_link, import_version)
               VALUES (%s, %s, 'Test Strategy', 'BTC', '4h', '2021-01-01', '2021-12-31',
               42.0, -15.0, 50, 'https://mcp-api.trader.dev/backtest/abc123', 1)""",
            [result_id, file_id],
        )
        hr_id = str(result_id)

        # Import regime bars
        bars = [
            {"bar_time": "2021-06-01T00:00:00Z", "regime": "bullish"},
            {"bar_time": "2021-06-01T04:00:00Z", "regime": "bullish"},
            {"bar_time": "2021-07-01T00:00:00Z", "regime": "bearish"},
            {"bar_time": "2021-07-01T04:00:00Z", "regime": "bearish"},
        ]
        client.post("/regime/series/import", json={
            "asset": "BTC", "timeframe": "4h", "model_version_id": mv["id"], "bars": bars,
        })

        # Insert trades
        run_command(
            "INSERT INTO result_trades (id, hal_result_id, direction, entry_time, exit_time, net_pnl) "
            "VALUES (%s, %s, 'long', '2021-06-01T00:00:00Z', '2021-06-15T00:00:00Z', 500)",
            [uuid4(), hr_id],
        )
        run_command(
            "INSERT INTO result_trades (id, hal_result_id, direction, entry_time, exit_time, net_pnl) "
            "VALUES (%s, %s, 'long', '2021-06-01T04:00:00Z', '2021-06-15T04:00:00Z', 300)",
            [uuid4(), hr_id],
        )
        run_command(
            "INSERT INTO result_trades (id, hal_result_id, direction, entry_time, exit_time, net_pnl) "
            "VALUES (%s, %s, 'long', '2021-07-01T00:00:00Z', '2021-07-15T00:00:00Z', -200)",
            [uuid4(), hr_id],
        )
        run_command(
            "INSERT INTO result_trades (id, hal_result_id, direction, entry_time, exit_time, net_pnl) "
            "VALUES (%s, %s, 'short', '2021-07-01T04:00:00Z', '2021-07-15T04:00:00Z', -100)",
            [uuid4(), hr_id],
        )
        # Trade outside regime coverage
        run_command(
            "INSERT INTO result_trades (id, hal_result_id, direction, entry_time, exit_time, net_pnl) "
            "VALUES (%s, %s, 'long', '2021-12-01T00:00:00Z', '2021-12-15T00:00:00Z', 50)",
            [uuid4(), hr_id],
        )

        resp = client.get(f"/regime/hal-results/{hr_id}/regime?model_version_id={mv['id']}")
        assert resp.status_code == 200
        result = resp.json()

        assert result["assignment_rule"] == "entry_bar_regime"
        # Nur 4 Bars importiert fuer ein Jahr Backtest-Zeitraum → Abdeckung bezogen auf
        # den Backtest-Zeitraum (nicht nur auf die vorhandenen Bars) ist gering.
        assert result["is_incomplete"]

        details = {d["regime"]: d for d in result["regime_details"]}
        assert details["bullish"]["trade_count"] == 2
        assert details["bullish"]["net_pnl"] == 800.0
        assert details["bearish"]["trade_count"] == 2
        assert details["bearish"]["net_pnl"] == -300.0
        assert details["ohne Regimezuordnung"]["trade_count"] == 1
        assert details["ohne Regimezuordnung"]["net_pnl"] == 50.0

        assert result["regime_dominance"] == "bullish"

        assert details["bullish"]["small_sample"] is True  # 2 trades < 6
        assert details["bearish"]["small_sample"] is True

    def test_small_sample_badge(self, client):
        """Less than 6 trades in a regime → small_sample badge."""
        mv_resp = client.post("/regime/models", json={
            "name": "zscore-hma-v1", "upper_threshold": 0.75, "lower_threshold": -0.75,
        })
        mv = mv_resp.json()
        hr = _make_hal_result(client)

        bars = [{"bar_time": "2021-06-01T00:00:00Z", "regime": "bullish"}]
        client.post("/regime/series/import", json={
            "asset": "BTC", "timeframe": "4h", "model_version_id": mv["id"], "bars": bars,
        })
        run_command(
            "INSERT INTO result_trades (id, hal_result_id, direction, entry_time, exit_time, net_pnl) "
            "VALUES (%s, %s, 'long', '2021-06-01T00:00:00Z', '2021-06-15T00:00:00Z', 100)",
            [uuid4(), hr["id"]],
        )

        resp = client.get(f"/regime/hal-results/{hr['id']}/regime?model_version_id={mv['id']}")
        assert resp.status_code == 200
        details = {d["regime"]: d for d in resp.json()["regime_details"]}
        assert details["bullish"]["small_sample"] is True

    def test_no_dominance_on_negative_total(self, client):
        """Regime-Dominanz only when total P&L > 0."""
        mv_resp = client.post("/regime/models", json={
            "name": "zscore-hma-v1", "upper_threshold": 0.75, "lower_threshold": -0.75,
        })
        mv = mv_resp.json()
        hr = _make_hal_result(client)

        bars = [
            {"bar_time": "2021-06-01T00:00:00Z", "regime": "bullish"},
            {"bar_time": "2021-07-01T00:00:00Z", "regime": "bearish"},
        ]
        client.post("/regime/series/import", json={
            "asset": "BTC", "timeframe": "4h", "model_version_id": mv["id"], "bars": bars,
        })
        run_command(
            "INSERT INTO result_trades (id, hal_result_id, direction, entry_time, exit_time, net_pnl) "
            "VALUES (%s, %s, 'long', '2021-06-01T00:00:00Z', '2021-06-15T00:00:00Z', 100)",
            [uuid4(), hr["id"]],
        )
        run_command(
            "INSERT INTO result_trades (id, hal_result_id, direction, entry_time, exit_time, net_pnl) "
            "VALUES (%s, %s, 'long', '2021-07-01T00:00:00Z', '2021-07-15T00:00:00Z', -200)",
            [uuid4(), hr["id"]],
        )

        resp = client.get(f"/regime/hal-results/{hr['id']}/regime?model_version_id={mv['id']}")
        assert resp.status_code == 200
        assert resp.json()["regime_dominance"] is None

    def test_trade_entry_between_bars_uses_bucket_regime(self, client):
        """Bug 2: Entry-Zeitpunkt muss der umschliessenden Bar zugeordnet werden,
        nicht nur bei exakter Zeitstempel-Gleichheit."""
        mv_resp = client.post("/regime/models", json={
            "name": "zscore-hma-v1", "upper_threshold": 0.75, "lower_threshold": -0.75,
        })
        mv = mv_resp.json()
        hr = _make_hal_result(client)

        bars = [
            {"bar_time": "2021-06-01T00:00:00Z", "regime": "bullish"},
            {"bar_time": "2021-06-01T04:00:00Z", "regime": "bearish"},
        ]
        client.post("/regime/series/import", json={
            "asset": "BTC", "timeframe": "4h", "model_version_id": mv["id"], "bars": bars,
        })
        # Entry mitten in der ersten 4h-Bar (nicht exakt auf Bar-Grenze)
        run_command(
            "INSERT INTO result_trades (id, hal_result_id, direction, entry_time, exit_time, net_pnl) "
            "VALUES (%s, %s, 'long', '2021-06-01T02:30:00Z', '2021-06-01T03:00:00Z', 100)",
            [uuid4(), hr["id"]],
        )
        # Entry weit ausserhalb jeder Bar-Abdeckung (Luecke groesser als ein Intervall)
        run_command(
            "INSERT INTO result_trades (id, hal_result_id, direction, entry_time, exit_time, net_pnl) "
            "VALUES (%s, %s, 'long', '2021-06-05T00:00:00Z', '2021-06-05T01:00:00Z', 50)",
            [uuid4(), hr["id"]],
        )

        resp = client.get(f"/regime/hal-results/{hr['id']}/regime?model_version_id={mv['id']}")
        assert resp.status_code == 200
        details = {d["regime"]: d for d in resp.json()["regime_details"]}
        assert details["bullish"]["trade_count"] == 1
        assert details["bullish"]["net_pnl"] == 100.0
        assert details["ohne Regimezuordnung"]["trade_count"] == 1

    def test_coverage_based_on_backtest_period(self, client):
        """Bug 3: Abdeckung bezieht sich auf den Backtest-Zeitraum, nicht auf
        die gesamte (moeglicherweise laengere) Zeitreihe."""
        mv_resp = client.post("/regime/models", json={
            "name": "zscore-hma-v1", "upper_threshold": 0.75, "lower_threshold": -0.75,
        })
        mv = mv_resp.json()

        result_id = uuid4()
        run_id = uuid4()
        run_command("INSERT INTO hal_import_runs (id, total_files) VALUES (%s, 1)", [run_id])
        file_id = uuid4()
        run_command(
            """INSERT INTO hal_imported_files (id, import_run_id, origin_path, content_hash,
               import_version, is_current, processing_status)
               VALUES (%s, %s, 'test', %s, 1, true, 'importiert')""",
            [file_id, run_id, str(uuid4())],
        )
        # Backtest-Zeitraum ist nur ein Tag (2021-06-01) → 6 Bars bei 4h-Timeframe
        run_command(
            """INSERT INTO hal_results (id, imported_file_id, strategy_name, asset, timeframe,
               period_start, period_end, net_return_pct, max_drawdown_pct, trade_count,
               report_link, import_version)
               VALUES (%s, %s, 'Test Strategy', 'BTC', '4h', '2021-06-01', '2021-06-01',
               10.0, -5.0, 1, 'https://mcp-api.trader.dev/backtest/cov1', 1)""",
            [result_id, file_id],
        )
        hr_id = str(result_id)

        bars = [
            {"bar_time": "2021-06-01T00:00:00Z", "regime": "bullish"},
            {"bar_time": "2021-06-01T04:00:00Z", "regime": "bullish"},
            {"bar_time": "2021-06-01T08:00:00Z", "regime": "bullish"},
            {"bar_time": "2021-06-01T12:00:00Z", "regime": "bullish"},
            {"bar_time": "2021-06-01T16:00:00Z", "regime": "bullish"},
            {"bar_time": "2021-06-01T20:00:00Z", "regime": "bullish"},
        ]
        client.post("/regime/series/import", json={
            "asset": "BTC", "timeframe": "4h", "model_version_id": mv["id"], "bars": bars,
        })
        run_command(
            "INSERT INTO result_trades (id, hal_result_id, direction, entry_time, exit_time, net_pnl) "
            "VALUES (%s, %s, 'long', '2021-06-01T00:00:00Z', '2021-06-01T02:00:00Z', 100)",
            [uuid4(), hr_id],
        )

        resp = client.get(f"/regime/hal-results/{hr_id}/regime?model_version_id={mv['id']}")
        assert resp.status_code == 200
        assert not resp.json()["is_incomplete"]  # 6/6 Bars im Backtest-Zeitraum vorhanden


class TestRegimeCalculator:
    """Unit tests for regime_calculator.py."""

    def test_constant_price_all_unavailable(self):
        from app.services.regime_calculator import compute_regime_bars
        n = 200
        closes = [100.0] * n
        base = datetime(2021, 1, 1, tzinfo=timezone.utc)
        times = [base + timedelta(hours=4 * i) for i in range(n)]
        rows = compute_regime_bars(closes, times, zscore_length=75, hma_length=2,
                                    confirmation_candles=2, upper_threshold=0.75, lower_threshold=-0.75)
        regimes = {r["regime"] for r in rows}
        assert regimes == {"nicht verfügbar"}

    def test_uptrend_bullish(self):
        from app.services.regime_calculator import compute_regime_bars
        import random
        random.seed(1)
        n = 300
        closes = [100.0 + 0.5 * i + random.gauss(0, 2) for i in range(n)]
        base = datetime(2021, 1, 1, tzinfo=timezone.utc)
        times = [base + timedelta(hours=4 * i) for i in range(n)]
        rows = compute_regime_bars(closes, times, zscore_length=75, hma_length=2,
                                    confirmation_candles=2, upper_threshold=0.75, lower_threshold=-0.75)
        regimes = {}
        for r in rows:
            regimes[r["regime"]] = regimes.get(r["regime"], 0) + 1
        assert regimes.get("bullish", 0) > regimes.get("bearish", 0)
        assert regimes["nicht verfügbar"] > 0  # warmup

    def test_downtrend_bearish(self):
        from app.services.regime_calculator import compute_regime_bars
        import random
        random.seed(1)
        n = 300
        closes = [100.0 - 0.5 * i + random.gauss(0, 2) for i in range(n)]
        base = datetime(2021, 1, 1, tzinfo=timezone.utc)
        times = [base + timedelta(hours=4 * i) for i in range(n)]
        rows = compute_regime_bars(closes, times, zscore_length=75, hma_length=2,
                                    confirmation_candles=2, upper_threshold=0.75, lower_threshold=-0.75)
        regimes = {}
        for r in rows:
            regimes[r["regime"]] = regimes.get(r["regime"], 0) + 1
        assert regimes.get("bearish", 0) > regimes.get("bullish", 0)
