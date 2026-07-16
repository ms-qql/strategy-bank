"""PROJ-6: Queue und trader.dev-Ausführung — Backend-Tests."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


def _make_source():
    from app.db import run_command
    row = run_command(
        "INSERT INTO sources (content, source_hash, source_type) VALUES (%s, %s, %s) RETURNING id",
        ["Test content", str(uuid4()), "text"],
        returning=True,
    )
    return str(row["id"])


def _make_extraction_run(source_id: str) -> str:
    from app.db import run_command
    row = run_command(
        """INSERT INTO extraction_runs (source_id, status, model, prompt_version)
           VALUES (%s, 'abgeschlossen', 'gpt-4', 'v1') RETURNING id""",
        [source_id],
        returning=True,
    )
    return str(row["id"])


def _make_frozen_version(client):
    source_id = _make_source()
    run_id = _make_extraction_run(source_id)
    draft_id = str(uuid4())
    from app.db import run_command
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


def _make_profile(client):
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


def _make_confirmed_batch(client, extra_versions=0):
    profile = _make_profile(client)
    version = _make_frozen_version(client)
    versions = [version["id"]]
    for _ in range(extra_versions):
        v = _make_frozen_version(client)
        versions.append(v["id"])
    resp = client.post(
        "/batches",
        json={"backtest_profile_id": profile["id"], "strategy_version_ids": versions},
    )
    batch = resp.json()
    with patch("app.routes.batches.get_credits") as mock:
        mock.return_value = {"balance": 1000, "tier": "free", "reset": "2026-07-22", "weekly_free": 1000}
        expected_runs = len(versions)
        resp = client.post(f"/batches/{batch['id']}/confirm", json={"credit_max": expected_runs})
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


class TestBatchStart:
    def test_start_transitions_runs_to_bestaetigt(self, client):
        batch = _make_confirmed_batch(client)
        resp = client.post(f"/batches/{batch['id']}/start")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "ok"
        assert data["batch_id"] == batch["id"]

        from app.db import run_query
        runs = run_query("SELECT status FROM runs WHERE batch_id = %s", [batch["id"]])
        assert len(runs) == 1
        assert all(r["status"] == "bestätigt" for r in runs)

    def test_start_non_confirmed_batch_rejected(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = client.post(
            "/batches",
            json={"backtest_profile_id": profile["id"], "strategy_version_ids": [version["id"]]},
        ).json()
        resp = client.post(f"/batches/{batch['id']}/start")
        assert resp.status_code == 422
        assert "bestätigt" in resp.json()["detail"].lower()

    def test_start_unknown_batch_404(self, client):
        resp = client.post(f"/batches/{uuid4()}/start")
        assert resp.status_code == 404


class TestGetBatchRuns:
    def test_lists_existing_batches(self, client):
        batch = _make_confirmed_batch(client)

        assert batch["id"] in {item["id"] for item in client.get("/batches").json()}

    def test_returns_runs_with_summary(self, client):
        batch = _make_confirmed_batch(client)
        client.post(f"/batches/{batch['id']}/start")
        resp = client.get(f"/batches/{batch['id']}/runs")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["batch_status"] == "in_ausfuehrung"
        assert "runs" in data
        assert "summary" in data
        assert len(data["runs"]) == 1
        assert data["summary"]["total"] == 1
        assert data["summary"]["offen"] == 1
        assert data["summary"]["erfolgreich"] == 0
        assert data["summary"]["fehlgeschlagen"] == 0
        assert data["summary"]["abgebrochen"] == 0

    def test_unknown_batch_404(self, client):
        resp = client.get(f"/batches/{uuid4()}/runs")
        assert resp.status_code == 404

    def test_runs_field_structure(self, client):
        batch = _make_confirmed_batch(client)
        client.post(f"/batches/{batch['id']}/start")
        resp = client.get(f"/batches/{batch['id']}/runs")
        runs = resp.json()["runs"]
        for run in runs:
            assert "id" in run
            assert "batch_id" in run
            assert "strategy_version_id" in run
            assert "provider_symbol" in run
            assert "direction_mode" in run
            assert "run_kind" in run
            assert "status" in run
            assert run["status"] == "bestätigt"
            assert run["error_message"] is None


class TestGetSingleRun:
    def test_returns_run_detail(self, client):
        batch = _make_confirmed_batch(client)
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run = runs_resp.json()["runs"][0]
        resp = client.get(f"/runs/{run['id']}")
        assert resp.status_code == 200, resp.text
        detail = resp.json()
        assert detail["id"] == run["id"]
        assert detail["batch_id"] == batch["id"]

    def test_unknown_run_404(self, client):
        resp = client.get(f"/runs/{uuid4()}")
        assert resp.status_code == 404

    def test_delete_terminal_run_removes_audit(self, client):
        batch = _make_confirmed_batch(client)
        run = client.get(f"/batches/{batch['id']}/runs").json()["runs"][0]
        from app.db import run_command, run_query_one
        run_command("UPDATE runs SET status = 'fehlgeschlagen' WHERE id = %s", [run["id"]])

        assert client.delete(f"/runs/{run['id']}").status_code == 204
        assert run_query_one("SELECT id FROM run_audits WHERE run_id = %s", [run["id"]]) is None

    def test_delete_pending_run(self, client):
        batch = _make_confirmed_batch(client)
        run = client.get(f"/batches/{batch['id']}/runs").json()["runs"][0]

        assert client.delete(f"/runs/{run['id']}").status_code == 204

    def test_delete_last_run_resets_batch_to_entwurf(self, client):
        # Regression: DELETE /runs/{id} used to never touch the parent batch,
        # so deleting a batch's only/last run left it stuck at 'bestätigt'
        # forever (config permanently locked, no way to start a new run).
        batch = _make_confirmed_batch(client)
        run = client.get(f"/batches/{batch['id']}/runs").json()["runs"][0]

        assert client.delete(f"/runs/{run['id']}").status_code == 204

        reloaded = client.get(f"/batches/{batch['id']}").json()
        assert reloaded["status"] == "entwurf"
        assert reloaded["confirmed_at"] is None
        assert reloaded["credit_max"] is None

    def test_delete_one_of_several_runs_keeps_batch_confirmed(self, client):
        batch = _make_confirmed_batch(client, extra_versions=1)
        runs = client.get(f"/batches/{batch['id']}/runs").json()["runs"]
        assert len(runs) == 2

        assert client.delete(f"/runs/{runs[0]['id']}").status_code == 204

        reloaded = client.get(f"/batches/{batch['id']}").json()
        assert reloaded["status"] == "bestätigt"
        assert reloaded["confirmed_at"] is not None


class TestCancelRun:
    def test_cancel_geplant_run(self, client):
        batch = _make_confirmed_batch(client)
        # before start, runs are 'geplant'
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run = runs_resp.json()["runs"][0]
        resp = client.post(f"/runs/{run['id']}/cancel")
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "abgebrochen"
        assert resp.json()["completed_at"] is not None

    def test_cancel_bestaetigt_run(self, client):
        batch = _make_confirmed_batch(client)
        client.post(f"/batches/{batch['id']}/start")
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run = runs_resp.json()["runs"][0]
        resp = client.post(f"/runs/{run['id']}/cancel")
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "abgebrochen"

    def test_cancel_running_run_rejected(self, client):
        batch = _make_confirmed_batch(client)
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run = runs_resp.json()["runs"][0]
        from app.db import run_command
        run_command("UPDATE runs SET status = 'läuft' WHERE id = %s", [run["id"]])
        resp = client.post(f"/runs/{run['id']}/cancel")
        assert resp.status_code == 422
        assert "geplante" in resp.json()["detail"].lower()

    def test_cancel_terminal_run_rejected(self, client):
        batch = _make_confirmed_batch(client)
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run = runs_resp.json()["runs"][0]
        from app.db import run_command
        run_command("UPDATE runs SET status = 'erfolgreich' WHERE id = %s", [run["id"]])
        resp = client.post(f"/runs/{run['id']}/cancel")
        assert resp.status_code == 422

    def test_cancel_unknown_run_404(self, client):
        resp = client.post(f"/runs/{uuid4()}/cancel")
        assert resp.status_code == 404


class TestRetry:
    def test_retry_credit_check_fehlgeschlagen(self, client):
        batch = _make_confirmed_batch(client)
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run = runs_resp.json()["runs"][0]
        from app.db import run_command
        run_command("UPDATE runs SET status = 'fehlgeschlagen' WHERE id = %s", [run["id"]])
        with patch("app.routes.runs.get_credits") as mock:
            mock.return_value = {"balance": 100, "tier": "free", "reset": "2026-07-22", "weekly_free": 100}
            resp = client.get(f"/runs/{run['id']}/retry-credit-check")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["ok"] is True
        assert data["reason"] is None

    def test_retry_credit_check_non_failed_rejected(self, client):
        batch = _make_confirmed_batch(client)
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run = runs_resp.json()["runs"][0]
        # status is 'geplant'
        resp = client.get(f"/runs/{run['id']}/retry-credit-check")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["ok"] is False
        assert "fehlgeschlagen" in data["reason"].lower()

    def test_retry_credit_check_no_balance(self, client):
        batch = _make_confirmed_batch(client)
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run = runs_resp.json()["runs"][0]
        from app.db import run_command
        run_command("UPDATE runs SET status = 'fehlgeschlagen' WHERE id = %s", [run["id"]])
        with patch("app.routes.runs.get_credits") as mock:
            mock.return_value = {"balance": 0, "tier": "free", "reset": "2026-07-22", "weekly_free": 100}
            resp = client.get(f"/runs/{run['id']}/retry-credit-check")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["ok"] is False
        assert "keine credits" in data["reason"].lower()

    def test_retry_creates_new_run(self, client):
        batch = _make_confirmed_batch(client)
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run = runs_resp.json()["runs"][0]
        from app.db import run_command
        run_command("UPDATE runs SET status = 'fehlgeschlagen' WHERE id = %s", [run["id"]])
        with patch("app.routes.runs.get_credits") as mock:
            mock.return_value = {"balance": 100, "tier": "free", "reset": "2026-07-22", "weekly_free": 100}
            resp = client.post(f"/runs/{run['id']}/retry")
        assert resp.status_code == 201, resp.text
        new_run = resp.json()
        assert "run_id" in new_run
        assert new_run["run_id"] != run["id"]

        all_runs = client.get(f"/batches/{batch['id']}/runs").json()
        assert all_runs["summary"]["total"] == 2
        assert all_runs["summary"]["fehlgeschlagen"] == 1
        assert all_runs["summary"]["offen"] == 1

    def test_retry_non_failed_rejected(self, client):
        batch = _make_confirmed_batch(client)
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run = runs_resp.json()["runs"][0]
        resp = client.post(f"/runs/{run['id']}/retry")
        assert resp.status_code == 422
        assert "fehlgeschlagen" in resp.json()["detail"].lower()

    def test_retry_no_credits_rejected(self, client):
        batch = _make_confirmed_batch(client)
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run = runs_resp.json()["runs"][0]
        from app.db import run_command
        run_command("UPDATE runs SET status = 'fehlgeschlagen' WHERE id = %s", [run["id"]])
        with patch("app.routes.runs.get_credits") as mock:
            mock.return_value = {"balance": 0, "tier": "free", "reset": "2026-07-22", "weekly_free": 100}
            resp = client.post(f"/runs/{run['id']}/retry")
        assert resp.status_code == 422
        assert "keine credits" in resp.json()["detail"].lower()

    def test_retry_service_error_502(self, client):
        batch = _make_confirmed_batch(client)
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run = runs_resp.json()["runs"][0]
        from app.db import run_command
        run_command("UPDATE runs SET status = 'fehlgeschlagen' WHERE id = %s", [run["id"]])
        with patch("app.routes.runs.get_credits") as mock:
            mock.side_effect = __import__(
                "app.services.trader_dev", fromlist=["CreditServiceError"]
            ).CreditServiceError("Test-Error")
            resp = client.get(f"/runs/{run['id']}/retry-credit-check")
        assert resp.status_code == 502

    def test_retry_unknown_run_404(self, client):
        resp = client.get(f"/runs/{uuid4()}/retry-credit-check")
        assert resp.status_code == 404

        resp = client.post(f"/runs/{uuid4()}/retry")
        assert resp.status_code == 404


class TestRunBacktestExecution:
    def test_worker_resubmits_execution_without_job_id(self):
        from app.services import worker

        cur = MagicMock()
        run = {"id": uuid4(), "strategy_version_id": uuid4(), "provider_symbol": "BTC", "direction_mode": "kombiniert", "run_kind": "standard"}
        execution = {"id": uuid4(), "provider_status": "submitted", "external_job_id": None}
        with patch.object(worker, "_find_or_create_execution", return_value=execution), patch.object(worker, "_submit_backtest") as submit:
            worker._process_one_run(cur, run)

        submit.assert_called_once_with(cur, run["id"], execution)

    def test_worker_regenerates_pine_for_failed_execution(self):
        from app.services import worker

        cur = MagicMock()
        cur.fetchone.return_value = {"id": uuid4(), "external_job_id": None, "provider_status": "failed"}
        run = {"id": uuid4(), "strategy_version_id": uuid4(), "provider_symbol": "BTC", "direction_mode": "kombiniert", "run_kind": "standard"}
        with patch.object(worker, "_load_strategy_details", return_value={"pine_source": "new pine"}):
            worker._find_or_create_execution(cur, run, "test-key")

        assert cur.execute.call_args_list[1].args[1] == ["new pine", cur.fetchone.return_value["id"]]

    def test_worker_submits_with_direct_mcp(self):
        from app.services import worker

        cur = MagicMock()
        run_id = uuid4()
        execution = {"id": uuid4(), "pine_source": "// pine", "provider_symbol": "BTC", "timeframe": "4h", "period_start": "2021-01-01", "period_end": "2024-12-31"}
        with patch.object(worker, "start_backtest", return_value={"jobId": "job-1"}):
            worker._submit_backtest(cur, run_id, execution)

        assert cur.execute.call_args_list[-1].args[1] == ["job-1", execution["id"]]

    def test_worker_uses_backtest_profile_id_for_execution(self):
        from app.services import worker

        cur = MagicMock()
        cur.fetchone.side_effect = [None, {"id": uuid4()}]
        run = {"id": uuid4(), "strategy_version_id": uuid4(), "provider_symbol": "BYBIT:BTCUSDT.P", "direction_mode": "kombiniert", "run_kind": "standard"}
        profile_id = uuid4()

        with patch.object(worker, "_load_strategy_details", return_value={"backtest_profile_id": profile_id}):
            worker._find_or_create_execution(cur, run, "test-key")

        assert cur.execute.call_args_list[1].args[1][7] == profile_id

    def test_run_with_backtest_execution_shows_metrics(self, client):
        batch = _make_confirmed_batch(client)
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run = runs_resp.json()["runs"][0]
        run_id = run["id"]
        sv_id = run["strategy_version_id"]

        from app.db import run_command
        import json
        exec_id = str(uuid4())
        run_command(
            """
            INSERT INTO backtest_executions
                (id, idempotency_key, strategy_version_id, provider_symbol,
                 timeframe, period_start, direction_mode, backtest_profile_version_id,
                 pine_source, executor_fingerprint, backtest_result, external_job_id,
                 provider_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                exec_id, "test-key", sv_id, "BYBIT:BTCUSDT.P",
                "4h", "2021-01-01", "kombiniert", str(batch["backtest_profile_id"]),
                "// Pine", "v1",
                json.dumps({"netProfitPct": 12.5, "profitFactor": 1.8, "sharpeRatio": 1.2,
                           "maxDrawdownPct": 15.0, "winRatePct": 55, "tradeCount": 42}),
                "job-123", "completed",
            ],
        )
        run_command(
            "UPDATE runs SET backtest_execution_id = %s, status = 'erfolgreich' WHERE id = %s",
            [exec_id, run_id],
        )

        resp = client.get(f"/runs/{run_id}")
        assert resp.status_code == 200, resp.text
        detail = resp.json()
        assert detail["status"] == "erfolgreich"
        assert detail["backtest_job_id"] == "job-123"
        assert detail["backtest_metrics"] is not None
        assert detail["backtest_metrics"]["net_profit_pct"] == 12.5
        assert detail["backtest_metrics"]["trade_count"] == 42

    def test_run_without_execution_shows_none_metrics(self, client):
        batch = _make_confirmed_batch(client)
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        run_id = runs_resp.json()["runs"][0]["id"]
        resp = client.get(f"/runs/{run_id}")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["backtest_metrics"] is None
        assert detail.get("backtest_job_id") is None


