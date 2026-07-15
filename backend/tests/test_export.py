"""PROJ-9: Tests für den Markdown-Export-Endpunkt."""

import re
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db import run_command, run_query_one


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
    warmup = overrides.pop("warmup_requirement", "0 bars")
    status = overrides.pop("status", "Entwurf")
    position_mode = overrides.pop("position_mode", None)
    position_mode_confirmed = overrides.pop("position_mode_confirmed", False)
    mts_compatibility = overrides.pop("mts_compatibility", None)
    mts_confirmed = overrides.pop("mts_confirmed", False)
    run_command(
        """INSERT INTO strategy_drafts
           (id, family_id, extraction_run_id, source_hash, version,
            name, thesis, category, direction,
            entry_rule, exit_rule, warmup_requirement,
            simultaneous_entry_exit_behavior, reversal_behavior,
            status, original_snapshot,
            position_mode, position_mode_confirmed,
            mts_compatibility, mts_confirmed)
           VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        [
            draft_id,
            draft_id,
            run_id,
            "abc123",
            name,
            thesis,
            category,
            direction,
            entry_rule,
            exit_rule,
            warmup,
            overrides.get("simultaneous_entry_exit_behavior"),
            overrides.get("reversal_behavior"),
            status,
            '{"name":"KI-Name","thesis":"KI-These","parameters":[]}',
            position_mode,
            position_mode_confirmed,
            mts_compatibility,
            mts_confirmed,
        ],
    )
    return {"id": draft_id, "family_id": draft_id, "name": name, "status": status}


def _add_parameter(draft_id: str, name: str, value: str) -> None:
    run_command(
        "INSERT INTO draft_parameters (draft_id, name, value, is_proposal) VALUES (%s, %s, %s, false)",
        [draft_id, name, value],
    )


def _freeze_draft(client: TestClient, draft_id: str) -> dict:
    client.patch(
        f"/drafts/{draft_id}",
        json={
            "position_mode": "entry_exit",
            "position_mode_confirmed": True,
            "mts_compatibility": "discrete",
            "mts_confirmed": True,
        },
    )
    resp = client.post(f"/drafts/{draft_id}/freeze")
    assert resp.status_code == 201, resp.text
    return resp.json()


def _make_run(
    strategy_version_id: str,
    *,
    run_kind: str = "standard",
    run_status: str = "erfolgreich",
    report_link: str | None = "https://trader.dev/report/abc",
    raw_response_available: bool = True,
    backtest_result: dict | None = None,
) -> str:
    profile_id = str(uuid4())
    run_command(
        """INSERT INTO backtest_profiles
           (id, family_id, version_number, name, timezone_session, order_type,
            position_sizing, compounding_rule, missing_bars_handling,
            corporate_actions_handling)
           VALUES (%s, %s, 1, 'test', 'Exchange', 'Market',
                   'Fix 100%%', 'Kein Compounding', 'Bar überspringen', 'Ignorieren')""",
        [profile_id, profile_id],
    )

    batch_id = str(uuid4())
    run_command(
        """INSERT INTO batches
           (id, backtest_profile_id, timeframe, period_start, period_end, run_kind, status)
           VALUES (%s, %s, '4h', '2024-01-01', '2024-12-31', %s, 'bestätigt')""",
        [batch_id, profile_id, run_kind],
    )

    run_id = str(uuid4())
    run_command(
        """INSERT INTO runs
           (id, batch_id, strategy_version_id, provider_symbol, direction_mode, run_kind,
            status, created_at)
           VALUES (%s, %s, %s, 'BYBIT:BTCUSDT.P', 'kombiniert', %s, %s, NOW())""",
        [run_id, batch_id, strategy_version_id, run_kind, run_status],
    )

    if backtest_result:
        be_id = str(uuid4())
        run_command(
            """INSERT INTO backtest_executions
               (id, idempotency_key, strategy_version_id, provider_symbol, timeframe,
                period_start, period_end, direction_mode, backtest_profile_version_id,
                evaluation_type, pine_source, executor_fingerprint, backtest_result, report_link)
               VALUES (%s, %s, %s, 'BYBIT:BTCUSDT.P', '4h',
                       '2024-01-01', '2024-12-31', 'kombiniert', %s, %s,
                       'pine', 'v1', %s, %s)""",
            [
                be_id,
                str(uuid4()),
                strategy_version_id,
                profile_id,
                run_kind,
                __import__("json").dumps(backtest_result),
                report_link,
            ],
        )
        run_command(
            "UPDATE runs SET backtest_execution_id = %s WHERE id = %s", [be_id, run_id]
        )

    run_command(
        """INSERT INTO run_audits
           (run_id, batch_id, strategy_snapshot, profile_snapshot,
            provider_symbol, timeframe, period_start, period_end, direction_mode, run_kind,
            credit_max, credit_balance, credit_remaining, credit_tier, credit_reset,
            report_link, raw_response_available)
           VALUES (%s, %s, '{}', '{}', 'BYBIT:BTCUSDT.P', '4h',
                   '2024-01-01', '2024-12-31', 'kombiniert', %s,
                   0, 0, 0, '', '', %s, %s)""",
        [run_id, batch_id, run_kind, report_link, raw_response_available],
    )

    return run_id


class TestExportMarkdown:
    def test_404_missing_draft(self, client):
        resp = client.get("/drafts/00000000-0000-0000-0000-000000000000/export.md")
        assert resp.status_code == 404

    def test_export_content_type_is_markdown(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]

    def test_export_with_no_versions(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text

        assert f"# {d['name']}" in content
        assert f"`{d['family_id']}`" in content
        assert "**Exportierte Versionen:** 0" in content
        assert "Noch nicht eingefroren" in content

    def test_export_with_frozen_version_and_run(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)
        _add_parameter(d["id"], "period", "14")
        version = _freeze_draft(client, d["id"])

        _make_run(
            version["id"],
            backtest_result={
                "netProfitPct": 12.5,
                "tradeCount": 42,
                "maxDrawdownPct": -8.3,
                "sharpeRatio": 1.2,
                "profitFactor": 2.1,
                "cagrPct": 8.0,
            },
        )

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text

        assert f"# {d['name']}" in content
        assert "**Exportierte Versionen:** 1" in content
        assert "## Version 1 — Freigegeben am" in content
        assert "Test Strategy" in content
        assert "RSI > 30" in content
        assert "RSI < 70" in content
        assert "| period | 14 |" in content
        assert "| `abc123` |" in content
        assert "| gpt-4 |" in content
        assert "| v1 |" in content
        assert "Entry-/Exit-Regel" in content
        assert "Diskret" in content
        assert "BYBIT:BTCUSDT.P" in content
        assert "12.50" in content
        assert "42" in content
        assert "-8.30" in content
        assert "1.20" in content
        assert "2.10" in content
        assert "8.00" in content
        assert "[Link](https://trader.dev/report/abc)" in content

    def test_export_version_with_no_runs(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)
        _freeze_draft(client, d["id"])

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text

        assert "*Keine Runs vorhanden.*" in content

    def test_export_run_incomplete_no_report_link(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)
        version = _freeze_draft(client, d["id"])

        _make_run(
            version["id"],
            report_link=None,
            backtest_result={"netProfitPct": 5.0, "tradeCount": 10},
        )

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text

        assert "(unvollständig)" in content

    def test_export_run_incomplete_no_raw_response(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)
        version = _freeze_draft(client, d["id"])

        _make_run(
            version["id"],
            report_link="https://trader.dev/report/abc",
            raw_response_available=False,
            backtest_result={"netProfitPct": 5.0, "tradeCount": 10},
        )

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text

        assert "(unvollständig)" in content

    def test_export_legacy_version_without_proj10(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)
        version = _freeze_draft(client, d["id"])

        run_command(
            "UPDATE strategy_versions SET snapshot = %s WHERE id = %s",
            [
                '{"name":"Legacy","thesis":"Alt","category":"Trendfolge","direction":"kombiniert",'
                '"entry_rule":"E1","exit_rule":"X1","warmup_requirement":"0 bars",'
                '"simultaneous_entry_exit_behavior":null,"reversal_behavior":null,'
                '"position_mode":null,"position_mode_confirmed":null,'
                '"exit_rule_origin":null,"mts_compatibility":null,"mts_confirmed":null,'
                '"parameters":[]}',
                version["id"],
            ],
        )

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text

        assert "Nicht verfügbar — Legacy-Version" in content

    def test_export_filename_header(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, name="My Strategy")

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        cd = resp.headers["content-disposition"]
        assert 'filename="My_Strategy_' in cd
        assert cd.endswith('.md"')

    def test_export_markdown_escaping(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, name="Test | Pipe")
        _add_parameter(d["id"], "param|name", "val|ue")
        _freeze_draft(client, d["id"])

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text

        assert "Test \\| Pipe" in content
        assert "param\\|name" in content
        assert "val\\|ue" in content

    def test_export_newline_in_text_escaped(self, client):
        """BUG-1 fix: Zeilenumbrüche werden zu <br> escaped."""
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, thesis="Zeile 1\nZeile 2")
        _freeze_draft(client, d["id"])

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text

        assert "Zeile 1<br>Zeile 2" in content
        assert "\n" not in content.split("Zeile 1")[1].split("Zeile 2")[0]

    def test_export_deterministic(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)
        version = _freeze_draft(client, d["id"])

        _make_run(
            version["id"],
            backtest_result={"netProfitPct": 10.0, "tradeCount": 5},
        )

        resp1 = client.get(f"/drafts/{d['id']}/export.md")
        resp2 = client.get(f"/drafts/{d['id']}/export.md")

        assert resp1.text == resp2.text

    def test_export_multiple_versions(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d1 = _make_draft(run, name="V1 Strategy")
        v1 = _freeze_draft(client, d1["id"])

        d2 = _make_draft(run, name="V2 Strategy")
        family_id = d1["family_id"]
        run_command(
            "UPDATE strategy_drafts SET family_id = %s WHERE id = %s",
            [family_id, d2["id"]],
        )
        d2_patched = client.patch(
            f"/drafts/{d2['id']}",
            json={
                "position_mode": "entry_exit",
                "position_mode_confirmed": True,
                "mts_compatibility": "discrete",
                "mts_confirmed": True,
            },
        )
        assert d2_patched.status_code == 200
        v2_resp = client.post(f"/drafts/{d2['id']}/freeze")
        assert v2_resp.status_code == 201
        v2 = v2_resp.json()

        _make_run(v1["id"], backtest_result={"netProfitPct": 5.0, "tradeCount": 3})
        _make_run(v2["id"], backtest_result={"netProfitPct": 15.0, "tradeCount": 7})

        resp = client.get(f"/drafts/{d1['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text

        assert "**Exportierte Versionen:** 2" in content
        assert "## Version 1 —" in content
        assert "## Version 2 —" in content
        assert "V1 Strategy" in content
        assert "V2 Strategy" in content
        assert "5.00" in content
        assert "15.00" in content

        v1_pos = content.index("## Version 1")
        v2_pos = content.index("## Version 2")
        assert v1_pos < v2_pos

    def test_export_draft_statuses(self, client):
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run, name="Main Strategy")
        _freeze_draft(client, d["id"])

        family_id = d["family_id"]
        draft2_id = str(uuid4())
        run_command(
            """INSERT INTO strategy_drafts
               (id, family_id, extraction_run_id, source_hash, version,
                name, thesis, category, direction,
                entry_rule, exit_rule, warmup_requirement, status,
                position_mode, position_mode_confirmed,
                mts_compatibility, mts_confirmed)
               VALUES (%s, %s, %s, 'abc123', 1, 'Untestable Draft', '', 'Sonstige', 'kombiniert',
                       '', '', '', 'nicht testbar',
                       NULL, false, NULL, false)""",
            [draft2_id, family_id, run],
        )

        draft3_id = str(uuid4())
        run_command(
            """INSERT INTO strategy_drafts
               (id, family_id, extraction_run_id, source_hash, version,
                name, thesis, category, direction,
                entry_rule, exit_rule, warmup_requirement, status,
                position_mode, position_mode_confirmed,
                mts_compatibility, mts_confirmed)
               VALUES (%s, %s, %s, 'abc123', 1, 'Draft V3', '', 'Sonstige', 'kombiniert',
                       '', '', '', 'Entwurf',
                       NULL, false, NULL, false)""",
            [draft3_id, family_id, run],
        )

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text

        assert "Entwurf: Untestable Draft — Nicht testbar" in content
        assert "Entwurf: Draft V3 — Entwurf" in content

    def test_export_run_running_shows_laeuft_status(self, client):
        """EC-3: Laufender Run erscheint mit Status 'Läuft'."""
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)
        version = _freeze_draft(client, d["id"])

        _make_run(
            version["id"],
            run_status="läuft",
            backtest_result=None,
            report_link=None,
        )

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text
        assert "Läuft" in content
        assert "(unvollständig)" in content  # no report link

    def test_export_run_planned_shows_geplant_status(self, client):
        """Geplanter Run erscheint mit Status 'Geplant'."""
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)
        version = _freeze_draft(client, d["id"])

        _make_run(
            version["id"],
            run_status="geplant",
            backtest_result=None,
            report_link=None,
        )

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text
        assert "Geplant" in content

    def test_export_run_failed_shows_failed_status(self, client):
        """Fehlgeschlagener Run erscheint mit Status 'Fehlgeschlagen'."""
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)
        version = _freeze_draft(client, d["id"])

        _make_run(
            version["id"],
            run_status="fehlgeschlagen",
            backtest_result=None,
            report_link=None,
        )

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text
        assert "Fehlgeschlagen" in content

    def test_export_run_aborted_shows_aborted_status(self, client):
        """Abgebrochener Run erscheint mit Status 'Abgebrochen'."""
        src = _make_source()
        run = _make_extraction_run(src)
        d = _make_draft(run)
        version = _freeze_draft(client, d["id"])

        _make_run(
            version["id"],
            run_status="abgebrochen",
            backtest_result=None,
            report_link=None,
        )

        resp = client.get(f"/drafts/{d['id']}/export.md")
        assert resp.status_code == 200
        content = resp.text
        assert "Abgebrochen" in content
