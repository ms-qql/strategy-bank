"""Tests for PROJ-17 acceptance criteria on batch instruments.

Spec contract: the frontend only sends the active subset of the user's
configured instruments; the backend must accept that list and either store
it verbatim or reject it with a clear 422. Defense in depth: an empty list
and duplicate provider_symbols must be rejected so a direct API call cannot
silently produce a no-op batch or a malformed run cartesian product.

These tests are self-contained: each test inserts the minimal data it needs
directly via SQL, without sharing fixtures with test_batches.py, so test
ordering and state pollution cannot affect the result.
"""

from unittest.mock import patch
from uuid import uuid4

from app.db import run_command


def _make_profile_via_api(client) -> str:
    resp = client.post(
        "/backtest-profiles",
        json={
            "name": "Standard",
            "timezone_session": "Exchange-Zeitzone",
            "signal_timing": "Schlusskurs",
            "fill_timing": "nächster verfügbarer Bar-Open",
            "order_type": "Market",
            "fee_pct": 0.06,
            "slippage_ticks": 2,
            "starting_capital": 10000,
            "quote_currency": "USD",
            "position_sizing": "Fix 100% Kapital",
            "compounding_rule": "Kein Compounding",
            "leverage": 1,
            "pyramiding": False,
            "max_open_positions": 1,
            "missing_bars_handling": "Bar überspringen",
            "corporate_actions_handling": "Ignorieren",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _make_frozen_version_via_api(client) -> str:
    """Legt Quelle → Extraction-Run → Entwurf an und friert ihn über die
    echten Endpunkte aus PROJ-2/3."""
    source_id = run_command(
        "INSERT INTO sources (content, source_hash, source_type) "
        "VALUES (%s, %s, %s) RETURNING id",
        ["Test content", str(uuid4()), "text"],
        returning=True,
    )["id"]
    run_id = run_command(
        "INSERT INTO extraction_runs (source_id, status, model, prompt_version) "
        "VALUES (%s, 'abgeschlossen', 'gpt-4', 'v1') RETURNING id",
        [source_id],
        returning=True,
    )["id"]
    draft_id = str(uuid4())
    run_command(
        "INSERT INTO strategy_drafts "
        "(id, family_id, extraction_run_id, source_hash, version, "
        " name, thesis, category, direction, "
        " entry_rule, exit_rule, warmup_requirement, status, "
        " position_mode, position_mode_confirmed, "
        " mts_compatibility, mts_confirmed) "
        "VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s, "
        "        %s, %s, %s, %s, %s, %s, %s, %s)",
        [
            draft_id, draft_id, run_id, "abc123",
            "Test Strategy", "Test thesis", "Trendfolge", "kombiniert",
            "RSI > 30", "RSI < 70", "100 bars", "Entwurf",
            "entry_exit", True, "discrete", True,
        ],
    )
    resp = client.post(f"/drafts/{draft_id}/freeze")
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _make_batch_with(client, instruments):
    profile_id = _make_profile_via_api(client)
    version_id = _make_frozen_version_via_api(client)
    return client.post(
        "/batches",
        json={
            "backtest_profile_id": profile_id,
            "strategy_version_ids": [version_id],
            "instruments": instruments,
        },
    )


class TestActiveListIsTheTruth:
    """The frontend sends only the user's active instruments. The backend
    must accept that list and treat it as the source of truth for runs."""

    def test_active_list_is_stored_verbatim(self, client):
        resp = _make_batch_with(
            client,
            [
                {"provider_symbol": "BYBIT:BTCUSDT.P", "label": "BTC"},
                {"provider_symbol": "BYBIT:ETHUSDT.P", "label": "ETH"},
            ],
        )
        assert resp.status_code == 201, resp.text
        batch = resp.json()
        assert [i["provider_symbol"] for i in batch["instruments"]] == [
            "BYBIT:BTCUSDT.P",
            "BYBIT:ETHUSDT.P",
        ]
        preview = client.get(f"/batches/{batch['id']}/preview").json()
        assert len(preview) == 2
        assert {p["provider_symbol"] for p in preview} == {
            "BYBIT:BTCUSDT.P",
            "BYBIT:ETHUSDT.P",
        }

    def test_missing_instruments_field_uses_server_defaults(self, client):
        profile_id = _make_profile_via_api(client)
        version_id = _make_frozen_version_via_api(client)
        resp = client.post(
            "/batches",
            json={
                "backtest_profile_id": profile_id,
                "strategy_version_ids": [version_id],
            },
        )
        assert resp.status_code == 201
        assert len(resp.json()["instruments"]) == 1


class TestDuplicateProviderSymbol:
    """Spec edge case: 'Zwei Zeilen besitzen dasselbe Provider-Symbol:
    Speichern wird mit „Provider-Symbol ist bereits vorhanden." blockiert.'"""

    def test_duplicate_symbols_rejected_on_create(self, client):
        resp = _make_batch_with(
            client,
            [
                {"provider_symbol": "BYBIT:BTCUSDT.P", "label": "BTC"},
                {"provider_symbol": "BYBIT:BTCUSDT.P", "label": "BTC again"},
            ],
        )
        assert resp.status_code == 422, resp.text
        assert "Provider-Symbol ist bereits vorhanden" in resp.text

    def test_duplicate_symbols_rejected_on_patch(self, client):
        create = _make_batch_with(
            client,
            [{"provider_symbol": "BYBIT:BTCUSDT.P", "label": "BTC"}],
        ).json()
        resp = client.patch(
            f"/batches/{create['id']}",
            json={
                "instruments": [
                    {"provider_symbol": "BYBIT:BTCUSDT.P", "label": "BTC"},
                    {"provider_symbol": "BYBIT:BTCUSDT.P", "label": "BTC again"},
                ],
            },
        )
        assert resp.status_code == 422, resp.text
        assert "Provider-Symbol ist bereits vorhanden" in resp.text

    def test_case_insensitive_duplicate_caught(self, client):
        """Provider-Symbole werden vom Backend case-sensitiv gespeichert; ein
        direkter API-Aufruf mit 'bybit:btcusdt.p' neben 'BYBIT:BTCUSDT.P'
        würde zu doppelten Runs führen, weil die Run-Vorschau pro Zeile
        einen separaten Run anlegt. Sauber wäre case-insensitive Match."""
        resp = _make_batch_with(
            client,
            [
                {"provider_symbol": "BYBIT:BTCUSDT.P", "label": "BTC"},
                {"provider_symbol": "bybit:btcusdt.p", "label": "btc"},
            ],
        )
        assert resp.status_code == 422
        assert "Provider-Symbol ist bereits vorhanden" in resp.text


class TestConfirmedBatchReadOnly:
    """Spec: 'Bestätigte Batches bleiben unveränderlich und zeigen die
    tatsächlich verwendeten Instrumente korrekt an.'"""

    def test_confirmed_batch_returns_used_instruments(self, client):
        create = _make_batch_with(
            client,
            [{"provider_symbol": "BYBIT:ETHUSDT.P", "label": "ETH"}],
        ).json()
        with patch("app.routes.batches.get_credits") as mock_credits:
            mock_credits.return_value = {
                "balance": 10, "tier": "free", "reset": "2024-01-01"
            }
            client.post(
                f"/batches/{create['id']}/confirm",
                json={"credit_max": 1},
            )
        confirmed = client.get(f"/batches/{create['id']}").json()
        assert confirmed["status"] == "bestätigt"
        assert confirmed["instruments"] == [
            {"provider_symbol": "BYBIT:ETHUSDT.P", "label": "ETH"}
        ]
