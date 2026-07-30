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
         "RSI < 30", "RSI > 70", "20 bars", "Entwurf", "{}", None, False, None, False],
    )
    return draft_id


class TestHalExportSingle:
    def test_export_returns_markdown_with_content_disposition(self, client):
        src = _make_source()
        run = _make_run(src)
        d = _make_draft(run, "HalExportTest")

        r = client.get(f"/hal/drafts/{d}/export")
        assert r.status_code == 200
        assert r.headers["content-disposition"] == "attachment; filename=HalExportTest.md"
        assert "# HalExportTest" in r.text
        assert "RSI < 30" in r.text

    def test_export_unknown_draft_404(self, client):
        r = client.get(f"/hal/drafts/{uuid4()}/export")
        assert r.status_code == 404

    def test_patch_no_longer_triggers_filesystem_write(self, client):
        # Regression guard: Hal-Sync is download-only now, PATCH must not
        # depend on any filesystem/Hal-Sync side effect to succeed.
        src = _make_source()
        run = _make_run(src)
        d = _make_draft(run, "HalPatchNoSideEffect")
        r = client.patch(f"/drafts/{d}", json={"thesis": "changed"})
        assert r.status_code == 200


class TestHalExportAll:
    def test_export_all_returns_zip_containing_draft(self, client):
        import zipfile
        import io

        src = _make_source()
        run = _make_run(src)
        _make_draft(run, "HalZipEntryTest")

        r = client.get("/hal/export-all")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        assert "HalZipEntryTest.md" in zf.namelist()
        content = zf.read("HalZipEntryTest.md").decode("utf-8")
        assert "# HalZipEntryTest" in content

    def test_export_all_dedupes_same_filename_across_families(self, client):
        import zipfile
        import io

        src = _make_source()
        run_a = _make_run(src)
        _make_draft(run_a, "HalZipDuplicateName")
        run_b = _make_run(src)
        _make_draft(run_b, "HalZipDuplicateName")

        r = client.get("/hal/export-all")
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        matching = [n for n in zf.namelist() if n.startswith("HalZipDuplicateName")]
        assert len(matching) == 2
        assert len(set(matching)) == 2


class TestHalExportSelected:
    def test_export_selected_includes_only_chosen_sources(self, client):
        import zipfile
        import io

        src_a = _make_source()
        run_a = _make_run(src_a)
        _make_draft(run_a, "HalSelectedIncluded")

        src_b = _make_source()
        run_b = _make_run(src_b)
        _make_draft(run_b, "HalSelectedExcluded")

        r = client.post("/hal/export-selected", json={"source_ids": [src_a]})
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        assert "HalSelectedIncluded.md" in zf.namelist()
        assert "HalSelectedExcluded.md" not in zf.namelist()

    def test_export_selected_multiple_sources(self, client):
        import zipfile
        import io

        src_a = _make_source()
        run_a = _make_run(src_a)
        _make_draft(run_a, "HalMultiA")

        src_b = _make_source()
        run_b = _make_run(src_b)
        _make_draft(run_b, "HalMultiB")

        r = client.post("/hal/export-selected", json={"source_ids": [src_a, src_b]})
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        assert "HalMultiA.md" in zf.namelist()
        assert "HalMultiB.md" in zf.namelist()

    def test_export_selected_empty_list_400(self, client):
        r = client.post("/hal/export-selected", json={"source_ids": []})
        assert r.status_code == 400

    def test_export_selected_unknown_source_returns_empty_zip(self, client):
        import zipfile
        import io

        r = client.post("/hal/export-selected", json={"source_ids": [str(uuid4())]})
        assert r.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        assert zf.namelist() == []

    def test_export_selected_dedupes_same_filename(self, client):
        import zipfile
        import io

        src = _make_source()
        run_a = _make_run(src)
        _make_draft(run_a, "HalSelectedDuplicateName")
        run_b = _make_run(src)
        _make_draft(run_b, "HalSelectedDuplicateName")

        r = client.post("/hal/export-selected", json={"source_ids": [src]})
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        matching = [n for n in zf.namelist() if n.startswith("HalSelectedDuplicateName")]
        assert len(matching) == 2
        assert len(set(matching)) == 2
