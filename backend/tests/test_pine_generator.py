"""PROJ-6 Pine-Generator Tests — LLM-basierter Ansatz (ersetzt Regex-Übersetzer)."""
import pytest
from app.services import pine_generator as pg


SNAPSHOT = {
    "thesis": "Mean-Reversion via RSI",
    "category": "Mean Reversion",
    "direction": "kombiniert",
    "entry_rule": "RSI > 30",
    "exit_rule": "RSI < 70",
    "position_mode": "entry_exit",
    "parameters": [{"name": "RSI Length", "value": "14", "unit": "bars"}],
}


class TestBuildPrompt:
    def test_includes_snapshot_fields(self):
        prompt = pg.build_prompt(
            SNAPSHOT,
            params=SNAPSHOT["parameters"],
            timeframe="4h",
            direction="kombiniert",
            initial_capital=10_000,
            commission_pct=0.06,
            slippage_ticks=2,
            pyramiding=0,
        )
        assert "RSI > 30" in prompt
        assert "RSI < 70" in prompt
        assert "RSI Length" in prompt
        assert "4h" in prompt
        assert "```pine" in prompt

    def test_missing_exit_rule_asks_for_default(self):
        snapshot = {**SNAPSHOT, "exit_rule": ""}
        prompt = pg.build_prompt(
            snapshot, params=[], timeframe="1h", direction="kombiniert",
            initial_capital=10_000, commission_pct=0.06, slippage_ticks=2, pyramiding=0,
        )
        assert "Systemdefault" in prompt

    def test_signal_reversal_is_described_without_internal_enum(self):
        snapshot = {**SNAPSHOT, "position_mode": "signal_reversal"}
        prompt = pg.build_prompt(
            snapshot, params=[], timeframe="4h", direction="kombiniert",
            initial_capital=10_000, commission_pct=0.06, slippage_ticks=2, pyramiding=0,
        )
        assert "signal_reversal" not in prompt
        assert "Gegensignal" in prompt


class TestExtractPine:
    def test_extracts_fenced_block(self):
        raw = "Hier ist das Script:\n```pine\n//@version=5\nstrategy(\"x\")\n```\nFertig."
        assert pg._extract_pine(raw) == '//@version=5\nstrategy("x")'

    def test_extracts_unfenced_source(self):
        raw = '//@version=5\nstrategy("x")'
        assert pg._extract_pine(raw) == raw

    def test_rejects_text_without_version_tag(self):
        assert pg._extract_pine("Ich kann das nicht generieren.") == ""

    def test_rejects_internal_position_mode_as_strategy_api(self):
        raw = '//@version=5\nstrategy("x")\nstrategy.signal_reversal'
        assert pg._extract_pine(raw) == ""


class TestGenerate:
    def test_missing_entry_raises(self):
        with pytest.raises(pg.PineGenerationError, match="Entry-Regel fehlt"):
            pg.generate({"entry_rule": "", "exit_rule": "RSI > 70"})

    def test_returns_llm_pine_source(self, monkeypatch):
        monkeypatch.setattr(pg, "run_opencode", lambda prompt: "```pine\n//@version=5\nstrategy(\"x\")\n```")
        code = pg.generate(SNAPSHOT)
        assert code == '//@version=5\nstrategy("x")'

    def test_invalid_llm_output_raises(self, monkeypatch):
        monkeypatch.setattr(pg, "run_opencode", lambda prompt: "Kann ich nicht generieren.")
        with pytest.raises(pg.PineGenerationError, match="kein gültiges Pine"):
            pg.generate(SNAPSHOT)

    def test_llm_call_failure_raises(self, monkeypatch):
        def _boom(prompt):
            raise RuntimeError("OpenCode-Prozess beendet mit Code 1")
        monkeypatch.setattr(pg, "run_opencode", _boom)
        with pytest.raises(pg.PineGenerationError, match="fehlgeschlagen"):
            pg.generate(SNAPSHOT)
