from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db import run_command, run_query


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


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


def _make_frozen_version(client: TestClient) -> dict:
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


_PROFILE_BODY = {
    "name": "Standard",
    "timezone_session": "Exchange",
    "order_type": "Market",
    "position_sizing": "Fix 100%",
    "compounding_rule": "Kein Compounding",
    "missing_bars_handling": "Bar überspringen",
    "corporate_actions_handling": "Ignorieren",
}


def _make_profile(client: TestClient) -> dict:
    resp = client.post("/backtest-profiles", json=_PROFILE_BODY)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _confirm_batch_and_get_run_ids(client: TestClient) -> list[str]:
    profile = _make_profile(client)
    version = _make_frozen_version(client)
    batch = client.post(
        "/batches",
        json={
            "backtest_profile_id": profile["id"],
            "strategy_version_ids": [version["id"]],
            "instruments": [{"provider_symbol": "BYBIT:BTCUSDT.P", "label": "BTC"}],
            "direction_modes": ["kombiniert"],
        },
    ).json()

    with patch("app.routes.batches.get_credits") as mock_credits:
        mock_credits.return_value = {
            "balance": 1000, "tier": "free", "reset": "2026-07-22", "weekly_free": 1000,
        }
        client.post(f"/batches/{batch['id']}/confirm", json={"credit_max": 1})

    rows = run_query("SELECT id FROM runs WHERE batch_id = %s", [batch["id"]])
    return [r["id"] for r in rows]


class TestAuditTrail:
    def test_get_audit_after_confirm(self, client):
        run_ids = _confirm_batch_and_get_run_ids(client)
        assert len(run_ids) == 1
        resp = client.get(f"/runs/{run_ids[0]}/audit")
        assert resp.status_code == 200, resp.text
        audit = resp.json()
        assert audit["run_id"] == str(run_ids[0])
        assert "strategy_snapshot" in audit
        assert "profile_snapshot" in audit
        assert audit["provider_symbol"] == "BYBIT:BTCUSDT.P"
        assert audit["direction_mode"] == "kombiniert"
        assert audit["run_kind"] == "standard"
        assert audit["timeframe"] == "4h"
        assert audit["period_start"] == "2021-01-01"
        assert audit["period_end"] == "2024-12-31"
        assert audit["credit_max"] == 1
        assert audit["credit_balance"] is None
        assert audit["credit_remaining"] is None
        assert audit["credit_tier"] is None
        assert audit["report_available"] is False
        assert audit["raw_response_available"] is False
        assert audit["report_link"] is None
        assert audit["raw_response"] is None
        assert audit["finalized_at"] is None
        assert audit["created_at"] is not None

    def test_audit_strategy_snapshot_includes_parameters(self, client):
        run_ids = _confirm_batch_and_get_run_ids(client)
        resp = client.get(f"/runs/{run_ids[0]}/audit")
        ss = resp.json()["strategy_snapshot"]
        assert "version" in ss
        assert "parameters" in ss
        assert isinstance(ss["parameters"], list)
        assert ss["version"]["snapshot"]["name"] == "Test Strategy"
        assert ss["version"]["snapshot"]["direction"] == "kombiniert"
        assert ss["version"]["snapshot"]["position_mode"] == "entry_exit"
        assert ss["version"]["snapshot"]["mts_compatibility"] == "discrete"

    def test_audit_profile_snapshot_has_backtest_config(self, client):
        run_ids = _confirm_batch_and_get_run_ids(client)
        resp = client.get(f"/runs/{run_ids[0]}/audit")
        ps = resp.json()["profile_snapshot"]
        assert ps["name"] == "Standard"
        assert ps["fee_pct"] == "0.06"
        assert ps["starting_capital"] == "10000"

    def test_nonexistent_run_audit_returns_404(self, client):
        resp = client.get(f"/runs/{uuid4()}/audit")
        assert resp.status_code == 404

    def test_invalid_uuid_audit_returns_404(self, client):
        resp = client.get("/runs/not-a-uuid/audit")
        assert resp.status_code == 404

    def test_multiple_runs_each_have_own_audit(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = client.post(
            "/batches",
            json={
                "backtest_profile_id": profile["id"],
                "strategy_version_ids": [version["id"]],
                "direction_modes": ["kombiniert", "long-only"],
                "instruments": [{"provider_symbol": "BYBIT:BTCUSDT.P", "label": "BTC"}],
            },
        ).json()

        with patch("app.routes.batches.get_credits") as mock_credits:
            mock_credits.return_value = {
                "balance": 1000, "tier": "free", "reset": "2026-07-22", "weekly_free": 1000,
            }
            client.post(f"/batches/{batch['id']}/confirm", json={"credit_max": 2})

        rows = run_query("SELECT id FROM runs WHERE batch_id = %s ORDER BY direction_mode", [batch["id"]])
        assert len(rows) == 2

        a1 = client.get(f"/runs/{rows[0]['id']}/audit").json()
        a2 = client.get(f"/runs/{rows[1]['id']}/audit").json()
        assert a1["id"] != a2["id"]
        assert a1["run_id"] != a2["run_id"]
        assert a1["direction_mode"] == "kombiniert"
        assert a2["direction_mode"] == "long-only"
        assert a1["strategy_snapshot"] == a2["strategy_snapshot"]
        assert a1["profile_snapshot"] == a2["profile_snapshot"]
        assert a1["batch_id"] == a2["batch_id"]

    def test_holdout_audit_has_correct_period(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = client.post(
            f"/strategy-versions/{version['id']}/holdout-batch",
            json={"backtest_profile_id": profile["id"]},
        ).json()

        with patch("app.routes.batches.get_credits") as mock_credits:
            mock_credits.return_value = {
                "balance": 1000, "tier": "free", "reset": "2026-07-22", "weekly_free": 1000,
            }
            client.post(f"/batches/{batch['id']}/confirm", json={"credit_max": 3})

        rows = run_query("SELECT id FROM runs WHERE batch_id = %s", [batch["id"]])
        audit = client.get(f"/runs/{rows[0]['id']}/audit").json()
        assert audit["run_kind"] == "holdout"
        assert audit["period_start"] == "2025-01-01"
        assert audit["period_end"] is not None  # frozen_at date

    def test_forward_test_audit_has_open_ended_period(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = client.post(
            f"/strategy-versions/{version['id']}/forward-test-batch",
            json={"backtest_profile_id": profile["id"]},
        ).json()

        with patch("app.routes.batches.get_credits") as mock_credits:
            mock_credits.return_value = {
                "balance": 1000, "tier": "free", "reset": "2026-07-22", "weekly_free": 1000,
            }
            client.post(f"/batches/{batch['id']}/confirm", json={"credit_max": 3})

        rows = run_query("SELECT id FROM runs WHERE batch_id = %s", [batch["id"]])
        audit = client.get(f"/runs/{rows[0]['id']}/audit").json()
        assert audit["run_kind"] == "forward_test"
        assert audit["period_end"] is None
