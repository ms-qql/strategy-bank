from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db import run_command
from app.services.hal_sync import HAL_QUELLEN_DIR


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


def _make_run(source_id: str) -> str:
    row = run_command(
        """INSERT INTO extraction_runs (source_id, status, model, prompt_version)
           VALUES (%s, 'abgeschlossen', 'gpt-4', 'v1') RETURNING id""",
        [source_id],
        returning=True,
    )
    return str(row["id"])


def _make_draft(run_id: str, name: str) -> str:
    draft_id = str(uuid4())
    run_command(
        """INSERT INTO strategy_drafts
           (id, family_id, extraction_run_id, source_hash, version,
            name, thesis, category, direction,
            entry_rule, exit_rule, warmup_requirement,
            status, original_snapshot,
            position_mode, position_mode_confirmed,
            mts_compatibility, mts_confirmed)
           VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        [draft_id, draft_id, run_id, str(uuid4()), name, "T", "Trendfolge", "kombiniert",
         "e", "x", "1", "Entwurf", "{}", None, False, None, False],
    )
    return draft_id


def _cleanup(*names: str) -> None:
    for n in names:
        from app.services.hal_sync import safe_filename
        (HAL_QUELLEN_DIR / (safe_filename(n) + ".md")).unlink(missing_ok=True)


class TestHalSyncOnPatch:
    def test_first_save_writes_hal_file(self, client):
        src = _make_source()
        run = _make_run(src)
        d = _make_draft(run, "HalTestFirstSave")
        try:
            r = client.patch(f"/drafts/{d}", json={"thesis": "trigger sync"})
            assert r.status_code == 200
            path = HAL_QUELLEN_DIR / "HalTestFirstSave.md"
            assert path.exists()
            assert "HalTestFirstSave" in path.read_text()
        finally:
            _cleanup("HalTestFirstSave")

    def test_rename_deletes_old_file(self, client):
        src = _make_source()
        run = _make_run(src)
        d = _make_draft(run, "HalTestOldName")
        try:
            client.patch(f"/drafts/{d}", json={"thesis": "init"})
            assert (HAL_QUELLEN_DIR / "HalTestOldName.md").exists()

            r = client.patch(f"/drafts/{d}", json={"name": "HalTestNewName"})
            assert r.status_code == 200
            assert not (HAL_QUELLEN_DIR / "HalTestOldName.md").exists()
            assert (HAL_QUELLEN_DIR / "HalTestNewName.md").exists()
        finally:
            _cleanup("HalTestOldName", "HalTestNewName")

    def test_conflict_detected_even_without_name_field_in_body(self, client):
        src = _make_source()
        run_a = _make_run(src)
        d_a = _make_draft(run_a, "HalTestConflict")
        r1 = client.patch(f"/drafts/{d_a}", json={"thesis": "owner"})
        run_b = _make_run(src)
        d_b = _make_draft(run_b, "HalTestConflict")  # different family, same name, created after owner already synced
        try:
            assert r1.status_code == 200

            r2 = client.patch(f"/drafts/{d_b}", json={"thesis": "intruder, no name in body"})
            assert r2.status_code == 409

            content = (HAL_QUELLEN_DIR / "HalTestConflict.md").read_text()
            assert "owner" not in content or "HalTestConflict" in content
        finally:
            _cleanup("HalTestConflict")

    def test_overwrite_hal_bypasses_conflict(self, client):
        src = _make_source()
        run_a = _make_run(src)
        d_a = _make_draft(run_a, "HalTestOverwrite")
        r_owner = client.patch(f"/drafts/{d_a}", json={"thesis": "owner"})
        assert r_owner.status_code == 200
        run_b = _make_run(src)
        d_b = _make_draft(run_b, "HalTestOverwrite")
        try:
            r_conflict = client.patch(f"/drafts/{d_b}", json={"thesis": "intruder"})
            assert r_conflict.status_code == 409

            r_ok = client.patch(f"/drafts/{d_b}?overwrite_hal=true", json={"thesis": "intruder wins now"})
            assert r_ok.status_code == 200
        finally:
            _cleanup("HalTestOverwrite")

    def test_same_family_overwrites_without_conflict(self, client):
        src = _make_source()
        run = _make_run(src)
        d = _make_draft(run, "HalTestSameFamily")
        try:
            r1 = client.patch(f"/drafts/{d}", json={"thesis": "v1"})
            assert r1.status_code == 200
            r2 = client.patch(f"/drafts/{d}", json={"thesis": "v2"})
            assert r2.status_code == 200
        finally:
            _cleanup("HalTestSameFamily")


class TestHalSyncBackfill:
    def test_backfill_is_post(self, client):
        r = client.get("/hal/sync-all")
        assert r.status_code == 405

    def test_backfill_skips_cross_family_conflict(self, client):
        src = _make_source()
        run_a = _make_run(src)
        d_a = _make_draft(run_a, "HalTestBackfillConflict")
        run_b = _make_run(src)
        d_b = _make_draft(run_b, "HalTestBackfillConflict")
        try:
            resp = client.post("/hal/sync-all")
            assert resp.status_code == 200
            body = resp.json()
            assert body["skipped"] >= 1
            assert (HAL_QUELLEN_DIR / "HalTestBackfillConflict.md").exists()
        finally:
            _cleanup("HalTestBackfillConflict")
