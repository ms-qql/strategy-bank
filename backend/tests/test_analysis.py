"""PROJ-23: Integrationstests für Erfolgsfaktorenanalyse."""

from uuid import uuid4

import pytest
from app.db import run_command

PINE_EMA_RSI = """//@version=5
strategy("Test", overlay=true)
fastLen = input.int(9, "Fast")
slowLen = input.int(21, "Slow")
fast = ta.ema(close, fastLen)
slow = ta.ema(close, slowLen)
rsiVal = ta.rsi(close, 14)
longCond = ta.crossover(fast, slow)
if longCond
    strategy.entry("long", strategy.long)
strategy.exit("exit", "long", stop=close * 0.95, trail_points=10)
"""

PINE_SMA = """//@version=5
strategy("Test2", overlay=true)
smaLen = input.int(50, "SMA")
sma = ta.sma(close, smaLen)
if ta.crossover(close, sma)
    strategy.entry("long", strategy.long)
if ta.crossunder(close, sma)
    strategy.close("long")
"""


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


def _make_frozen_version(client, name: str, direction: str = "kombiniert") -> dict:
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
            name, "Test thesis", "Trendfolge", direction,
            "SMA Cross", "SMA Reverse", "100 bars", "Entwurf",
            "entry_exit", True, "discrete", True,
        ],
    )
    resp = client.post(f"/drafts/{draft_id}/freeze")
    assert resp.status_code == 201, resp.text
    return resp.json()


def _sample_md(
    name: str,
    *,
    calmar_good: bool,
    direction: str = "kombiniert",
    version_id: str | None = None,
    pine: str = PINE_EMA_RSI,
    fee: str = "0.06%",
    include_pine: bool = True,
) -> bytes:
    net_return = "80.0" if calmar_good else "5.0"
    sortino = "1.2" if calmar_good else "0.1"
    extra_id = f"\n**Strategieversion-ID:** {version_id}" if version_id else ""
    pine_block = f"\n```pinescript\n{pine}\n```\n" if include_pine else ""
    return f"""# Backtest: {name}

**Datum:** 2026-07-30{extra_id}
**Richtung:** {direction}

---

## Faktoren

| Faktor | Wert |
|--------|------|
| Asset | BTCUSDT |
| Timeframe | 4h |
| Periode | 2022-01-01 – 2024-12-31 |
| Gebühren | {fee} |
| Slippage | 2 |
| Sizing-Modell | Fix 100% |

---

## Ergebnis KPIs

| KPI | Wert |
|-----|------|
| Net Return | {net_return}% |
| Max Drawdown | -10.0% |
| Total Trades | 60 |
| Sortino Ratio | {sortino} |
{pine_block}""".encode("utf-8")


@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


