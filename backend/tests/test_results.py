"""PROJ-7: Ergebnisvergleich — Backend-Tests."""
import json
from unittest.mock import patch
from uuid import uuid4

import pytest
from app.db import run_command, run_query


def _make_source() -> str:
    row = run_command(
        "INSERT INTO sources (content, source_hash, source_type) VALUES (%s, %s, %s) RETURNING id",
        ["Test content", str(uuid4()), "text"],
        returning=True,
    )
    return str(row["id"])


def _make_extraction_run(source_id: str) -> str:
    row = run_command(
        """INSERT INTO extraction_runs (source_id, status, model, prompt_version)
           VALUES (%s, 'abgeschlossen', 'gpt-4', 'v1') RETURNING id""",
        [source_id],
        returning=True,
    )
    return str(row["id"])


def _make_frozen_version(client) -> dict:
    source_id = _make_source()
    run_id = _make_extraction_run(source_id)
    draft_id = str(uuid4())
    run_command(
        """INSERT INTO strategy_drafts
           (id, family_id, extraction_run_id, source_hash, version,
            name, thesis, category, direction,
            entry_rule, exit_rule, warmup_requirement, status,
            position_mode, position_mode_confirmed,
            mts_compatibility, mts_confirmed)
           VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        [
            draft_id, draft_id, run_id, "abc123",
            "Test Strategy", "Test thesis", "Trendfolge", "kombiniert",
            "RSI > 30", "RSI < 70", "100 bars", "Entwurf",
            "entry_exit", True, "discrete", True,
        ],
    )
    resp = client.post(f"/drafts/{draft_id}/freeze")
    assert resp.status_code == 201, resp.text
    return resp.json()


def _make_profile(client) -> dict:
    resp = client.post(
        "/backtest-profiles",
        json={
            "name": "Standard",
            "timezone_session": "Exchange",
            "order_type": "Market",
            "position_sizing": "Fix 100%",
            "compounding_rule": "Kein Compounding",
            "missing_bars_handling": "Bar überspringen",
            "corporate_actions_handling": "Ignorieren",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _make_confirmed_batch(client, version_id: str, profile_id: str) -> dict:
    resp = client.post(
        "/batches",
        json={"backtest_profile_id": profile_id, "strategy_version_ids": [version_id]},
    )
    batch = resp.json()
    with patch("app.routes.batches.get_credits") as mock:
        mock.return_value = {"balance": 1000, "tier": "free", "reset": "2026-07-22", "weekly_free": 1000}
        resp = client.post(f"/batches/{batch['id']}/confirm", json={"credit_max": 3})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _attach_backtest_execution(run_id: str, backtest_result: dict | None = None, report_link: str | None = None) -> str:
    exec_id = str(uuid4())
    r = run_query("SELECT strategy_version_id, provider_symbol, direction_mode FROM runs WHERE id = %s", [run_id])[0]
    b = run_query("SELECT backtest_profile_id, run_kind FROM batches WHERE id = (SELECT batch_id FROM runs WHERE id = %s)", [run_id])[0]
    run_command(
        """
        INSERT INTO backtest_executions
            (id, idempotency_key, strategy_version_id, provider_symbol,
             timeframe, period_start, period_end, direction_mode,
             backtest_profile_version_id, evaluation_type, pine_source,
             executor_fingerprint, provider_status, backtest_result,
             report_link, report_available)
        VALUES (%s, %s, %s, %s, '4h', '2021-01-01', '2024-12-31', %s, %s, %s, '//@version=5', 'fp', 'completed', %s, %s, %s)
        """,
        [
            exec_id, f"ik-{exec_id}", str(r["strategy_version_id"]), r["provider_symbol"],
            r["direction_mode"], str(b["backtest_profile_id"]), b["run_kind"],
            json.dumps(backtest_result) if backtest_result else None,
            report_link,
            bool(report_link),
        ],
    )
    run_command("UPDATE runs SET backtest_execution_id = %s, status = 'erfolgreich' WHERE id = %s", [exec_id, run_id])
    return exec_id


def _find_run(client, run_id: str) -> dict:
    resp = client.get("/results")
    assert resp.status_code == 200
    for row in resp.json():
        if row["run_id"] == run_id:
            return row
    pytest.fail(f"Run {run_id} not found in /results")


@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


class TestResultsEmpty:
    def test_no_runs_returns_empty_list(self, client):
        resp = client.get("/results")
        assert resp.status_code == 200
        assert resp.json() == []


class TestResultsWithData:
    def test_single_run_returns_row_with_strategy_and_profile(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = _make_confirmed_batch(client, version["id"], profile["id"])

        runs = run_query("SELECT id FROM runs WHERE batch_id = %s LIMIT 1", [batch["id"]])
        run_id = str(runs[0]["id"])

        bt = {"netProfitPct": 15.5, "cagrPct": 3.67, "profitFactor": 1.8,
              "sharpeRatio": 1.2, "maxDrawdownPct": -12.3, "tradeCount": 42}
        _attach_backtest_execution(run_id, bt, "https://trader.dev/report/123")

        r = _find_run(client, run_id)
        assert r["strategy_id"] == version["id"]
        assert r["strategy_name"] == "Test Strategy"
        assert r["strategy_version_number"] == version["version_number"]
        assert r["category"] == "Trendfolge"
        assert r["instrument"] is not None
        assert r["direction"] == "kombiniert"
        assert r["result_type"] == "standard"
        assert r["status"] == "erfolgreich"
        assert r["profile_id"] == profile["id"]
        assert r["profile_name"] == "Standard"
        assert r["profile_version_number"] == 1
        assert r["net_profit_pct"] == 15.5
        assert r["cagr_pct"] == 3.67
        assert r["trade_count"] == 42
        assert r["max_drawdown_pct"] == -12.3
        assert r["sharpe_ratio"] == 1.2
        assert r["profit_factor"] == 1.8
        assert r["report_link"] == "https://trader.dev/report/123"
        assert r["incomplete"] is False

    def test_run_without_execution_shows_null_metrics(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = _make_confirmed_batch(client, version["id"], profile["id"])

        runs = run_query("SELECT id FROM runs WHERE batch_id = %s LIMIT 1", [batch["id"]])
        run_id = str(runs[0]["id"])

        r = _find_run(client, run_id)
        assert r["net_profit_pct"] is None
        assert r["cagr_pct"] is None
        assert r["trade_count"] is None
        assert r["sharpe_ratio"] is None
        assert r["incomplete"] is False

    def test_metrics_without_report_link_marked_incomplete(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = _make_confirmed_batch(client, version["id"], profile["id"])

        runs = run_query("SELECT id FROM runs WHERE batch_id = %s LIMIT 1", [batch["id"]])
        run_id = str(runs[0]["id"])

        bt = {"netProfitPct": 10.0, "tradeCount": 30, "cagrPct": 2.5,
              "maxDrawdownPct": -5.0, "sharpeRatio": 0.8, "profitFactor": 1.3}
        _attach_backtest_execution(run_id, bt, None)

        r = _find_run(client, run_id)
        assert r["net_profit_pct"] == 10.0
        assert r["incomplete"] is True

    def test_low_activity_below_threshold(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = _make_confirmed_batch(client, version["id"], profile["id"])

        runs = run_query("SELECT id FROM runs WHERE batch_id = %s LIMIT 1", [batch["id"]])
        run_id = str(runs[0]["id"])

        bt = {"netProfitPct": 5.0, "tradeCount": 10, "cagrPct": 1.2,
              "maxDrawdownPct": -3.0, "sharpeRatio": 0.5, "profitFactor": 1.1}
        _attach_backtest_execution(run_id, bt, "https://trader.dev/report/low")

        r = _find_run(client, run_id)
        assert r["trade_count"] == 10
        assert r["low_activity"] is True

    def test_zero_trades_shows_unavailable_metrics(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = _make_confirmed_batch(client, version["id"], profile["id"])

        runs = run_query("SELECT id FROM runs WHERE batch_id = %s LIMIT 1", [batch["id"]])
        run_id = str(runs[0]["id"])

        bt = {"netProfitPct": 0.0, "tradeCount": 0, "maxDrawdownPct": 0.0}
        _attach_backtest_execution(run_id, bt, "https://trader.dev/report/zero")

        r = _find_run(client, run_id)
        assert r["trade_count"] == 0
        assert r["low_activity"] is True
        assert r["calmar_ratio"] is None
        assert r["cagr_pct"] == 0.0

    def test_calmar_computed_from_cagr_and_drawdown(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = _make_confirmed_batch(client, version["id"], profile["id"])

        runs = run_query("SELECT id FROM runs WHERE batch_id = %s LIMIT 1", [batch["id"]])
        run_id = str(runs[0]["id"])

        bt = {"netProfitPct": 20.0, "cagrPct": 4.0, "tradeCount": 50,
              "maxDrawdownPct": -10.0, "sharpeRatio": 1.5, "profitFactor": 2.0}
        _attach_backtest_execution(run_id, bt, "https://trader.dev/report/abc")

        r = _find_run(client, run_id)
        assert r["calmar_ratio"] == 0.4

    def test_cagr_fallback_from_net_return_and_period(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = _make_confirmed_batch(client, version["id"], profile["id"])

        runs = run_query("SELECT id FROM runs WHERE batch_id = %s LIMIT 1", [batch["id"]])
        run_id = str(runs[0]["id"])

        bt = {"netProfitPct": 16.08, "tradeCount": 30,
              "maxDrawdownPct": -8.0, "sharpeRatio": 1.0, "profitFactor": 1.5}
        _attach_backtest_execution(run_id, bt, "https://trader.dev/report/fallback")

        r = _find_run(client, run_id)
        assert r["cagr_pct"] is not None
        assert abs(r["cagr_pct"] - 3.8) < 0.1

    def test_multiple_result_types_are_separate_rows(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = _make_confirmed_batch(client, version["id"], profile["id"])

        runs = run_query("SELECT id FROM runs WHERE batch_id = %s", [batch["id"]])
        for run in runs:
            bt = {"netProfitPct": 10.0, "tradeCount": 30, "cagrPct": 2.5,
                  "maxDrawdownPct": -5.0, "sharpeRatio": 0.8, "profitFactor": 1.2}
            _attach_backtest_execution(str(run["id"]), bt, "https://trader.dev/report/x")

        resp = client.get("/results")
        rows = resp.json()
        batch_run_ids = {str(r["id"]) for r in runs}
        batch_rows = [row for row in rows if row["run_id"] in batch_run_ids]
        assert len(batch_rows) == 3
        assert all(r["result_type"] == "standard" for r in batch_rows)
