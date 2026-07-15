# PROJ-7: Ergebnisvergleich

## Status: Planned
**Created:** 2026-07-15
**Last Updated:** 2026-07-15

## Dependencies
- Requires: PROJ-6 (Queue und trader.dev-Ausführung) — liefert abgeschlossene Run-Ergebnisse.

## User Stories
- Als Trader möchte ich Kernmetriken aller Runs in einer Tabelle sehen, um Strategien objektiv zu vergleichen.
- Als Trader möchte ich nach Strategie, Instrument, Kategorie, Richtung und Status filtern, um gezielt Teilmengen zu betrachten.
- Als Trader möchte ich Research-, historische Holdout- und echte Forward-Ergebnisse klar getrennt sehen, um keine Holdout-Daten fälschlich als Research-Bestätigung zu lesen.

## Acceptance Criteria
- [ ] Pro erfolgreichem Run werden mindestens angezeigt: Net Return %, CAGR %, Trade Count, Max Drawdown %, Sharpe Ratio, Profit Factor, Calmar Ratio, trader.dev-Report-Link.
- [ ] Calmar Ratio wird als `CAGR / abs(Max Drawdown)` berechnet. Ist Max Drawdown 0 oder fehlt ein Eingangswert, wird Calmar als „nicht verfügbar" angezeigt, nie als 0 oder mit Platzhalterwert ersetzt.
- [ ] Ergebnistabelle unterstützt Filter nach Strategie, Version, Instrument, Kategorie, Richtung und Status.
- [ ] Ergebnistabelle unterstützt Sortierung nach jeder einzelnen Metrik (keine Mehrfachsortierung nötig).
- [ ] Runs mit weniger als 24 Trades im vierjährigen Gesamtzeitraum (Default, nutzerseitig änderbar) werden als „niedrige Aktivität" gekennzeichnet — ausdrücklich ohne Aussage über statistische Signifikanz.
- [ ] Research-, historisches Holdout- und echtes Forward-Ergebnis derselben Strategieversion sind visuell und in Filtern eindeutig unterscheidbar, nie in derselben Zeile vermischt.
- [ ] Runs mit unterschiedlichen Backtest-Profilen werden in der UI nicht als gleichwertig nebeneinander dargestellt (z. B. Warnhinweis oder getrennte Gruppierung), sondern erkennbar als nicht direkt vergleichbar markiert.
- [ ] Kein Composite Score, keine automatische Gewinner-Kennzeichnung wird berechnet oder angezeigt.
- [ ] Fehlt der Report-Link trotz vorhandener Metriken, bleibt das Ergebnis sichtbar und wird zusätzlich als „unvollständig" markiert.

## Edge Cases
- Run mit Trade Count 0: Zeile erscheint, alle abgeleiteten Ratios zeigen „nicht verfügbar" statt 0 oder leer ohne Erklärung.
- Nutzer sortiert nach Sharpe Ratio, mehrere Runs haben „nicht verfügbar": diese werden konsistent ans Ende (oder klar markiert an den Anfang) sortiert, nie zufällig gemischt mit numerischen Werten.
- Nutzer filtert nach einer Kombination, die keine Treffer liefert: klare Leermeldung statt leerer Tabelle ohne Erklärung.
- Zwei Runs derselben Strategieversion und desselben Instruments, aber unterschiedlicher Richtungsmodi (Long-only, Short-only): beide erscheinen als eigene Zeilen, kein automatisches Aufsummieren zu einem „kombiniert"-Wert.
- Änderung des Mindestaktivitäts-Schwellwerts durch den Nutzer: wirkt nur auf die Anzeige, verändert keine gespeicherten Run-Daten.

## Technical Requirements (optional)
- Performance: Filter/Sortierung clientseitig ausreichend für MVP-Datenmengen (Solo-Nutzer, keine Paginierung über tausende Runs zu erwarten).
- Alle Beschriftungen und Statushinweise auf Deutsch.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
