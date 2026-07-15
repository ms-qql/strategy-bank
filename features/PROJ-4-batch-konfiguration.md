# PROJ-4: Batch-Konfiguration

## Status: Planned
**Created:** 2026-07-15
**Last Updated:** 2026-07-15

## Dependencies
- Requires: PROJ-3 (Verifizierung und Versionierung) — nur freigegebene Strategieversionen sind wählbar.

Externe trader.dev-Capabilities und Defaults stammen verbindlich aus `docs/trader-dev-capability-spike.md`.

## User Stories
- Als Trader möchte ich Instrumente, Zeitraum, Timeframe und Richtung für einen Batch auswählen, um mehrere Runs konsistent zu konfigurieren.
- Als Trader möchte ich ein wiederverwendbares Backtest-Profil nutzen, um Runs untereinander vergleichbar zu halten.
- Als Trader möchte ich vor dem Start sehen, welche Runs geplant sind, um die Konfiguration zu prüfen, bevor Credits verbraucht werden.

## Acceptance Criteria
- [ ] Standard-Testuniversum ist vorbelegt: BTC (`BYBIT:BTCUSDT.P`), S&P-500-Proxy (`BYBIT:SPYUSDT.P`), Gold (`XAUUSD`, Polygon Forex) — als exakte Provider-Symbole gespeichert, nicht nur als fachlicher Name.
- [ ] Instrumente, Timeframe und Zeitraum sind pro Batch änderbar; Änderungen werden ebenfalls als exakte Provider-Werte gespeichert.
- [ ] Default-Timeframe: 4 Stunden. Default-Research-Zeitraum: 2021-01-01 bis 2024-12-31.
- [ ] Richtung: Default ist kombinierter Long-/Short-Run. Alternativ pro Batch wählbar: Long-only oder Short-only. Jeder gewählte Richtungsmodus erzeugt einen eigenen Run.
- [ ] Backtest-Profil enthält mindestens: Datenquelle/Provider-Symbol, Zeitzone/Handelssitzung, Signalzeitpunkt (Default: Schlusskurs) und Fill-Zeitpunkt (Default: nächster verfügbarer Bar-Open), Ordertyp, Gebühren (Default 0,06 % pro Order), Slippage (Default 2 Ticks), Startkapital (Default 10.000, Quote-Währung USD), Positionsgröße und Compounding-Regel, Leverage (Default: kein Leverage), Pyramiding (Default: aus) und maximal gleichzeitig offene Positionen (Default: 1), Umgang mit fehlenden Bars und Corporate Actions.
- [ ] Backtest-Profile sind speicherbar und wiederverwendbar über mehrere Batches hinweg.
- [ ] Alle Runs innerhalb eines Vergleichs verwenden dasselbe Backtest-Profil.
- [ ] Vor Bestätigung zeigt die App die vollständige Liste geplanter Runs (Strategieversion × Instrument × Richtungsmodus).
- [ ] Historischer Holdout (ab 2025-01-01 bis `frozen_at` der jeweiligen Version) und echter Forward-Test (ab `frozen_at`) sind als getrennte, nicht im Standard-Batch enthaltene Auswertungen konfigurierbar und dürfen erst nach Einfrieren der Version ausgelöst werden.
- [ ] Daten ab 2025 werden während Extraktion, Regelklärung, Parameterauswahl und Ranking nicht angezeigt oder verwendet.

## Edge Cases
- Nutzer versucht, den historischen Holdout vor der Freigabe der Strategieversion auszuwerten: blockiert mit Hinweis „Holdout erst nach Freigabe der Version verfügbar.".
- Wurde der Holdout-Zeitraum bereits zur Änderung einer Strategie herangezogen, gilt er für die neue Version nicht mehr als unangetasteter Holdout — die App markiert ihn entsprechend als „bereits verwendet".
- trader.dev unterstützt ein gewähltes Instrument/Timeframe/Zeitraum nicht (siehe PROJ-6 Fehlerfall): Batch-Konfiguration erlaubt trotzdem das Anlegen, der betroffene Run wird erst in der Queue (PROJ-6) blockiert, nicht bereits hier — vermeidet stille Symbolersetzung an dieser Stelle.
- Nutzer wählt Long-only und Short-only gleichzeitig für denselben Batch: beides sind unabhängige Runs, kein „kombiniert"-Ersatz.
- Backtest-Profil wird nach Nutzung in einem bereits gestarteten Batch geändert: Änderung erzeugt eine neue Profilversion, laufende/abgeschlossene Runs referenzieren weiterhin die ursprüngliche Profilversion.

## Technical Requirements (optional)
- Backtest-Profil-Defaults stammen aus `docs/trader-dev-capability-spike.md`.
- Persistenz: Batch, Backtest-Profil und geplante Runs sind vor Bestätigung vollständig, aber änderbar; nach Bestätigung unveränderlich (siehe PROJ-8 Audit-Trail).

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