class TestAnalysisRunCreation:
    def test_create_run_computes_success_and_features(self, client):
        v_good = _make_frozen_version(client, "Erfolgreiche Strategie", direction="kombiniert")
        v_bad = _make_frozen_version(client, "Erfolglose Strategie", direction="short-only")

        client.post(
            "/hal-results/import",
            files=[(
                "files",
                ("good.md", _sample_md("Erfolgreiche Strategie", calmar_good=True, version_id=v_good["id"], pine=PINE_EMA_RSI), "text/markdown"),
            )],
        )
        client.post(
            "/hal-results/import",
            files=[(
                "files",
                ("bad.md", _sample_md("Erfolglose Strategie", calmar_good=False, direction="short-only", version_id=v_bad["id"], pine=PINE_SMA), "text/markdown"),
            )],
        )

        resp = client.post("/analysis/runs")
        assert resp.status_code == 201, resp.text
        run = resp.json()
        assert run["total_analyzed"] == 2
        assert run["total_excluded"] == 0

        detail = client.get(f"/analysis/runs/{run['id']}?axis=indicator").json()
        rows_by_name = {r["strategy_name"]: r for r in detail["rows"]}
        assert rows_by_name["Erfolgreiche Strategie"]["is_success"] is True
        assert rows_by_name["Erfolglose Strategie"]["is_success"] is False
        assert set(rows_by_name["Erfolgreiche Strategie"]["indicators"]) == {"EMA", "RSI"}
        assert rows_by_name["Erfolglose Strategie"]["indicators"] == ["SMA"]

    def test_result_without_pine_code_excluded(self, client):
        _make_frozen_version(client, "Ohne Pine")
        client.post(
            "/hal-results/import",
            files=[(
                "files",
                ("no-pine.md", _sample_md("Ohne Pine", calmar_good=True, include_pine=False), "text/markdown"),
            )],
        )

        resp = client.post("/analysis/runs")
        assert resp.status_code == 400, resp.text

    def test_reimport_of_same_version_keeps_only_newest(self, client):
        version = _make_frozen_version(client, "Korrigiert")
        client.post(
            "/hal-results/import",
            files=[(
                "files",
                ("v1.md", _sample_md("Korrigiert Alt", calmar_good=False, version_id=version["id"], pine=PINE_SMA), "text/markdown"),
            )],
        )
        client.post(
            "/hal-results/import",
            files=[(
                "files",
                ("v2.md", _sample_md("Korrigiert Neu", calmar_good=True, version_id=version["id"], pine=PINE_EMA_RSI), "text/markdown"),
            )],
        )

        resp = client.post("/analysis/runs")
        run = resp.json()
        assert run["total_analyzed"] == 1

        detail = client.get(f"/analysis/runs/{run['id']}?axis=indicator").json()
        assert len(detail["rows"]) == 1
        row = detail["rows"][0]
        assert row["strategy_name"] == "Korrigiert Neu"
        assert row["is_success"] is True

    def test_direction_axis_uses_canonical_values(self, client):
        v = _make_frozen_version(client, "Long Only Strat", direction="long-only")
        client.post(
            "/hal-results/import",
            files=[(
                "files",
                ("dir.md", _sample_md("Long Only Strat", calmar_good=True, direction="long-only", version_id=v["id"]), "text/markdown"),
            )],
        )
        run = client.post("/analysis/runs").json()
        detail = client.get(f"/analysis/runs/{run['id']}?axis=direction").json()
        assert detail["rows"][0]["direction"] == "long-only"
        assert any(row["value"] == "long-only" for row in detail["cohort"])

    def test_empty_success_group_has_no_available_lift(self, client):
        v = _make_frozen_version(client, "Nur Verlierer")
        client.post(
            "/hal-results/import",
            files=[(
                "files",
                ("loser.md", _sample_md("Nur Verlierer", calmar_good=False, version_id=v["id"]), "text/markdown"),
            )],
        )
        run = client.post("/analysis/runs").json()
        detail = client.get(f"/analysis/runs/{run['id']}?axis=indicator").json()
        assert all(row["lift"] is None for row in detail["cohort"])
        assert all(row["success"] == 0 for row in detail["cohort"])

    def test_run_does_not_modify_strategy_or_hal_data(self, client):
        v = _make_frozen_version(client, "Unveraendert")
        client.post(
            "/hal-results/import",
            files=[(
                "files",
                ("unchanged.md", _sample_md("Unveraendert", calmar_good=True, version_id=v["id"]), "text/markdown"),
            )],
        )
        from app.db import run_query_one
        before_sv = run_query_one("SELECT COUNT(*)::int c FROM strategy_versions")
        before_hr = run_query_one("SELECT COUNT(*)::int c FROM hal_results")

        client.post("/analysis/runs")

        after_sv = run_query_one("SELECT COUNT(*)::int c FROM strategy_versions")
        after_hr = run_query_one("SELECT COUNT(*)::int c FROM hal_results")
        assert before_sv == after_sv
        assert before_hr == after_hr

    def test_invalid_axis_returns_400(self, client):
        v = _make_frozen_version(client, "Achse Test")
        client.post(
            "/hal-results/import",
            files=[(
                "files",
                ("axis.md", _sample_md("Achse Test", calmar_good=True, version_id=v["id"]), "text/markdown"),
            )],
        )
        run = client.post("/analysis/runs").json()
        resp = client.get(f"/analysis/runs/{run['id']}?axis=bogus")
        assert resp.status_code == 400

    def test_delete_run_does_not_touch_results(self, client):
        v = _make_frozen_version(client, "Loeschbar")
        client.post(
            "/hal-results/import",
            files=[(
                "files",
                ("del.md", _sample_md("Loeschbar", calmar_good=True, version_id=v["id"]), "text/markdown"),
            )],
        )
        run = client.post("/analysis/runs").json()

        del_resp = client.delete(f"/analysis/runs/{run['id']}")
        assert del_resp.status_code == 204
        assert client.get(f"/analysis/runs/{run['id']}").status_code == 404
        assert client.get("/results").json()

    def test_delete_nonexistent_run_returns_404(self, client):
        assert client.delete(f"/analysis/runs/{uuid4()}").status_code == 404

    def test_no_comparable_results_returns_400(self, client):
        resp = client.post("/analysis/runs")
        assert resp.status_code == 400

    def test_list_runs(self, client):
        v = _make_frozen_version(client, "Listbar")
        client.post(
            "/hal-results/import",
            files=[(
                "files",
                ("list.md", _sample_md("Listbar", calmar_good=True, version_id=v["id"]), "text/markdown"),
            )],
        )
        client.post("/analysis/runs")
        client.post("/analysis/runs")
        runs = client.get("/analysis/runs").json()
        assert len(runs) == 2
