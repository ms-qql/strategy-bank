# PROJ-7: Ergebnisvergleich

## Status: Architected
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
**Erstellt:** 2026-07-15 · **Stack:** Next.js 16 (App Router) + shadcn/ui / FastAPI + raw SQL / PostgreSQL · **Branch:** dev

### A) Komponentenstruktur (UI)

```text
ErgebnisvergleichPage
├── Seitenkopf (Titel, Trefferzahl und Aktivitätsschwelle)
├── ErgebnisFilter
│   ├── Strategie und Version
│   ├── Instrument und Kategorie
│   ├── Richtung und Status
│   └── Ergebnisart: Research / historisches Holdout / echtes Forward
├── ProfilVergleichshinweis
│   └── warnt bei mehreren Backtest-Profilen und trennt deren Gruppen
├── ErgebnisGruppe (genau eine Backtest-Profilversion)
│   └── ErgebnisTabelle
│       └── ErgebnisZeile
│           ├── Strategie-, Versions- und Run-Merkmale
│           ├── ErgebnisartBadge und StatusBadge
│           ├── einzeln sortierbare Metrikspalten
│           ├── AktivitätBadge bei Unterschreitung der Schwelle
│           ├── UnvollständigBadge bei fehlendem Report-Link
│           └── Link zum trader.dev-Report, falls vorhanden
└── LeererZustand (keine Ergebnisse für diese Filter)
```

Die Aktivitätsschwelle startet bei 24 Trades und kann direkt auf der Seite
geändert werden. Sie beeinflusst nur die Kennzeichnung der sichtbaren Zeilen;
Run-Daten werden dadurch weder geändert noch neu bewertet.

### B) Datenmodell (Klartext)

PROJ-7 legt keine neue Tabelle an. Die Vergleichsansicht liest und verbindet
bereits vorhandene, unveränderliche Daten:

```text
Jede Vergleichszeile enthält:
  - Run-ID, Strategie-ID, Strategiename, Kategorie und Versionsnummer
  - Instrument, Richtung, Status und Ergebnisart
  - genaue Backtest-Profil-ID, Profilname und Profilversion
  - Testzeitraum
  - Net Return %, CAGR %, Trade Count, Max Drawdown %,
    Sharpe Ratio, Profit Factor und Calmar Ratio
  - trader.dev-Report-Link und Kennzeichen „unvollständig"
```

Run-Status und Ergebnisart stammen aus `runs`. Name, Kategorie und Version
stammen aus dem eingefrorenen Strategie-Snapshot. Das ebenfalls eingefrorene
Backtest-Profil bestimmt, welche Zeilen direkt vergleichbar sind. Die
Provider-Metriken und der Report-Link stammen aus der vorhandenen externen
Backtest-Ausführung.

CAGR wird aus dem Provider-Ergebnis übernommen. Fehlt CAGR dort, wird sie aus
Net Return und dem exakten Testzeitraum abgeleitet. Calmar wird zentral als
`CAGR / abs(Max Drawdown)` bereitgestellt. Fehlt ein Eingangswert oder ist Max
Drawdown 0, bleiben CAGR beziehungsweise Calmar ausdrücklich „nicht verfügbar“.
Bei Trade Count 0 werden auch nicht berechenbare Ratios nicht künstlich zu 0.

### C) API-Form (nur Endpunkte)

```text
GET /results
    → liefert alle Runs als vergleichsfertige Zeilen mit Strategie-, Profil-,
      Ergebnisart-, Metrik- und Report-Informationen
```

Der Endpunkt liefert auch noch laufende, fehlgeschlagene und abgebrochene Runs,
damit der Statusfilter vollständig funktioniert. Metriken bleiben dort nicht
verfügbar, solange kein gültiges Ergebnis vorliegt. Die MVP-Menge wird in einem
Abruf geliefert; Filter und Einzelsortierung erfolgen anschließend im Browser.

### D) Tech-Entscheidungen (warum)

- **Eigene Ergebnisansicht statt Ausbau einer Batch-Tabelle:** Der Vergleich umfasst Runs aus mehreren Batches, Zeiträumen und Ergebnisarten. Eine globale Ansicht erfüllt diesen Zweck, ohne die Ausführungsansicht mit fachfremden Filtern zu überladen.
- **Eine Lese-API statt mehrerer Browser-Abfragen:** Strategie-, Profil- und Providerdaten werden im Backend zu einer eindeutigen Zeile verbunden. Das verhindert widersprüchliche Kennzahlen und hält die UI einfach.
- **Keine neue Ergebnistabelle:** Alle benötigten Rohdaten und Snapshots existieren bereits. Eine weitere Kopie könnte veralten und würde keinen zusätzlichen MVP-Nutzen bringen.
- **CAGR- und Calmar-Normalisierung im Backend:** Abgeleitete Kennzahlen folgen dadurch überall denselben Null- und Berechnungsregeln. Die UI zeigt nur den fachlichen Zustand an.
- **Clientseitige Filterung und Einzelsortierung:** Für den Solo-Nutzer und die erwartete Anzahl unter einigen tausend Runs ist ein einmaliger Abruf einfacher und ausreichend schnell. Nicht verfügbare Metriken stehen bei auf- und absteigender Sortierung konsistent am Ende.
- **Strikte Trennung der Ergebnisarten:** `standard`, `holdout` und `forward_test` werden als Research, historisches Holdout und echtes Forward angezeigt und gefiltert. Jede Ausführung bleibt eine eigene Zeile; es gibt keine Vermischung oder Summierung.
- **Gruppierung nach exakter Backtest-Profilversion:** Nur Runs mit derselben Profilversion stehen in derselben Vergleichsgruppe. Bei mehreren Profilen erklärt ein Warnhinweis, warum die Gruppen nicht unmittelbar gleichwertig sind.
- **Aktivitätskennzeichnung ohne Qualitätsurteil:** „Niedrige Aktivität“ beschreibt ausschließlich die Unterschreitung der gewählten Trade-Schwelle und behauptet weder Signifikanz noch Strategiequalität.
- **Fehlender Report-Link entwertet Metriken nicht:** Die Zeile bleibt sichtbar und erhält „unvollständig“, damit vorhandene Ergebnisse nicht verloren gehen und die Datenlücke transparent bleibt.
- **Keine Rangliste:** Es gibt weder Composite Score noch Gewinner-Markierung; Nutzer vergleichen die einzelnen Metriken selbst.
- **Kein MinIO:** Der Vergleich verwendet strukturierte Daten und externe Links, aber keine hochzuladenden Dateien.

### E) Abhängigkeiten

- Backend: keine neuen Python-Pakete; vorhandenes FastAPI, Pydantic und PostgreSQL/raw SQL genügen.
- Frontend: keine neuen npm-Pakete; vorhandenes Next.js, Zod und shadcn/ui genügen.
- PROJ-6 liefert Run-Status, Provider-Ergebnis und Report-Verweis.
- PROJ-8 liefert die unveränderlichen Strategie- und Backtest-Profil-Snapshots.

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
