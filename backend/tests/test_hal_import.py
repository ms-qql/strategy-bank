"""PROJ-21: Integrationstests für HAL-Import, Shortlist und Ergebnisansicht."""

import io
import zipfile
from unittest.mock import patch
from uuid import uuid4

import pytest
from app.db import run_command, run_query, run_query_one
from fastapi.testclient import TestClient


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


def _make_frozen_version(client, name: str = "Trendfolge SMA Kreuz") -> dict:
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
            draft_id, draft_id, run_id, str(uuid4()),
            name, "Test thesis", "Trendfolge", "kombiniert",
            "SMA Cross", "SMA Reverse", "100 bars", "Entwurf",
            "entry_exit", True, "discrete", True,
        ],
    )
    resp = client.post(f"/drafts/{draft_id}/freeze")
    assert resp.status_code == 201, resp.text
    return resp.json()


def _sample_hal_md(strategy_name: str = "Test Strategie") -> bytes:
    return f"""# Backtest: {strategy_name}

**Datum:** 2026-07-30

---

## Faktoren

| Faktor | Wert |
|--------|------|
| Asset | BTCUSDT |
| Timeframe | 4h |
| Periode | 2022-01-01 – 2024-12-31 |

---

## Ergebnis KPIs

| KPI | Wert |
|-----|------|
| Net Return | 25.0% |
| Max Drawdown | -10.0% |
| Total Trades | 40 |
| Sortino Ratio | 1.2 |
""".encode("utf-8")


@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


