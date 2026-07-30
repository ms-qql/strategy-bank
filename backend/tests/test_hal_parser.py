"""PROJ-21: Tests für Hal-Backtest-Parser."""

from datetime import date

from app.services.hal_parser import parse_hal_backtest


SAMPLE_MD = """# Backtest: Trendfolge SMA Kreuz

**Datum:** 2026-07-30
**Quelle:** [01_Quellen/SMA_Cross.md](../01_Quellen/SMA_Cross.md)

**Richtung:** kombiniert

---

## Faktoren

| Faktor | Wert |
|--------|------|
| Asset | BYBIT:BTCUSDT.P (BTC) |
| Timeframe | 4h |
| Periode | 2022-01-01 – 2024-12-31 |
| Bars | 6570 |

---

## Input-Parameter

| Parameter | Wert | Beschreibung |
|-----------|------|--------------|
| Fast MA | 20 | Schneller gleitender Durchschnitt |
| Slow MA | 100 | Langsamer gleitender Durchschnitt |

---

## Ergebnis KPIs

| KPI | Wert |
|-----|------|
| Startkapital | $10000 |
| Endkapital | $15600 |
| **Net Return** | **56.0%** |
| Profit Factor | 1.8 |
| Win Rate | 42% (21/50) |
| Sharpe Ratio | 1.2 |
| Sortino Ratio | 1.5 |
| Max Drawdown | -15.0% |
| Total Trades | 50 |
| Kommission gesamt | $120.00 |

### Long/Short-Breakdown

| Richtung | Trades | Winning | Net P&L |
|----------|--------|---------|---------|
| Long | 30 | 15 | +$4200 |
| Short | 20 | 6 | +$1400 |

---

## Report

https://trader.dev/report/abc123

---

## Pine Script

```pinescript
//@version=6
strategy("SMA Cross", overlay=true)
```

---

## Anmerkungen

1. Test
"""


class TestParserMinimalvertrag:
    def test_parse_valid_file(self):
        result = parse_hal_backtest(SAMPLE_MD)
        assert result.is_valid
        assert result.strategy_name == "Trendfolge SMA Kreuz"
        assert result.asset == "BYBIT:BTCUSDT.P"
        assert result.timeframe == "4h"
        assert result.period_start == date(2022, 1, 1)
        assert result.period_end == date(2024, 12, 31)
        assert result.net_return_pct == 56.0
        assert result.max_drawdown_pct == -15.0
        assert result.trade_count == 50

    def test_parse_optional_fields(self):
        result = parse_hal_backtest(SAMPLE_MD)
        assert result.sortino_ratio == 1.5
        assert result.profit_factor == 1.8
        assert result.sharpe_ratio == 1.2
        assert result.win_rate_pct == 42.0
        assert result.report_link == "https://trader.dev/report/abc123"
        assert result.direction == "kombiniert"
        assert result.pine_code is not None
        assert "//@version=6" in result.pine_code
        assert result.long_short_breakdown is not None

    def test_parse_parameters(self):
        result = parse_hal_backtest(SAMPLE_MD)
        assert len(result.parameters) >= 2

    def test_missing_required_fields_sets_error(self):
        md = "# Backtest: X\n\n## Ergebnis KPIs\n| KPI | Wert |\n|-----|------|\n"
        result = parse_hal_backtest(md)
        assert not result.is_valid
        assert result.error is not None

    def test_empty_markdown(self):
        result = parse_hal_backtest("")
        assert not result.is_valid

    def test_missing_asset_and_timeframe(self):
        md = """# Backtest: Test

## Ergebnis KPIs
| KPI | Wert |
|-----|------|
| Net Return | 10% |
| Max Drawdown | -5% |
| Total Trades | 20 |
"""
        result = parse_hal_backtest(md)
        assert not result.is_valid
        assert "Asset fehlt" in result.error
        assert "Timeframe fehlt" in result.error

    def test_negative_net_return(self):
        md = """# Backtest: Negativ

## Faktoren
| Faktor | Wert |
|--------|------|
| Asset | BTCUSDT |
| Timeframe | 1d |
| Periode | 2023-01-01 – 2023-12-31 |

## Ergebnis KPIs
| KPI | Wert |
|-----|------|
| Net Return | -30.0% |
| Max Drawdown | -45% |
| Total Trades | 15 |
"""
        result = parse_hal_backtest(md)
        assert result.is_valid
        assert result.net_return_pct == -30.0
        assert result.max_drawdown_pct == -45.0

    def test_direction_long_only(self):
        md = """# Backtest: Long Only

**Richtung:** long-only

## Faktoren
| Faktor | Wert |
|--------|------|
| Asset | ETHUSDT |
| Timeframe | 1d |
| Periode | 2023-01-01 – 2023-12-31 |

## Ergebnis KPIs
| KPI | Wert |
|-----|------|
| Net Return | 20% |
| Max Drawdown | -10% |
| Total Trades | 30 |
"""
        result = parse_hal_backtest(md)
        assert result.is_valid
        assert result.direction == "long-only"

    def test_no_pine_code_no_report(self):
        result = parse_hal_backtest(SAMPLE_MD)
        assert result.pine_code is not None
        assert result.report_link is not None
