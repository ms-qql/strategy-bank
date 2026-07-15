# trader.dev Capability-Spike

**Stand:** 2026-07-15  
**Status:** Verbindliche MVP-Arbeitsgrundlage

Dieses Dokument ist die zentrale Quelle für externe trader.dev-Capabilities in den Feature-Dokumenten. Die Annahmen zu Credits werden für den MVP akzeptiert und in P1 erneut geprüft.

## Bestätigte MVP-Grundlage

- Backtests erhalten vollständigen Pine-Script-v5-Quellcode über `run_backtest`; Ergebnisse werden über `get_backtest_result` abgefragt.
- Standardinstrumente: `BYBIT:BTCUSDT.P`, `BYBIT:SPYUSDT.P` und `XAUUSD` (Polygon Forex).
- Arbeitsdefaults: 0,06 % Gebühren pro Order, 2 Ticks Slippage und 10.000 USD Startkapital.
- Für die MVP-Planung gilt ein Credit pro Run und ein Free-Tier-Budget von 1.000 Credits pro Woche.
- Der Credit-Stand wird über `get_credits` abgefragt.
- Backtests können öffentlich sichtbar sein. Der Nutzer verantwortet, nur dafür zulässige Strategien einzureichen; ein Privacy-Gate ist nicht Teil des MVP.
- Ein `cascade_exit_pattern` mit `severity: error` kennzeichnet eine ungültige Pine-Exit-Übersetzung.
- Detaildaten können über `get_trades` und `get_equity_curve` anhand der Ergebnis-ID abgefragt werden.

## P1-Prüfung

- Tatsächliche Credit-Kosten je verwendeter MCP-Aktion erneut messen.
- Free-Tier-Menge und Reset-Zeitraum erneut prüfen.