class TestHalImportUpload:
    def test_import_md_file(self, client):
        resp = client.post(
            "/hal-results/import",
            files=[("files", ("test.md", _sample_hal_md("SMA Cross"), "text/markdown"))],
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["total"] == 1
        assert body["files"][0]["status"] == "importiert"

    def test_import_zip_with_multiple_md(self, client):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("strat_a.md", _sample_hal_md("Strategy A"))
            zf.writestr("strat_b.md", _sample_hal_md("Strategy B"))
        resp = client.post(
            "/hal-results/import",
            files=[("files", ("backtests.zip", buf.getvalue(), "application/zip"))],
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["total"] == 2
        assert all(f["status"] == "importiert" for f in body["files"])

    def test_import_same_file_is_unchanged(self, client):
        md = _sample_hal_md("Duplicate")
        client.post("/hal-results/import", files=[("files", ("dup.md", md, "text/markdown"))])
        resp = client.post("/hal-results/import", files=[("files", ("dup.md", md, "text/markdown"))])
        assert resp.status_code == 201
        assert resp.json()["files"][0]["status"] == "unverändert"

    def test_import_changed_file_is_updated(self, client):
        md1 = _sample_hal_md("Evolving")
        client.post("/hal-results/import", files=[("files", ("ev.md", md1, "text/markdown"))])
        md2 = md1.replace(b"25.0%", b"30.0%")
        resp = client.post("/hal-results/import", files=[("files", ("ev.md", md2, "text/markdown"))])
        assert resp.status_code == 201
        assert resp.json()["files"][0]["status"] == "aktualisiert"

    def test_import_invalid_file_marked_failed(self, client):
        md = b"# No tables\n\nJust text.\n"
        resp = client.post(
            "/hal-results/import",
            files=[("files", ("bad.md", md, "text/markdown"))],
        )
        assert resp.status_code == 201
        assert resp.json()["files"][0]["status"] == "fehlerhaft"

    def test_import_non_md_rejected_in_zip(self, client):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("a.pdf", b"%PDF-1.4 fake")
        resp = client.post(
            "/hal-results/import",
            files=[("files", ("mix.zip", buf.getvalue(), "application/zip"))],
        )
        assert resp.status_code == 400

    def test_zip_slip_path_rejected_with_specific_message(self, client):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../evil.md", _sample_hal_md("Evil"))
            zf.writestr("ok.md", _sample_hal_md("Ok Strat"))
        resp = client.post(
            "/hal-results/import",
            files=[("files", ("mix.zip", buf.getvalue(), "application/zip"))],
        )
        assert resp.status_code == 201, resp.text
        files = {f["origin_path"]: f for f in resp.json()["files"]}
        assert files["../evil.md"]["status"] == "fehlerhaft"
        assert files["../evil.md"]["error_message"] == "Unsicherer Dateipfad im Archiv."
        assert files["ok.md"]["status"] == "importiert"

    def test_reupload_of_folder_with_rejected_file_does_not_crash(self, client):
        """Regression: derselbe Ordner (inkl. bereits abgelehnter Datei) darf
        beliebig oft erneut hochgeladen werden, ohne die gesamte Transaktion
        (inkl. bereits gültiger Geschwisterdateien) zu verlieren."""

        def make_zip():
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                zf.writestr("readme.pdf", b"%PDF not a backtest")
                zf.writestr("strat_ok.md", _sample_hal_md("Reupload OK Strat"))
            return buf.getvalue()

        resp1 = client.post("/hal-results/import", files=[("files", ("folder.zip", make_zip(), "application/zip"))])
        assert resp1.status_code == 201, resp1.text
        statuses1 = {f["origin_path"]: f["status"] for f in resp1.json()["files"]}
        assert statuses1["readme.pdf"] == "fehlerhaft"
        assert statuses1["strat_ok.md"] == "importiert"

        resp2 = client.post("/hal-results/import", files=[("files", ("folder.zip", make_zip(), "application/zip"))])
        assert resp2.status_code == 201, resp2.text
        statuses2 = {f["origin_path"]: f["status"] for f in resp2.json()["files"]}
        assert statuses2["readme.pdf"] == "unverändert"
        assert statuses2["strat_ok.md"] == "unverändert"

    def test_import_list_runs(self, client):
        client.post("/hal-results/import", files=[("files", ("t.md", _sample_hal_md(), "text/markdown"))])
        resp = client.get("/hal-results/imports")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_no_files_returns_400(self, client):
        resp = client.post("/hal-results/import", files=[])
        assert resp.status_code == 422


class TestHalAssignment:
    def test_name_match_is_suggestion_not_auto_assign(self, client):
        """Ein eindeutiger Namenstreffer ist ein Vorschlag, keine stille Zuweisung."""
        version = _make_frozen_version(client)
        md = _sample_hal_md("Trendfolge SMA Kreuz")
        resp = client.post("/hal-results/import", files=[("files", ("test.md", md, "text/markdown"))])
        resp_data = resp.json()
        assert resp_data["files"][0]["status"] == "importiert"
        assert resp_data["files"][0]["strategy_name"] == "Trendfolge SMA Kreuz"

        r = run_query_one(
            "SELECT hr.strategy_version_id, hr.assignment_origin FROM hal_results hr JOIN hal_imported_files hif ON hif.id = hr.imported_file_id WHERE hif.origin_path = 'test.md' AND hif.is_current = true"
        )
        assert r is not None
        assert r["strategy_version_id"] is None
        assert r["assignment_origin"] is None

        unassigned = client.get("/hal-results/unassigned").json()
        row = next(u for u in unassigned if u["import_origin_path"] == "test.md")
        assert row["suggested_version_id"] == version["id"]
        assert row["suggested_version_name"] == "Trendfolge SMA Kreuz"

    def test_ambiguous_name_match_stays_unassigned_without_suggestion(self, client):
        """Zwei unterschiedliche Strategiefamilien mit demselben Namen ⇒ kein Vorschlag."""
        _make_frozen_version(client, name="Ambiger Name")
        _make_frozen_version(client, name="Ambiger Name")
        md = _sample_hal_md("Ambiger Name")
        client.post("/hal-results/import", files=[("files", ("amb.md", md, "text/markdown"))])

        r = run_query_one(
            "SELECT hr.strategy_version_id FROM hal_results hr JOIN hal_imported_files hif ON hif.id = hr.imported_file_id WHERE hif.origin_path = 'amb.md' AND hif.is_current = true"
        )
        assert r["strategy_version_id"] is None

        unassigned = client.get("/hal-results/unassigned").json()
        row = next(u for u in unassigned if u["import_origin_path"] == "amb.md")
        assert row["suggested_version_id"] is None

    def test_list_unassigned(self, client):
        client.post("/hal-results/import", files=[("files", ("x.md", _sample_hal_md("Unknown Strategy"), "text/markdown"))])
        resp = client.get("/hal-results/unassigned")
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) >= 1

    def test_manual_assign(self, client):
        version = _make_frozen_version(client)
        client.post("/hal-results/import", files=[("files", ("z.md", _sample_hal_md("Unknown"), "text/markdown"))])
        unassigned = client.get("/hal-results/unassigned").json()
        result_id = unassigned[0]["id"]

        resp = client.post(f"/hal-results/{result_id}/assign", json={"strategy_version_id": version["id"]})
        assert resp.status_code == 200
        assert resp.json()["strategy_version_id"] == version["id"]
        assert resp.json()["assignment_origin"] == "manual"

    def test_unassign_result(self, client):
        version = _make_frozen_version(client)
        client.post("/hal-results/import", files=[("files", ("w.md", _sample_hal_md("Unlink Me"), "text/markdown"))])
        unassigned = client.get("/hal-results/unassigned").json()
        result_id = unassigned[0]["id"]
        client.post(f"/hal-results/{result_id}/assign", json={"strategy_version_id": version["id"]})

        resp = client.post(f"/hal-results/{result_id}/assign", json={"strategy_version_id": None})
        assert resp.status_code == 200
        assert resp.json()["strategy_version_id"] is None

    def test_assign_nonexistent_version_404(self, client):
        client.post("/hal-results/import", files=[("files", ("v.md", _sample_hal_md("X"), "text/markdown"))])
        unassigned = client.get("/hal-results/unassigned").json()
        result_id = unassigned[0]["id"]

        resp = client.post(f"/hal-results/{result_id}/assign", json={"strategy_version_id": str(uuid4())})
        assert resp.status_code == 404

    def test_assign_nonexistent_result_404(self, client):
        resp = client.post(f"/hal-results/{uuid4()}/assign", json={"strategy_version_id": None})
        assert resp.status_code == 404


class TestShortlist:
    def test_add_and_list_shortlist(self, client):
        version = _make_frozen_version(client)
        resp = client.put(f"/shortlist/{version['id']}")
        assert resp.status_code == 200

        lst = client.get("/shortlist").json()
        assert any(e["strategy_version_id"] == version["id"] for e in lst)

    def test_remove_from_shortlist(self, client):
        version = _make_frozen_version(client)
        client.put(f"/shortlist/{version['id']}")
        resp = client.delete(f"/shortlist/{version['id']}")
        assert resp.status_code == 204

        lst = client.get("/shortlist").json()
        assert not any(e["strategy_version_id"] == version["id"] for e in lst)

    def test_shortlist_nonexistent_version_404(self, client):
        resp = client.put(f"/shortlist/{uuid4()}")
        assert resp.status_code == 404

    def test_remove_nonexistent_is_noop(self, client):
        resp = client.delete(f"/shortlist/{uuid4()}")
        assert resp.status_code == 204


class TestResultsWithHalImport:
    def test_hal_results_appear_in_results(self, client):
        client.post(
            "/hal-results/import",
            files=[("files", ("hal_result.md", _sample_hal_md("Visible"), "text/markdown"))],
        )
        resp = client.get("/results")
        assert resp.status_code == 200
        rows = resp.json()
        hal_rows = [r for r in rows if r["result_type"] == "HAL-Import"]
        assert len(hal_rows) >= 1
        r = hal_rows[0]
        assert r["import_origin_path"] is not None
        assert r["import_hash"] is not None

    def test_hal_results_have_metrics(self, client):
        client.post(
            "/hal-results/import",
            files=[("files", ("metric.md", _sample_hal_md("Metric Test"), "text/markdown"))],
        )
        resp = client.get("/results")
        rows = resp.json()
        hal_rows = [r for r in rows if r["result_type"] == "HAL-Import"]
        r = hal_rows[0]
        assert r["net_profit_pct"] == 25.0
        assert r["max_drawdown_pct"] == -10.0
        assert r["trade_count"] == 40
        assert r["sortino_ratio"] == 1.2

    def test_updated_file_has_new_version(self, client):
        md1 = _sample_hal_md("Version Test")
        client.post("/hal-results/import", files=[("files", ("ver.md", md1, "text/markdown"))])
        md2 = md1.replace(b"25.0%", b"35.0%")
        client.post("/hal-results/import", files=[("files", ("ver.md", md2, "text/markdown"))])

        resp = client.get("/results")
        rows = [r for r in resp.json() if r["import_origin_path"] == "ver.md"]
        assert len(rows) == 1
        assert rows[0]["import_version"] == 2
        assert rows[0]["net_profit_pct"] == 35.0

    def test_unchanged_file_not_duplicated(self, client):
        md = _sample_hal_md("Dedup Test")
        client.post("/hal-results/import", files=[("files", ("dedup.md", md, "text/markdown"))])
        client.post("/hal-results/import", files=[("files", ("dedup.md", md, "text/markdown"))])

        rows = [r for r in client.get("/results").json() if r["import_origin_path"] == "dedup.md"]
        assert len(rows) == 1
