from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db import run_command


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
    """Legt Quelle → Extraction-Run → Entwurf an und friert ihn zu einer
    Strategieversion ein, über die echten Endpunkte aus PROJ-2/3."""
    source_id = _make_source()
    run_id = _make_extraction_run(source_id)
    draft_id = str(uuid4())
    run_command(
        """INSERT INTO strategy_drafts
           (id, family_id, extraction_run_id, source_hash, version,
            name, thesis, category, direction,
            entry_rule, exit_rule, warmup_requirement, status)
           VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s)""",
        [
            draft_id, draft_id, run_id, "abc123",
            "Test Strategy", "Test thesis", "Trendfolge", "kombiniert",
            "RSI > 30", "RSI < 70", "100 bars", "Entwurf",
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


class TestListAllVersions:
    def test_lists_versions_across_families(self, client):
        v1 = _make_frozen_version(client)
        v2 = _make_frozen_version(client)
        resp = client.get("/versions")
        assert resp.status_code == 200, resp.text
        ids = {v["id"] for v in resp.json()}
        assert {v1["id"], v2["id"]} <= ids


class TestBacktestProfiles:
    def test_create_defaults(self, client):
        profile = _make_profile(client)
        assert profile["version_number"] == 1
        assert profile["fee_pct"] == 0.06
        assert profile["slippage_ticks"] == 2
        assert profile["starting_capital"] == 10000
        assert profile["max_open_positions"] == 1

    def test_edit_creates_new_version_not_overwrite(self, client):
        profile = _make_profile(client)
        body = {**_PROFILE_BODY, "name": "Geändert"}
        resp = client.patch(f"/backtest-profiles/{profile['family_id']}", json=body)
        assert resp.status_code == 200, resp.text
        new_version = resp.json()
        assert new_version["version_number"] == 2
        assert new_version["id"] != profile["id"]

        versions = client.get(f"/backtest-profiles/{profile['family_id']}/versions").json()
        assert [v["version_number"] for v in versions] == [1, 2]
        assert versions[0]["name"] == "Standard"

    def test_list_returns_latest_version_per_family(self, client):
        profile = _make_profile(client)
        client.patch(f"/backtest-profiles/{profile['family_id']}", json={**_PROFILE_BODY, "name": "v2"})
        listed = client.get("/backtest-profiles").json()
        assert len(listed) == 1
        assert listed[0]["version_number"] == 2

    def test_get_single_version_by_own_id_returns_superseded_version(self, client):
        profile = _make_profile(client)
        client.patch(f"/backtest-profiles/{profile['family_id']}", json={**_PROFILE_BODY, "name": "v2"})
        resp = client.get(f"/backtest-profiles/versions/{profile['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["version_number"] == 1

    def test_get_single_version_unknown_id_404(self, client):
        resp = client.get(f"/backtest-profiles/versions/{uuid4()}")
        assert resp.status_code == 404


class TestBatchCreateAndPreview:
    def test_create_with_defaults(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        resp = client.post(
            "/batches",
            json={
                "backtest_profile_id": profile["id"],
                "strategy_version_ids": [version["id"]],
            },
        )
        assert resp.status_code == 201, resp.text
        batch = resp.json()
        assert batch["status"] == "entwurf"
        assert batch["timeframe"] == "4h"
        assert batch["period_start"] == "2021-01-01"
        assert batch["period_end"] == "2024-12-31"
        assert len(batch["instruments"]) == 3
        assert batch["direction_modes"] == ["kombiniert"]

    def test_preview_is_cartesian_product(self, client):
        profile = _make_profile(client)
        v1 = _make_frozen_version(client)
        v2 = _make_frozen_version(client)
        resp = client.post(
            "/batches",
            json={
                "backtest_profile_id": profile["id"],
                "strategy_version_ids": [v1["id"], v2["id"]],
                "direction_modes": ["kombiniert", "long-only"],
            },
        )
        batch = resp.json()
        preview = client.get(f"/batches/{batch['id']}/preview").json()
        # 2 Strategieversionen x 3 Instrumente (Default) x 2 Richtungsmodi
        assert len(preview) == 12

    def test_unknown_strategy_version_rejected(self, client):
        profile = _make_profile(client)
        resp = client.post(
            "/batches",
            json={"backtest_profile_id": profile["id"], "strategy_version_ids": [str(uuid4())]},
        )
        assert resp.status_code == 422

    def test_explicit_empty_instruments_and_modes_not_replaced_with_defaults(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        resp = client.post(
            "/batches",
            json={
                "backtest_profile_id": profile["id"],
                "strategy_version_ids": [version["id"]],
                "instruments": [],
                "direction_modes": [],
            },
        )
        assert resp.status_code == 201, resp.text
        batch = resp.json()
        assert batch["instruments"] == []
        assert batch["direction_modes"] == []

    def test_standard_batch_period_end_beyond_default_rejected(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        resp = client.post(
            "/batches",
            json={
                "backtest_profile_id": profile["id"],
                "strategy_version_ids": [version["id"]],
                "period_end": "2025-06-01",
            },
        )
        assert resp.status_code == 422

    def test_standard_batch_period_end_beyond_default_rejected_on_patch(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = client.post(
            "/batches",
            json={"backtest_profile_id": profile["id"], "strategy_version_ids": [version["id"]]},
        ).json()
        resp = client.patch(f"/batches/{batch['id']}", json={"period_end": "2025-06-01"})
        assert resp.status_code == 422


class TestBatchConfirm:
    def test_confirm_materializes_runs(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = client.post(
            "/batches",
            json={"backtest_profile_id": profile["id"], "strategy_version_ids": [version["id"]]},
        ).json()

        resp = client.post(f"/batches/{batch['id']}/confirm")
        assert resp.status_code == 201, resp.text
        confirmed = resp.json()
        assert confirmed["status"] == "bestätigt"
        assert confirmed["confirmed_at"] is not None

        preview = client.get(f"/batches/{batch['id']}/preview").json()
        from app.db import run_query
        rows = run_query("SELECT status, run_kind FROM runs WHERE batch_id = %s", [batch["id"]])
        assert len(rows) == len(preview) == 3
        assert all(r["status"] == "geplant" and r["run_kind"] == "standard" for r in rows)

    def test_confirmed_batch_cannot_be_edited(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        batch = client.post(
            "/batches",
            json={"backtest_profile_id": profile["id"], "strategy_version_ids": [version["id"]]},
        ).json()
        client.post(f"/batches/{batch['id']}/confirm")

        resp = client.patch(f"/batches/{batch['id']}", json={"timeframe": "1h"})
        assert resp.status_code == 422

        resp2 = client.post(f"/batches/{batch['id']}/confirm")
        assert resp2.status_code == 422


class TestHoldoutForwardTest:
    def test_holdout_blocked_gate_uses_freeze(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        resp = client.post(
            f"/strategy-versions/{version['id']}/holdout-batch",
            json={"backtest_profile_id": profile["id"]},
        )
        assert resp.status_code == 201, resp.text
        batch = resp.json()
        assert batch["run_kind"] == "holdout"
        assert batch["period_start"] == "2025-01-01"

    def test_holdout_second_attempt_blocked_as_consumed(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        client.post(
            f"/strategy-versions/{version['id']}/holdout-batch",
            json={"backtest_profile_id": profile["id"]},
        )
        resp = client.post(
            f"/strategy-versions/{version['id']}/holdout-batch",
            json={"backtest_profile_id": profile["id"]},
        )
        assert resp.status_code == 422

        status = client.get(f"/strategy-versions/{version['id']}/holdout-status").json()
        assert status["consumed"] is True

    def test_forward_test_open_ended(self, client):
        profile = _make_profile(client)
        version = _make_frozen_version(client)
        resp = client.post(
            f"/strategy-versions/{version['id']}/forward-test-batch",
            json={"backtest_profile_id": profile["id"]},
        )
        assert resp.status_code == 201, resp.text
        batch = resp.json()
        assert batch["run_kind"] == "forward_test"
        assert batch["period_end"] is None

    def test_holdout_unknown_version_404(self, client):
        profile = _make_profile(client)
        resp = client.post(
            f"/strategy-versions/{uuid4()}/holdout-batch",
            json={"backtest_profile_id": profile["id"]},
        )
        assert resp.status_code == 404
