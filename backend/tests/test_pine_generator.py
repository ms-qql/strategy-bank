"""PROJ-6 Pine-Generator Tests."""
import pytest
from app.services.pine_generator import (
    PineGenerationError,
    _is_bar_count_exit,
    _translate_rule,
    _build_context,
    generate,
)


class TestBarCountExit:
    def test_detects_german_default(self):
        assert _is_bar_count_exit("Exit nach 10 vollständig vergangenen Bars")

    def test_detects_english(self):
        assert _is_bar_count_exit("Exit after 10 completed bars")

    def test_rejects_normal_rule(self):
        assert not _is_bar_count_exit("RSI > 70")


class TestRSITranslation:
    def test_rsi_below(self):
        expr = _translate_rule("RSI < 30", {})
        assert "ta.rsi(close, 14)" in expr
        assert "< 30" in expr

    def test_rsi_with_explicit_period(self):
        expr = _translate_rule("RSI(7) < 25", {})
        assert "ta.rsi(close, 7)" in expr
        assert "< 25" in expr

    def test_rsi_with_parameter(self):
        ctx = _build_context([{"name": "RSI Period", "value": "21", "unit": ""}])
        expr = _translate_rule("RSI < 30", ctx)
        assert "rsi_period" in expr or "21" in expr


class TestSMATranslation:
    def test_close_gt_sma(self):
        expr = _translate_rule("Close > SMA(200)", {})
        assert "close" in expr
        assert "ta.sma(close" in expr
        assert "200" in expr

    def test_close_cross_above_sma(self):
        expr = _translate_rule("Close crosses above SMA(50)", {})
        assert "ta.crossover(close, ta.sma(close, 50))" in expr


class TestAndOrSplit:
    def test_and_condition(self):
        expr = _translate_rule("RSI < 30 AND Close > SMA(200)", {})
        assert "and" in expr
        assert "ta.rsi" in expr
        assert "ta.sma" in expr

    def test_or_condition(self):
        expr = _translate_rule("RSI < 30 OR MACD crosses above zero", {})
        assert "or" in expr.lower() or "or" in expr


class TestPineGeneration:
    def test_minimal_strategy(self):
        snapshot = {
            "entry_rule": "RSI < 30",
            "exit_rule": "",
            "direction": "kombiniert",
            "position_mode": "entry_exit",
        }
        code = generate(snapshot)
        assert "// @version=5" in code
        assert "ta.rsi(close, 14)" in code
        assert "strategy.entry" in code
        assert "strategy.close_all" in code

    def test_long_only(self):
        snapshot = {
            "entry_rule": "Close > SMA(20)",
            "exit_rule": "Exit nach 10 vollständig vergangenen Bars",
            "direction": "long-only",
            "position_mode": "entry_exit",
        }
        code = generate(snapshot)
        assert "strategy.long" in code
        assert "strategy.short" not in code

    def test_signal_reversal(self):
        snapshot = {
            "entry_rule": "RSI crosses above 30",
            "exit_rule": "",
            "direction": "kombiniert",
            "position_mode": "signal_reversal",
        }
        code = generate(snapshot)
        assert "signal reversal" in code.lower()

    def test_with_parameters(self):
        snapshot = {
            "entry_rule": "RSI < 30 AND Close > SMA(200)",
            "exit_rule": "",
            "direction": "kombiniert",
            "position_mode": "entry_exit",
        }
        params = [
            {"name": "RSI Period", "value": "14", "unit": ""},
            {"name": "SMA Period", "value": "200", "unit": ""},
        ]
        code = generate(snapshot, params)
        assert "input.float" in code

    def test_bar_count_exit(self):
        snapshot = {
            "entry_rule": "RSI < 30",
            "exit_rule": "Exit nach 10 vollständig vergangenen Bars",
            "direction": "kombiniert",
            "position_mode": "entry_exit",
        }
        code = generate(snapshot)
        assert "_barSinceEntry" in code

    def test_missing_entry_raises(self):
        with pytest.raises(PineGenerationError, match="Entry-Regel fehlt"):
            generate({"entry_rule": "", "exit_rule": "RSI > 70"})

    def test_unrecognized_rule_raises(self):
        with pytest.raises(PineGenerationError, match="übersetzbar"):
            _translate_rule("Some exotic indicator pattern", {})

    def test_macd_crossover(self):
        expr = _translate_rule("MACD crosses above signal", {})
        assert "ta.crossover" in expr
        assert "ta.macd" in expr

    def test_volume_condition(self):
        expr = _translate_rule("Volume > SMA(20)", {})
        assert "volume" in expr
        assert "ta.sma(volume" in expr

    def test_build_context(self):
        ctx = _build_context([
            {"name": "RSI Period", "value": "14", "unit": ""},
            {"name": "SMA Fast", "value": "50", "unit": ""},
        ])
        assert "rsi_period" in ctx or len(ctx) == 2


class TestPineScriptValidity:
    """Checks that generated Pine code contains required structural elements."""

    def test_has_strategy_declaration(self):
        snapshot = {
            "entry_rule": "RSI < 30",
            "exit_rule": "",
            "direction": "kombiniert",
            "position_mode": "entry_exit",
        }
        code = generate(snapshot)
        assert "// @version=5" in code
        assert "strategy.entry" in code

    def test_has_bar_tracking(self):
        snapshot = {
            "entry_rule": "RSI < 30",
            "exit_rule": "",
            "direction": "kombiniert",
            "position_mode": "entry_exit",
        }
        code = generate(snapshot)
        assert "_barSinceEntry" in code

    def test_has_fail_safe(self):
        snapshot = {
            "entry_rule": "RSI < 30",
            "exit_rule": "",
            "direction": "kombiniert",
            "position_mode": "entry_exit",
        }
        code = generate(snapshot)
        assert "fail-safe" in code or "close_all" in code

    def test_short_only_inverts(self):
        snapshot = {
            "entry_rule": "RSI < 30",
            "exit_rule": "",
            "direction": "short-only",
            "position_mode": "entry_exit",
        }
        code = generate(snapshot)
        assert "strategy.short" in code
