# PROJ-6: Queue und trader.dev-Ausführung

## Status: Planned
**Created:** 2026-07-15
**Last Updated:** 2026-07-15

## Dependencies
- Requires: PROJ-5 (Credit-Gate) — liefert den bestätigten, kostenfreigegebenen Batch.
- Requires: PROJ-8 (Audit-Trail) — liefert die persistente Grundlage für Zustände, externe Job-IDs und Reproduktionsdaten.

Externe trader.dev-Tools und Fehlermeldungen stammen verbindlich aus `docs/trader-dev-capability-spike.md`.

## User Stories
- Als Trader möchte ich, dass jeder Run idempotent ausgeführt wird, um keine doppelten Credits durch technische Fehler zu verlieren.
- Als Trader möchte ich Fortschritt und Teilergebnisse eines Batches sehen, ohne auf den letzten Run warten zu müssen.
- Als Trader möchte ich bei fehlerhafter Regel-zu-Pine-Übersetzung eine korrigierte Wiederholung statt eines stillschweigend falschen Ergebnisses.

## Acceptance Criteria
- [ ] Jeder Run durchläuft genau die Zustandsfolge `geplant → bestätigt → in_queue → läuft → erfolgreich | fehlgeschlagen | abgebrochen`.
- [ ] Vor der externen Ausführung übersetzt die App die kanonische Entry-/Exit-Regel der freigegebenen Strategieversion in Pine Script v5 (trader.dev akzeptiert ausschließlich vollständigen Pine-Source-Code, kein deklaratives Regelformat).
- [ ] Jeder Run erhält einen Idempotency-Key aus Strategieversions-ID, Instrument, Timeframe, Zeitraum, Richtungsmodus, Backtest-Profilversion und Auswertungsart; derselbe Key darf keinen zweiten externen `run_backtest`-Aufruf auslösen.
- [ ] Runs werden über `run_backtest` (asynchron, mit `get_backtest_result`) ausgeführt, nicht über `quick_backtest` — Pflicht für nachvollziehbaren `jobId`-Lebenszyklus.
- [ ] Meldet die trader.dev-Antwort ein `cascade_exit_pattern`-Warning mit `severity: error`, wird der Run als fehlgeschlagen markiert, die Pine-Übersetzung korrigiert (Edge-Trigger statt Dauerfeuer-`strategy.close()`) und automatisch einmal neu ausgeführt, bevor der Nutzer eine Fehlermeldung sieht.
- [ ] Ein Fehler in einem Run stoppt nicht automatisch den gesamten Batch; andere Runs laufen weiter.
- [ ] Fehlgeschlagene Runs zeigen einen für den Nutzer verständlichen Fehlergrund (kein reiner Stacktrace).
- [ ] Ein Retry eines fehlgeschlagenen Runs ist eine bewusste Nutzeraktion, durchläuft erneut das Credit-Gate (PROJ-5) und darf erneut Credits verbrauchen.
- [ ] Ein noch nicht gestarteter Run (Status `geplant` oder `bestätigt`) kann vom Nutzer abgebrochen werden.
- [ ] trader.dev unterstützt ein gewähltes Instrument/Timeframe/Zeitraum nicht (z. B. „no bars"-Fehler): Run wird vor bzw. bei erster externer Ausführung blockiert bzw. als fehlgeschlagen markiert — keine stille Symbolersetzung.
- [ ] Die Batch-Ansicht zeigt laufenden Fortschritt (Anzahl erfolgreich/fehlgeschlagen/offen) und bereits verfügbare Teilergebnisse, ohne auf den Abschluss aller Runs zu warten.
- [ ] Nach einem Prozessneustart wird die Verarbeitung anhand persistierter Zustände fortgesetzt (kein Verlust von `in_queue`/`läuft`-Runs).

## Edge Cases
- Externer Timeout oder Teilfehler bei `get_backtest_result`: Run-Status `fehlgeschlagen`, kein stiller automatischer Retry außer der einmaligen Cascade-Exit-Korrektur.
- Keine Trades im Ergebnis: Run gilt als erfolgreich mit Trade Count 0; abgeleitete Kennzahlen (Sharpe, Profit Factor, Calmar) werden als nicht verfügbar behandelt statt künstlich auf 0 gesetzt.
- Cascade-Exit-Korrektur schlägt auch im zweiten Versuch fehl: Run bleibt `fehlgeschlagen`, Fehlertext nennt explizit „Regel nicht automatisch zuverlässig in Pine übersetzbar" statt eines generischen API-Fehlers.
- Zwei Runs mit derselben Strategieversions-ID und identischer Run-Konfiguration werden im selben Batch angelegt: der zweite Run nutzt denselben Idempotency-Key, löst keinen zweiten externen Aufruf aus und referenziert dasselbe Ergebnis.
- Abbruch eines bereits `läuft`-Runs: nicht möglich im MVP (nur `geplant`/`bestätigt` abbrechbar) — Nutzer muss Abschluss oder Fehlschlag abwarten.
- Report-Link fehlt trotz erfolgreicher Metriken in der Antwort: Ergebnis bleibt sichtbar, wird aber als unvollständig markiert (siehe PROJ-7).

## Technical Requirements (optional)
- MCP-Aufrufe: `run_backtest`, `get_backtest_result`, `get_trades`, `get_equity_curve` (mit `result.id`, nicht `jobId`).
- Persistenz muss Zwischenzustände (`in_queue`, `läuft`) und Idempotency-Keys überstehen, um nach Neustart fortsetzbar zu sein.
- Security: trader.dev-API-Key nie im Frontend oder in Logs.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
