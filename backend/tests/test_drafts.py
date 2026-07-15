from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db import run_command, run_query, run_query_one


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def _make_source() -> str:
    row = run_command(
        "INSERT INTO sources (content, source_hash, source_type) VALUES (%s, %s, %s) RETURNING id",
        ["Test content", "abc123", "text"],
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


def _make_draft(run_id: str, **overrides) -> dict:
    draft_id = str(uuid4())
    name = overrides.pop("name", "Test Strategy")
    thesis = overrides.pop("thesis", "Test thesis")
    category = overrides.pop("category", "Trendfolge")
    direction = overrides.pop("direction", "kombiniert")
    entry_rule = overrides.pop("entry_rule", "RSI > 30")
    exit_rule = overrides.pop("exit_rule", "RSI < 70")
    warmup = overrides.pop("warmup_requirement", "100 bars")
    status = overrides.pop("status", "Entwurf")
    run_command(
        """INSERT INTO strategy_drafts
           (id, family_id, extraction_run_id, source_hash, version,
            name, thesis, category, direction,
            entry_rule, exit_rule, warmup_requirement,
            simultaneous_entry_exit_behavior, reversal_behavior,
            status, original_snapshot)
           VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        [
            draft_id, draft_id, run_id, "abc123",
            name, thesis, category, direction,
            entry_rule, exit_rule, warmup,
            overrides.get("simultaneous_entry_exit_behavior"),
            overrides.get("reversal_behavior"),
            status,
            '{"name":"KI-Name","thesis":"KI-These","entry_rule":"RSI < 30","exit_rule":"RSI > 70","parameters":[{"name":"period","value":"14"}]}',
        ],
    )
    return {"id": draft_id, "family_id": draft_id, "name": name, "status": status}


def _add_parameter(draft_id: str, name: str, value: str, is_proposal: bool = True) -> None:
    run_command(
        """INSERT INTO draft_parameters (draft_id, name, value, is_proposal)
           VALUES (%s, %s, %s, %s)""",
        [draft_id, name, value, is_proposal],
    )


def _add_open_question(draft_id: str, description: str = "unklar") -> None:
    run_command(
        "INSERT INTO draft_open_questions (draft_id, description, reasoning) VALUES (%s, %s, '')",
        [draft_id, description],
    )


class TestPatchDraft:
    def test_update_name(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)

        resp = client.patch(f"/drafts/{d['id']}", json={"name": "Neuer Name"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Neuer Name"
        assert data["thesis"] == "Test thesis"

    def test_update_parameters_sets_not_proposal(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)
        _add_parameter(d["id"], "period", "14")

        resp = client.patch(
            f"/drafts/{d['id']}",
            json={"parameters": [{"name": "period", "value": "20"}]},
        )
        assert resp.status_code == 200
        params = resp.json()["parameters"]
        assert len(params) == 1
        assert params[0]["value"] == "20"
        assert params[0]["is_proposal"] is False

    def test_cannot_patch_frozen(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, status="freigegeben")

        resp = client.patch(f"/drafts/{d['id']}", json={"name": "x"})
        assert resp.status_code == 422

    def test_404_for_missing_draft(self, client):
        resp = client.patch("/drafts/00000000-0000-0000-0000-000000000000", json={"name": "x"})
        assert resp.status_code == 404

    def test_invalid_category_rejected(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)

        resp = client.patch(f"/drafts/{d['id']}", json={"category": "KeineGültige"})
        assert resp.status_code == 422

    def test_invalid_direction_rejected(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)

        resp = client.patch(f"/drafts/{d['id']}", json={"direction": "only"})
        assert resp.status_code == 422


class TestCloseOpenQuestion:
    def test_delete_open_question(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)
        _add_open_question(d["id"])

        qid = run_query_one(
            "SELECT id FROM draft_open_questions WHERE draft_id = %s", [d["id"]]
        )["id"]

        resp = client.delete(f"/drafts/{d['id']}/open-questions/{qid}")
        assert resp.status_code == 204

        remaining = run_query(
            "SELECT id FROM draft_open_questions WHERE draft_id = %s", [d["id"]]
        )
        assert len(remaining) == 0

    def test_404_wrong_draft(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d1 = _make_draft(run)
        d2 = _make_draft(run)
        _add_open_question(d1["id"])
        qid = run_query_one(
            "SELECT id FROM draft_open_questions WHERE draft_id = %s", [d1["id"]]
        )["id"]

        resp = client.delete(f"/drafts/{d2['id']}/open-questions/{qid}")
        assert resp.status_code == 404


class TestFreeze:
    def test_freeze_creates_version(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, warmup_requirement="0 bars")
        _add_parameter(d["id"], "period", "14")

        resp = client.post(f"/drafts/{d['id']}/freeze")
        assert resp.status_code == 201
        data = resp.json()
        assert data["version_number"] == 1
        assert data["family_id"] == d["family_id"]
        assert data["snapshot"]["name"] == "Test Strategy"
        assert len(data["parameters"]) == 1
        assert len(data["user_diff"]) > 0  # KI said RSI < 30 / RSI > 70, user changed
        assert any(entry["field"] == "entry_rule" for entry in data["user_diff"])

        draft = run_query_one("SELECT status, frozen_at FROM strategy_drafts WHERE id = %s", [d["id"]])
        assert draft["status"] == "freigegeben"
        assert draft["frozen_at"] is not None

    def test_freeze_increments_version_number(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d1 = _make_draft(run, warmup_requirement="0 bars")
        client.post(f"/drafts/{d1['id']}/freeze")

        d2 = _make_draft(run, warmup_requirement="0 bars")
        run_command("UPDATE strategy_drafts SET family_id = %s WHERE id = %s", [d1["family_id"], d2["id"]])

        resp = client.post(f"/drafts/{d2['id']}/freeze")
        assert resp.status_code == 201
        assert resp.json()["version_number"] == 2

    def test_freeze_blocked_by_open_questions(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, warmup_requirement="0 bars")
        _add_open_question(d["id"])

        resp = client.post(f"/drafts/{d['id']}/freeze")
        assert resp.status_code == 422
        assert "Unklarheiten" in resp.json()["detail"]

    def test_freeze_blocked_missing_entry(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, entry_rule=None, warmup_requirement="0 bars")

        resp = client.post(f"/drafts/{d['id']}/freeze")
        assert resp.status_code == 422
        assert "Entry" in resp.json()["detail"]

    def test_freeze_blocked_missing_exit(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, exit_rule=None, warmup_requirement="0 bars")

        resp = client.post(f"/drafts/{d['id']}/freeze")
        assert resp.status_code == 422
        assert "Exit" in resp.json()["detail"]

    def test_freeze_blocked_missing_warmup(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, warmup_requirement=None)

        resp = client.post(f"/drafts/{d['id']}/freeze")
        assert resp.status_code == 422
        assert "Warm-up" in resp.json()["detail"]

    def test_freeze_blocked_not_entwurf(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, status="nicht testbar", warmup_requirement="0 bars")

        resp = client.post(f"/drafts/{d['id']}/freeze")
        assert resp.status_code == 422

    def test_frozen_version_is_appended_not_mutated(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, warmup_requirement="0 bars")
        _add_parameter(d["id"], "period", "14")

        resp = client.post(f"/drafts/{d['id']}/freeze")
        version_id = resp.json()["id"]

        # Verify version row exists and draft status changed
        v = run_query_one("SELECT id, version_number FROM strategy_versions WHERE id = %s", [version_id])
        assert v is not None

        # Verify version parameters exist
        vp = run_query("SELECT name, value FROM version_parameters WHERE version_id = %s", [version_id])
        assert len(vp) == 1
        assert vp[0]["name"] == "period"

        # Second freeze of same draft should fail (already frozen)
        resp2 = client.post(f"/drafts/{d['id']}/freeze")
        assert resp2.status_code == 422


class TestMarkUntestable:
    def test_mark_untestable(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)

        resp = client.post(f"/drafts/{d['id']}/mark-untestable", json={"reason": "Nicht quantifizierbar"})
        assert resp.status_code == 204

        draft = run_query_one("SELECT status, status_reason FROM strategy_drafts WHERE id = %s", [d["id"]])
        assert draft["status"] == "nicht testbar"
        assert draft["status_reason"] == "Nicht quantifizierbar"

    def test_404_missing_draft(self, client):
        resp = client.post(
            "/drafts/00000000-0000-0000-0000-000000000000/mark-untestable",
            json={"reason": "X"},
        )
        assert resp.status_code == 404

    def test_cannot_mark_frozen(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, status="freigegeben")

        resp = client.post(f"/drafts/{d['id']}/mark-untestable", json={"reason": "X"})
        assert resp.status_code == 422


class TestListVersions:
    def test_list_versions(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, warmup_requirement="0 bars")
        client.post(f"/drafts/{d['id']}/freeze")

        resp = client.get(f"/drafts/{d['id']}/versions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["version_number"] == 1
        assert data[0]["draft_id"] == d["id"]

    def test_404_missing_draft(self, client):
        resp = client.get("/drafts/00000000-0000-0000-0000-000000000000/versions")
        assert resp.status_code == 404


class TestGetVersion:
    def test_get_version_with_diff(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, warmup_requirement="0 bars")
        _add_parameter(d["id"], "period", "20", is_proposal=False)
        freeze_resp = client.post(f"/drafts/{d['id']}/freeze")
        version_id = freeze_resp.json()["id"]

        resp = client.get(f"/versions/{version_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == version_id
        assert data["snapshot"]["name"] == "Test Strategy"
        assert len(data["parameters"]) == 1
        assert len(data["user_diff"]) > 0

    def test_404_missing_version(self, client):
        resp = client.get("/versions/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


class TestNewDraftFromVersion:
    def test_new_draft_from_version(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, warmup_requirement="0 bars")
        _add_parameter(d["id"], "period", "14")
        freeze_resp = client.post(f"/drafts/{d['id']}/freeze")
        version_id = freeze_resp.json()["id"]

        resp = client.post(f"/versions/{version_id}/new-draft")
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Strategy"
        assert data["family_id"] == d["family_id"]
        assert data["status"] == "Entwurf"
        assert len(data["parameters"]) == 1

        # Verify parent_version_id is set
        draft = run_query_one(
            "SELECT parent_version_id FROM strategy_drafts WHERE id = %s", [data["id"]]
        )
        assert str(draft["parent_version_id"]) == version_id

    def test_404_missing_version(self, client):
        resp = client.post("/versions/00000000-0000-0000-0000-000000000000/new-draft")
        assert resp.status_code == 404
