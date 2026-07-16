"""PROJ-12: Execution-Routes + Worker-Availability — Backend-Tests."""
from unittest.mock import patch
from uuid import uuid4

import pytest


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _make_confirmed_batch(client):
    """Helper: creates source → draft → freeze → profile → batch → confirm."""
    from app.db import run_command
    source_id = str(run_command(
        "INSERT INTO sources (content, source_hash, source_type) VALUES (%s, %s, %s) RETURNING id",
        ["Test content", str(uuid4()), "text"],
        returning=True,
    )["id"])
    run_id = str(run_command(
        """INSERT INTO extraction_runs (source_id, status, model, prompt_version)
           VALUES (%s, 'abgeschlossen', 'gpt-4', 'v1') RETURNING id""",
        [source_id],
        returning=True,
    )["id"])
    draft_id = str(uuid4())
    run_command(
        """INSERT INTO strategy_drafts
           (id, family_id, extraction_run_id, source_hash, version,
            name, thesis, category, direction,
            entry_rule, exit_rule, warmup_requirement, status,
            position_mode, position_mode_confirmed,
            mts_compatibility, mts_confirmed)
           VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        [draft_id, draft_id, run_id, "abc123", "Test", "t", "Trendfolge", "kombiniert",
         "RSI > 30", "RSI < 70", "100 bars", "Entwurf", "entry_exit", True, "discrete", True],
    )
    resp = client.post(f"/drafts/{draft_id}/freeze")
    assert resp.status_code == 201, resp.text
    version = resp.json()

    resp = client.post("/backtest-profiles", json={
        "name": "Standard", "timezone_session": "Exchange",
        "order_type": "Market", "position_sizing": "Fix 100%",
        "compounding_rule": "Kein Compounding", "missing_bars_handling": "Bar überspringen",
        "corporate_actions_handling": "Ignorieren",
    })
    assert resp.status_code == 201, resp.text
    profile = resp.json()

    resp = client.post("/batches", json={
        "backtest_profile_id": profile["id"],
        "strategy_version_ids": [version["id"]],
    })
    batch = resp.json()
    with patch("app.routes.batches.get_credits") as mock:
        mock.return_value = {"balance": 1000, "tier": "free", "reset": "2026-07-22", "weekly_free": 1000}
        resp = client.post(f"/batches/{batch['id']}/confirm", json={"credit_max": 3})
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestExecutionAvailability:
    def test_worker_available_with_recent_heartbeat(self, client):
        resp = client.get("/execution/availability")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["available"] is True
        assert data["worker_id"] == "strategy-bank-worker-v1"

    def test_worker_unavailable_with_stale_heartbeat(self, client):
        from app.db import run_command
        run_command(
            "UPDATE worker_heartbeat SET last_heartbeat = '2000-01-01'::timestamptz"
            " WHERE worker_id = 'strategy-bank-worker-v1'"
        )
        resp = client.get("/execution/availability")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["available"] is False
        assert data["worker_id"] == "strategy-bank-worker-v1"

    def test_worker_unavailable_when_no_heartbeat_row(self, client):
        from app.db import run_command
        run_command("TRUNCATE worker_heartbeat")
        resp = client.get("/execution/availability")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["available"] is False


class TestStartBatchWithWorkerCheck:
    def test_start_batch_fails_when_worker_unavailable(self, client):
        from app.db import run_command
        run_command(
            "UPDATE worker_heartbeat SET last_heartbeat = '2000-01-01'::timestamptz"
            " WHERE worker_id = 'strategy-bank-worker-v1'"
        )
        batch = _make_confirmed_batch(client)
        resp = client.post(f"/batches/{batch['id']}/start")
        assert resp.status_code == 503, resp.text
        assert "nicht verfügbar" in resp.json()["detail"].lower()

    def test_start_batch_succeeds_when_worker_available(self, client):
        batch = _make_confirmed_batch(client)
        resp = client.post(f"/batches/{batch['id']}/start")
        assert resp.status_code == 200, resp.text

    def test_start_batch_double_start_graceful(self, client):
        batch = _make_confirmed_batch(client)
        r1 = client.post(f"/batches/{batch['id']}/start")
        assert r1.status_code == 200
        r2 = client.post(f"/batches/{batch['id']}/start")
        assert r2.status_code == 422  # batch nicht mehr im Status 'bestätigt'
        assert "bestätigt" in r2.json()["detail"].lower()
        from app.db import run_query
        runs = run_query("SELECT status FROM runs WHERE batch_id = %s", [batch["id"]])
        assert all(r["status"] == "bestätigt" for r in runs)


class TestExecutionRouteSecurity:
    def test_availability_no_internal_details_leaked(self, client):
        resp = client.get("/execution/availability")
        data = resp.json()
        assert "database_url" not in data
        assert "opencode_binary" not in data
        assert "password" not in data
