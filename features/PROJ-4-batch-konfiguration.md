# PROJ-4: Batch-Konfiguration

## Status: In Progress
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
**Erstellt:** 2026-07-15 · **Stack:** Next.js 16 (App Router) + shadcn/ui / FastAPI + raw SQL / PostgreSQL · **Branch:** dev

### A) Komponentenstruktur (UI)
```
BatchesPage (app/batches/page.tsx — neu)
├── ProfilAuswahl (bestehendes Backtest-Profil wählen ODER „Neues Profil")
├── BacktestProfilFormular (bei neu/bearbeiten eines Profils)
│   ├── Ausführung: Zeitzone/Handelssitzung, Signalzeitpunkt, Fill-Zeitpunkt, Ordertyp
│   ├── Kosten: Gebühren, Slippage
│   ├── Kapital: Startkapital, Quote-Währung, Positionsgröße + Compounding-Regel
│   ├── Risiko: Leverage, Pyramiding, max. gleichzeitig offene Positionen
│   └── Datenqualität: Umgang mit fehlenden Bars, Corporate Actions
├── StrategieversionAuswahl (Multi-Select, nur Status „freigegeben")
├── InstrumentAuswahl (vorbelegt: BTC/S&P-Proxy/Gold als Provider-Symbole, editierbar/erweiterbar)
├── ZeitraumUndTimeframe (ein gemeinsamer Timeframe + Zeitraum je Batch; Default 4h, 2021-01-01–2024-12-31)
├── RichtungsmodusAuswahl (Mehrfachauswahl: Kombiniert / Long-only / Short-only)
├── RunVorschau (Tabelle: Strategieversion × Instrument × Richtungsmodus = eine Zeile je Run)
└── Aktionsleiste: „Entwurf speichern" / „Batch bestätigen"

EvaluationsPanel (Ergänzung auf der Versions-Detailseite aus PROJ-3)
├── „Historischen Holdout auswerten" — nur aktiv wenn Version freigegeben UND Holdout für die Familie unverbraucht
└── „Forward-Test starten" — nur aktiv wenn Version freigegeben; Zeitraum startet bei frozen_at, offenes Ende
```

### B) Datenmodell (Klartext)
```
backtest_profiles (append-only, Muster wie strategy_versions aus PROJ-3)
  - family_id, version_number, Name
  - alle Ausführungsfelder aus den Akzeptanzkriterien (Session/Zeitzone, Signal-/Fill-Zeitpunkt,
    Ordertyp, Gebühren, Slippage, Startkapital, Quote-Währung, Positionsgröße/Compounding,
    Leverage, Pyramiding, max. offene Positionen, fehlende Bars, Corporate Actions)
  - sobald von mindestens einem Batch referenziert: gesperrt für UPDATE/DELETE:
    eine Änderung legt eine neue Version derselben family_id an, laufende/abgeschlossene
    Batches behalten ihre ursprüngliche Profilversion.

batches
  - id, backtest_profile_version_id, timeframe, period_start, period_end
  - run_kind: 'standard' | 'holdout' | 'forward_test'
  - status: 'entwurf' | 'bestätigt', confirmed_at, created_at
  - solange 'entwurf': vollständig veränderbar; ab 'bestätigt': gesperrt (Audit-Trail PROJ-8)

batch_instruments (batch_id, provider_symbol, Label)
batch_strategy_versions (batch_id, strategy_version_id)
batch_direction_modes (batch_id, mode: 'kombiniert' | 'long_only' | 'short_only')

runs (NEU, entsteht erst bei „Batch bestätigen")
  - id, batch_id, strategy_version_id, provider_symbol, direction_mode, run_kind, status='geplant'
  - Vor Bestätigung ist die Run-Liste nur eine berechnete Vorschau (Kartesisches Produkt aus
    Strategieversionen × Instrumenten × Richtungsmodi) — keine eigene Persistenz.
  - Nach Bestätigung: append-only, gesperrt für UPDATE/DELETE (gleiche Konvention wie
    strategy_versions). PROJ-6 liest und aktualisiert den Status je Run weiter.

family_holdout_status (NEU, 1 Zeile je family_id)
  - family_id, consumed_at (nullable)
  - wird gesetzt, sobald für diese family_id erstmals ein Holdout-Batch bestätigt wurde;
    gilt dann für alle Versionen derselben Familie als „bereits verwendet".
```

### C) API-Form (nur Endpunkte)
```
GET    /backtest-profiles                         # aktuelle Version je family_id
POST   /backtest-profiles                         # neues Profil (version_number=1)
PATCH  /backtest-profiles/{family_id}              # legt neue Profilversion an, sofern die
                                                   # bisherige bereits in einem Batch verwendet wurde
GET    /backtest-profiles/{family_id}/versions     # Versionshistorie

POST   /batches                                    # Entwurf anlegen (Profil, Instrumente,
                                                   # Timeframe, Zeitraum, Richtungsmodi, Strategieversionen)
PATCH  /batches/{id}                               # Entwurf bearbeiten (nur solange 'entwurf')
GET    /batches/{id}/preview                       # berechnete Run-Liste vor Bestätigung
POST   /batches/{id}/confirm                       # sperrt Entwurf, materialisiert die runs-Zeilen
GET    /batches/{id}                               # Batch inkl. Status lesen

POST   /strategy-versions/{id}/holdout-batch       # Batch mit run_kind='holdout'; 422 wenn
                                                   # Version nicht freigegeben
POST   /strategy-versions/{id}/forward-test-batch  # Batch mit run_kind='forward_test',
                                                   # period_start=frozen_at, period_end=null;
                                                   # 422 wenn Version nicht freigegeben
GET    /strategy-versions/{id}/holdout-status      # unverbraucht/verbraucht für die family_id
```