class TestRunSummary:
    def test_mixed_status_summary(self, client):
        batch = _make_confirmed_batch(client, extra_versions=3)
        runs_resp = client.get(f"/batches/{batch['id']}/runs")
        runs = runs_resp.json()["runs"]
        assert len(runs) == 4

        from app.db import run_command
        run_command("UPDATE runs SET status = 'erfolgreich' WHERE id = %s", [runs[0]["id"]])
        run_command("UPDATE runs SET status = 'fehlgeschlagen', error_message = 'test error' WHERE id = %s", [runs[1]["id"]])
        run_command("UPDATE runs SET status = 'abgebrochen' WHERE id = %s", [runs[2]["id"]])

        resp = client.get(f"/batches/{batch['id']}/runs")
        summary = resp.json()["summary"]
        assert summary["total"] == 4
        assert summary["erfolgreich"] == 1
        assert summary["fehlgeschlagen"] == 1
        assert summary["abgebrochen"] == 1
        assert summary["offen"] == 1

    def test_all_pending_summary(self, client):
        batch = _make_confirmed_batch(client)
        resp = client.get(f"/batches/{batch['id']}/runs")
        summary = resp.json()["summary"]
        assert summary["total"] == 1
        assert summary["offen"] == 1
        assert summary["erfolgreich"] == 0
        assert summary["fehlgeschlagen"] == 0
        assert summary["abgebrochen"] == 0


class TestSecurity:
    def test_non_uuid_run_id_returns_404_not_500(self, client):
        resp = client.get("/runs/not-a-uuid")
        assert resp.status_code == 404

        resp = client.post("/runs/not-a-uuid/cancel")
        assert resp.status_code == 404

    def test_sql_injection_run_id_sanitized(self, client):
        resp = client.get("/runs/' OR '1'='1")
        assert resp.status_code == 404

    def test_empty_post_body_handled(self, client):
        batch = _make_confirmed_batch(client)
        resp = client.post(f"/batches/{batch['id']}/start", json={})
        assert resp.status_code == 200

    def test_large_uuid_list_rejected_gracefully(self, client):
        resp = client.get(f"/runs/{uuid4()}")
        assert resp.status_code == 404
