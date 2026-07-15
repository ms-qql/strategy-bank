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

**Tested:** 2026-07-15
**Backend:** `GET /results` endpoint (FastAPI, TestClient)
**Frontend:** Next.js build (Turbopack, TypeScript)
**Tester:** QA Engineer (AI)

### Acceptance Criteria Status

#### AC-1: Metrik-Anzeige (Net Return %, CAGR %, Trade Count, Max DD %, Sharpe, PF, Calmar, Report-Link)
- [x] Alle Pflichtmetriken in API-Antwort vorhanden (`net_profit_pct`, `cagr_pct`, `trade_count`, `max_drawdown_pct`, `sharpe_ratio`, `profit_factor`, `calmar_ratio`, `report_link`)
- [x] Metriken korrekt typisiert (float | null für nicht verfügbare Werte)
- [x] Report-Link als nullable String, mit report_available flag

#### AC-2: Calmar-Berechnung (CAGR / abs(Max Drawdown))
- [x] Calmar = cagr / abs(mdd) — verifiziert: 3.67 / 12.3 = 0.298..., -1.275 / 20 = -0.06375
- [x] Max Drawdown = 0 → Calmar = null (nicht 0)
- [x] Fehlende Eingangswerte → Calmar = null
- [x] Null-Werte im Frontend als „–" dargestellt, nicht als 0

#### AC-3: Filter (Strategie, Version, Instrument, Kategorie, Richtung, Status)
- [x] Strategie, Instrument, Kategorie, Richtung, Status, Ergebnisart als Dropdown-Filter
- [x] Version-Filter als separates Dropdown (nach QA ergänzt)

#### AC-4: Sortierung nach jeder einzelnen Metrik
- [x] Spaltenheader klickbar (Net Return, CAGR, Trades, Max DD, Sharpe, PF, Calmar)
- [x] Drei-Zustand: desc → asc → none
- [x] null-Werte sortieren konsistent ans Ende

#### AC-5: Niedrige-Aktivitäts-Kennzeichnung (< 24 Trades, Default)
- [x] Backend: `low_activity = true` bei trade_count < 24
- [x] Frontend: Aktivitätsschwelle als Number-Input änderbar
- [x] Frontend: Nur Nutzer-Schwellwert entscheidet (Backend-Flag entfernt, nach QA fix)

#### AC-6: Getrennte Ergebnisarten (Research / Holdout / Forward)
- [x] Jede Ergebnisart eigene Zeile (standard / holdout / forward_test)
- [x] Visuelle Unterscheidung über Badge (Research / Historisches Holdout / Echter Forward-Test)
- [x] Filterbar über Ergebnisart-Dropdown

#### AC-7: Profil-Gruppierung (Warnung bei mehreren Backtest-Profilen)
- [x] Backend liefert `profile_family_id` für Gruppierung
- [x] Frontend gruppiert nach `profile_family_id` in separaten Cards
- [x] Warn-Banner bei mehr als einer Profilgruppe (amber Border)

#### AC-8: Kein Composite Score / keine Gewinner-Markierung
- [x] Kein Scoring-Algorithmus in Backend oder Frontend
- [x] Keine automatische Hervorhebung oder Ranking-Badge

#### AC-9: Fehlender Report-Link → „Unvollständig"-Kennzeichnung
- [x] Backend: `incomplete = true` wenn backtest_result vorhanden, aber report_link fehlt
- [x] Frontend: „Unvollständig"-Badge (orange) bei `hasMetrics && row.incomplete`
- [x] Zeile bleibt sichtbar, Metriken unverändert

### Edge Cases Status

#### EC-1: Run mit Trade Count 0
- [x] Zeile erscheint normal
- [x] Abgeleitete Ratios (Sharpe, PF, Calmar) = null / „–"
- [x] `low_activity = true`

#### EC-2: Sortierung mit „nicht verfügbar"-Werten
- [x] null-Werte sortieren konsistent ans Ende (ascending und descending)

#### EC-3: Leermeldung bei Filter ohne Treffer
- [x] `<SearchX>`-Icon mit Text „Keine Ergebnisse für diese Filterkombination."
- [x] Bei komplett leerer DB: „Keine Runs vorhanden."

#### EC-4: Gleiche Strategie + Instrument, unterschiedliche Richtungen
- [x] Beide Richtungen (kombiniert, long-only) als eigene Zeilen
- [x] Kein automatisches Summieren

#### EC-5: Änderung der Aktivitätsschwelle
- [x] Nur Anzeige betroffen, keine Persistenz

### Security Audit Results
- [x] SQL-Injection: Keine Nutzereingaben im SQL-Query (parameterloser SELECT)
- [x] Authentication: Solo-Nutzer-App, kein Auth-Mechanismus nötig
- [x] Input Validation: Keine Request-Parameter, keine Injection-Vektoren
- [x] Rate Limiting: Read-Only-Endpoint, kein Missbrauchspotential
- [x] Secrets: Keine Secrets im Source oder API-Response

### Bugs Found

_Beide während QA gefundenen Bugs wurden direkt behoben:_

- **BUG-1** (Medium): Version-Filter fehlte → als separates Dropdown ergänzt.
- **BUG-2** (Low): Backend-low_activity-Flag überschrieb Nutzer-Schwellwert → entfernt, nur `trade_count < threshold` entscheidet.

### Summary
- **Acceptance Criteria:** 9/9 passed
- **Edge Cases:** 5/5 passed
- **Bugs Found (QA):** 2 resolved
- **Security:** Pass
- **Production Ready:** YES
- **Recommendation:** Deploy

## Deployment
_To be added by /deploy_