Status-Codes wie gewohnt: 200/201 Erfolg, 404 nicht gefunden, 422 Gate-Fehler (Version nicht
freigegeben, Holdout bereits verbraucht, Batch bereits bestätigt und trotzdem editiert).

### D) Tech-Entscheidungen (warum)
- **Run-Liste ist vor Bestätigung nur eine Vorschau, keine eigene Tabelle:** Ein Kartesisches
  Produkt aus Strategieversionen × Instrumenten × Richtungsmodi ist beim Lesen billig zu
  berechnen. So tauchen halbfertige Batches nie als „geplante Runs" im Audit-Trail auf.
- **Backtest-Profile sind append-only versioniert wie strategy_versions:** dieselbe Anforderung
  wie bei Strategieversionen (eine Änderung darf laufende/abgeschlossene Runs nicht rückwirkend
  verändern) — bewährtes Muster aus PROJ-3 wiederverwendet statt neu erfunden.
- **Holdout-Status hängt an der family_id, nicht an der einzelnen Version:** Der historische
  Holdout-Zeitraum bezieht sich auf dieselben Marktdaten unabhängig von der Versionsnummer;
  einmal gesehen, bleibt er für alle Nachfolgeversionen dieser Familie verbraucht.
- **Runs sperren erst bei Bestätigung, nicht früher:** deckt sich mit dem Unveränderlichkeits-
  Prinzip aus PROJ-8 und der REVOKE-UPDATE/DELETE-Konvention aus PROJ-3.
- **Ein Timeframe/Zeitraum pro Batch, nicht pro Instrument:** die Spec verlangt, dass alle Runs
  eines Vergleichs unter identischen Bedingungen laufen.
- **Keine Symbol-/Timeframe-Validierung gegen trader.dev in diesem Schritt:** laut Edge Case
  wird ein nicht unterstütztes Instrument erst in der Queue (PROJ-6) blockiert — vermeidet
  stille Symbolersetzung schon in der Batch-Konfiguration.
- **Holdout/Forward-Test als eigener run_kind auf derselben Batch-Struktur:** kein separates
  Datenmodell nötig; das Freigabe-Gate (`frozen_at` gesetzt) entscheidet, ob der jeweilige
  Endpunkt einen Batch anlegen darf.

### E) Abhängigkeiten
- Backend (Python): keine neuen Pakete.
- Frontend (Next.js): keine neue npm-Abhängigkeit. Neu über die shadcn/ui-CLI zu ergänzende
  Komponenten (copy-paste, kein Paket): `select` (Timeframe/Richtungsmodus), `checkbox`
  (Mehrfachauswahl Richtungsmodi), `calendar`/`popover` (Zeitraum). Bestehender Zod-Client
  reicht für Validierung — kein react-hook-form nötig für dieses überschaubare Formular.
- Tests: Kartesisches-Produkt-Vorschau, Bestätigen sperrt Batch/Runs, Profiländerung nach
  Nutzung erzeugt neue Version statt Überschreiben, Holdout-Gate vor Freigabe blockiert,
  Holdout-„bereits verwendet"-Markierung nach erster Nutzung.

## Implementation Notes (Backend)
**Umgesetzt:** 2026-07-15

- `backend/sql/005_batch_konfiguration.sql`: `backtest_profiles` (append-only, gleiches
  Muster wie `strategy_versions`), `batches`, `batch_instruments`,
  `batch_strategy_versions`, `batch_direction_modes`, `runs`, `family_holdout_status`.
  Angewendet auf `strategy_bank`- und `strategy_bank_test`-DB.
- `backend/app/routes/batches.py` + `backend/app/schemas/batches.py`: alle Endpunkte aus
  dem Tech Design (`/backtest-profiles`, `/batches`, `/batches/{id}/preview`,
  `/batches/{id}/confirm`, `/strategy-versions/{id}/holdout-batch`,
  `/strategy-versions/{id}/forward-test-batch`, `/strategy-versions/{id}/holdout-status`).
- Abweichung vom Tech Design: Der 422-Hinweis „Holdout erst nach Freigabe der Version
  verfügbar" ist Frontend-Sache (Button-Disable anhand `draft.status`) — der Endpunkt
  selbst ist bereits über `strategy_version_id` an eine freigegebene Version gebunden,
  ein nicht existierender Wert liefert generisch 404 „Version nicht gefunden."
- Holdout-Verbrauch wird direkt beim Anlegen des Holdout-Batches markiert
  (`family_holdout_status.consumed_at`), nicht erst bei dessen Bestätigung — einfacher,
  ein einziger Schreibpunkt statt Interaktion zwischen Anlage und Bestätigung.
- 12 pytest-Tests in `backend/tests/test_batches.py`: Profil-Versionierung (keine
  Überschreibung), Batch-Vorschau als Kartesisches Produkt, Bestätigen sperrt/materialisiert
  Runs, Holdout-Gate + „bereits verwendet"-Markierung, Forward-Test mit offenem Ende.
  Komplette Suite (`backend/tests`): 74 passed.

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
