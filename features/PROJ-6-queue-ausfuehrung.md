# PROJ-6: Queue und trader.dev-Ausführung

## Status: Architected
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
**Erstellt:** 2026-07-15 · **Stack:** Next.js 16 (App Router) + shadcn/ui / FastAPI + raw SQL / PostgreSQL · **Branch:** dev

### A) Komponentenstruktur (UI)

```text
BatchAusfuehrungPage (Erweiterung der bestehenden Batch-Seite)
├── BatchKopf (Status, Gesamtfortschritt, Credit-Snapshot)
├── Fortschrittsanzeige (erfolgreich / fehlgeschlagen / offen)
├── RunTabelle
│   └── RunZeile
│       ├── Strategie, Instrument, Timeframe und Richtung
│       ├── StatusBadge
│       ├── Teilergebnis oder verständlicher Fehlergrund
│       ├── „Abbrechen“ (nur geplant oder bestätigt)
│       └── „Erneut versuchen“ (nur fehlgeschlagen, führt zum Credit-Gate)
└── BatchHinweis (andere Runs laufen trotz Einzelfehler weiter)
```

Die Seite fragt während offener Runs regelmäßig den aktuellen Batch-Zustand ab.
Dadurch erscheinen Fortschritt und Teilergebnisse zeitnah, ohne zusätzliche
Echtzeit-Infrastruktur. Fertige Runs werden sofort angezeigt; die Seite wartet
nicht auf den Abschluss des gesamten Batches.

### B) Datenmodell (Klartext)

```text
runs (ERWEITERT, ein fachlicher Run je Batch-Kombination)
  - unveränderliche Run-Konfiguration aus PROJ-4/5
  - Status: geplant, bestätigt, in_queue, läuft, erfolgreich,
    fehlgeschlagen oder abgebrochen
  - Zeitpunkte der einzelnen Zustandsübergänge
  - verständlicher Fehlergrund und technische Fehlerkategorie
  - Referenz auf genau eine externe Ausführung

backtest_executions (NEU, eine externe Ausführung je Idempotency-Key)
  - eindeutiger Idempotency-Key aus allen auswertungsrelevanten Eingaben
  - vollständiger Pine-Script-v5-Stand
  - trader.dev-Job-ID und spätere Ergebnis-ID
  - interner Versuch: erster Lauf oder einmalige Cascade-Exit-Korrektur
  - Provider-Status, Warnungen und Ergebnisverfügbarkeit
```

Mehrere fachliche Runs mit identischem Idempotency-Key dürfen auf dieselbe
`backtest_executions`-Ausführung und damit dasselbe Ergebnis zeigen. So bleiben
beide Runs im Batch sichtbar, aber nur der erste löst `run_backtest` aus.

PostgreSQL ist zugleich die persistente Queue: bestätigte Runs werden dort
eingereiht und von einem separaten Backend-Worker übernommen. Nach einem
Prozessneustart setzt der Worker nicht abgeschlossene Ausführungen anhand ihrer
gespeicherten Job-ID fort. Die Laufzeit- und Ergebnisdaten werden zusätzlich in
den je Run angelegten Audit-Eintrag aus PROJ-8 übernommen. Dateien fallen nicht
an; MinIO wird nicht benötigt.

### C) API-Form (nur Endpunkte)

```text
POST /batches/{id}/start
    → reiht alle bestätigten Runs des Batches ein

GET /batches/{id}/runs
    → liefert Gesamtfortschritt, Run-Status und verfügbare Teilergebnisse

GET /runs/{id}
    → liefert Status, Fehlergrund und vorhandenes Ergebnis eines Runs

POST /runs/{id}/cancel
    → bricht einen noch nicht gestarteten Run ab

POST /runs/{id}/retry-credit-check
    → prüft die aktuellen Credits für einen bewussten Retry

POST /runs/{id}/retry
    → legt nach bestätigtem Credit-Gate einen neuen fachlichen Retry-Run an
```

Die bestehende Batch-Bestätigung aus PROJ-5 bleibt getrennt vom Start. Ein Retry
verändert den fehlgeschlagenen historischen Run nicht, sondern erzeugt einen
neuen nachvollziehbaren Run mit neuem Credit-Snapshot. Alle trader.dev-Zugriffe
bleiben im Backend; Zugangsdaten und technische Rohfehler erreichen das Frontend
nicht.

### D) Tech-Entscheidungen (warum)

- **PostgreSQL als Queue:** Die Anwendung braucht bereits PostgreSQL und nur eine überschaubare Zahl von Backtests. Eine zusätzliche Redis-/Queue-Plattform würde Betrieb und Fehlerquellen erhöhen, ohne einen MVP-Nutzen zu liefern.
- **Separater Worker-Prozess:** Externe Backtests und Ergebnisabfragen dauern länger als eine HTTP-Anfrage. Der Worker verarbeitet sie unabhängig vom Browser und kann nach Neustarts aus den persistenten Zuständen weiterarbeiten.
- **Eigene externe Ausführung neben dem fachlichen Run:** Der Idempotency-Key beschreibt einen Provider-Aufruf, während im Batch mehrere identische Runs sichtbar sein dürfen. Die Trennung verhindert doppelte Credit-Kosten, ohne Runs zu verschlucken.
- **Datenbankweit eindeutiger Idempotency-Key:** Gleichzeitige Startversuche und Prozessneustarts können dadurch keinen zweiten `run_backtest`-Aufruf für dieselbe Konfiguration erzeugen.
- **Pine-Übersetzung vor dem Provider-Aufruf:** trader.dev akzeptiert ausschließlich vollständigen Pine-v5-Quellcode. Gespeicherter Pine-Stand und Executor-Version machen das Ergebnis später reproduzierbar.
- **Genau eine interne Cascade-Korrektur:** Nur `cascade_exit_pattern` mit `severity: error` erhält automatisch einen zweiten Versuch mit Edge-Trigger. Alle anderen Fehler bleiben sichtbar und benötigen einen bewussten, erneut kostenbestätigten Retry.
- **Polling statt WebSockets:** Kurze regelmäßige Statusabfragen reichen für minutenlange Backtests und funktionieren mit der vorhandenen Next.js-/FastAPI-Struktur. Echtzeit-Infrastruktur ist dafür nicht nötig.
- **Keine stille Symbolersetzung:** Nicht unterstützte Instrumente, Timeframes oder Zeiträume werden als verständlicher Run-Fehler gespeichert; das bewahrt die Vergleichbarkeit.
- **Null statt künstlicher Null-Kennzahl:** Ein erfolgreicher Run ohne Trades behält Trade Count 0, während nicht berechenbare Kennzahlen ausdrücklich als nicht verfügbar gelten.

### E) Abhängigkeiten

- Backend: keine neuen Python-Pakete; vorhandenes FastAPI, Pydantic, PostgreSQL/raw SQL und die bestehende OpenCode-trader.dev-Anbindung genügen.
- Frontend: keine neuen npm-Pakete; vorhandene shadcn/ui-Komponenten und Browser-Timer genügen.
- PROJ-5 liefert Batch-Bestätigung, Credit-Snapshot und das erneute Credit-Gate.
- PROJ-8 liefert den Audit-Eintrag, den PROJ-6 während der Ausführung ergänzt und beim terminalen Status finalisiert.
- trader.dev liefert `run_backtest`, `get_backtest_result`, `get_trades` und `get_equity_curve`.

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
