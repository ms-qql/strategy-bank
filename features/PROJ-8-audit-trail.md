# PROJ-8: Audit-Trail

## Status: Planned
**Created:** 2026-07-15
**Last Updated:** 2026-07-15

## Dependencies
- Requires: PROJ-3 (Verifizierung und Versionierung) — liefert die unveränderlichen Strategieversionen als Referenz.
- Requires: PROJ-4 (Batch-Konfiguration) — liefert Backtest-Profil und geplante Runs.
- Requires: PROJ-5 (Credit-Gate) — liefert Credit-Maximum und Kontostand-Snapshot.

Die zu speichernden externen trader.dev-Metadaten stammen verbindlich aus `docs/trader-dev-capability-spike.md`. PROJ-6 schreibt seine Laufzeitdaten anschließend in diese persistente Grundlage.

## User Stories
- Als Trader möchte ich zu jedem Ergebnis die exakte Regelversion und Testkonfiguration sehen, um Kennzahlen nachvollziehen zu können.
- Als Trader möchte ich, dass historische Runs bei späteren Änderungen nicht überschrieben werden, um frühere Vergleiche weiterhin belastbar zu haben.
- Als Trader möchte ich Agent-Runtime, Modell und Prompt-Version eines Runs sehen, um Reproduzierbarkeit über Zeit zu beurteilen.

## Acceptance Criteria
- [ ] Jeder Run referenziert dauerhaft und unveränderlich: die eingefrorene Strategieversion, das vollständige Backtest-Profil, Instrument-ID/Timeframe/Zeitraum, Richtungsmodus, Agent-Runtime und Modell, Prompt-/Executor-Version, die verwendete trader.dev-MCP-Aktion (`run_backtest`/`quick_backtest`), verfügbare Engine- und Datenstand-Angaben, Start-, End- und Erstellungszeitpunkt sowie externen Report-Link und rohe strukturierte Antwort (sofern verfügbar).
- [ ] Änderungen an einer Strategie (neue Version) überschreiben keine historischen Run-Datensätze; alte Runs bleiben unverändert einsehbar und weiterhin ihrer ursprünglichen Version zugeordnet.
- [ ] Jeder Audit-Trail-Eintrag ist von der Ergebnisansicht (PROJ-7) aus für den jeweiligen Run direkt aufrufbar.
- [ ] Für jeden Run ist erkennbar, ob es sich um Research-, historisches Holdout- oder echtes Forward-Ergebnis handelt (Herkunft aus PROJ-4).
- [ ] Fehlt die rohe strukturierte Antwort trotz erfolgreichem Run, zeigt der Audit-Trail dies explizit als „Rohantwort nicht verfügbar" statt eines leeren Feldes ohne Erklärung.

## Edge Cases
- Nutzer versucht, einen Audit-Trail-Eintrag zu bearbeiten: nicht möglich, UI bietet ausschließlich Leseansicht für abgeschlossene Runs.
- Zwei Runs teilen sich dieselbe Strategieversion, aber unterschiedliche Backtest-Profile: jeder Run hat einen eigenständigen, vollständigen Audit-Trail-Eintrag, kein gemeinsames „geteiltes" Profilobjekt, das sich rückwirkend ändern könnte.
- Prozessneustart während eines laufenden Runs: nach Fortsetzung (PROJ-6) wird der Audit-Trail nachträglich um End-/Erstellungszeitpunkt vervollständigt, nicht rückwirkend verändert vor dem tatsächlichen Ereignis.
- Export eines Runs ohne Report-Link (siehe PROJ-7 „unvollständig"): Audit-Trail zeigt das Fehlen explizit statt eines Platzhalter-Links.

## Technical Requirements (optional)
- Persistenz: append-only für Run-bezogene Audit-Daten, keine UPDATE-Operationen auf bereits abgeschlossene Runs außer dem einmaligen Nachtragen von End-/Erstellungszeitpunkt bei Prozessfortsetzung.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
