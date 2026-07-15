# PROJ-4: Batch-Konfiguration

## Status: Deployed
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

## Implementation Notes (Frontend)
**Umgesetzt:** 2026-07-15

- `nextjs_app/app/batches/page.tsx`: Batch-Konfigurationsseite — Backtest-Profil
  wählen/anlegen, Strategieversionen (Multi-Select), Instrumente (editierbare
  Tabelle, vorbelegt mit BTC/S&P-Proxy/Gold), Zeitraum & Timeframe,
  Richtungsmodus (Mehrfachauswahl), Run-Vorschau (Kartesisches Produkt),
  Entwurf speichern / Batch bestätigen.
- `nextjs_app/app/entwuerfe/[id]/page.tsx`: `EvaluationsPanel`-Ergänzung im
  Versions-Detail — Backtest-Profil wählen, „Historischen Holdout auswerten"
  (deaktiviert sobald `holdout-status` `consumed` meldet) und „Forward-Test
  starten"; beide erzeugen einen Batch über die Spezial-Endpunkte und leiten
  zu `/batches?batch={id}` weiter. „Batch starten"-Button je Version leitet
  zu `/batches?version={id}` (Strategieversion vorausgewählt).
- `/batches` lädt bei `?batch={id}` einen bestehenden (auch nicht-standard)
  Batch vollständig nach (Profil, Versionen, Instrumente, Zeitraum,
  Richtungsmodi, Vorschau) und zeigt den `run_kind` als eigenes Badge.
  Zeitraum-Felder sind für Holdout/Forward-Test schreibgeschützt (Daten
  stammen vom Server: 2025-01-01–`frozen_at` bzw. `frozen_at`–offen) und ohne
  die 2024-12-31-Obergrenze der Standard-Batches.
- Abweichung vom Tech Design: `select`/`calendar`/`popover` aus shadcn/ui
  wurden nicht ergänzt — natives `<select>` (vorhandene `SelectField`) und
  `<input type="date">` decken den Bedarf ohne zusätzliche Abhängigkeit.
- Backend-Ergänzung `GET /versions` (`backend/app/routes/drafts.py` +
  `VersionSummary`-Schema in `backend/app/schemas/drafts.py`): listet alle
  freigegebenen Strategieversionen familienübergreifend für die
  Versionsauswahl in der Batch-Konfiguration; Test in
  `backend/tests/test_batches.py::TestListAllVersions`.
- Manuell gegen laufenden Stack verifiziert (Backend auf Testport, echte
  Postgres-DB, Playwright-Smoke ohne Console-Errors): Version einfrieren →
  Holdout-Batch anlegen → Vorschau (3 Runs) → Batch bestätigen → Status
  „bestätigt"; erneuter Holdout-Versuch danach korrekt deaktiviert
  („bereits verwendet"). Testdaten anschließend wieder entfernt.
- `npx tsc --noEmit` sauber; `npm run lint` zeigt nur zwei vorbestehende,
  projektweite Findings (`react-hooks/set-state-in-effect` beim
  `loadInitial()`/`loadDraft()`-Muster, ungenutzter `Parameter`-Import),
  keine davon durch diese Änderung eingeführt.

## QA Test Results
**Getestet:** 2026-07-15 · **Tester:** QA Engineer / Red-Team · **Ergebnis: NOT READY (1 High, 2 Medium)**

### Setup
- Backend gegen echte Postgres-DB auf separatem Testport (8010), Frontend (Next.js Dev) via
  Rewrite-Proxy gegen diesen Port, `BACKEND_URL`/`NEXT_PUBLIC_API_URL=/api` temporär umgestellt.
- Automatisierte Suite zuerst: `conda run -n Dashboard --no-capture-output python -m pytest
  backend/tests` → **75/75 passed**, keine Regression in PROJ-1/2/3.
- Manuelle Tests: `curl` gegen jeden Endpunkt aus dem Tech Design + Playwright-Skripte gegen die
  laufende UI (XSS-Payload, Tastatur-Dateneingabe, Responsive 375/768/1440, Fehler-Alerts).
- Testdaten (Quellen, Entwürfe, Versionen, Profile, Batches) nach dem Lauf vollständig aus der
  Dev-DB entfernt; Dev-Server gestoppt, `.env.local` zurückgesetzt.

### Acceptance Criteria
| # | Kriterium | Ergebnis |
|---|---|---|
| 1 | Standard-Testuniversum vorbelegt (BTC/S&P-Proxy/Gold, exakte Provider-Symbole) | ✅ PASS |
| 2 | Instrumente/Timeframe/Zeitraum änderbar, exakte Provider-Werte gespeichert | ✅ PASS |
| 3 | Default-Timeframe 4h, Default-Zeitraum 2021-01-01–2024-12-31 | ✅ PASS |
| 4 | Richtung: Default kombiniert; Long-only/Short-only wählbar, je ein eigener Run | ✅ PASS |
| 5 | Backtest-Profil-Felder + Defaults (Gebühren 0,06 %, Slippage 2 Ticks, Startkapital 10.000 USD, kein Leverage, Pyramiding aus, max. 1 offene Position, …) | ✅ PASS |
| 6 | Backtest-Profile speicherbar/wiederverwendbar über mehrere Batches | ✅ PASS |
| 7 | Alle Runs eines Vergleichs nutzen dasselbe Backtest-Profil | ✅ PASS |
| 8 | Vollständige Run-Vorschau vor Bestätigung (Kartesisches Produkt) | ✅ PASS |
| 9 | Holdout (2025-01-01–`frozen_at`) und Forward-Test (`frozen_at`–offen) getrennt, nur nach Freigabe auslösbar | ✅ PASS (mit dokumentierter Abweichung: generisches 404 statt spezifischer 422-Meldung, siehe Implementation Notes Backend) |
| 10 | Daten ab 2025 werden nicht in Extraktion/Regelklärung/Parameterauswahl/Ranking verwendet | ❌ **FAIL — siehe Bug 1** (Standard-Batches können unbemerkt Daten ab 2025 einschließen) |

**8/9 vollständig bestanden, 1 mit dokumentierter Abweichung (kein Bug), 1 fehlgeschlagen.**

### Edge Cases
| Edge Case | Ergebnis |
|---|---|
| Holdout vor Freigabe der Version | ✅ Blockiert (404 „Version nicht gefunden" statt spezifischem Text — Abweichung bereits in Implementation Notes dokumentiert, kein neuer Bug) |
| Holdout-Zeitraum nach erster Nutzung als „bereits verwendet" markiert (`family_holdout_status`) | ✅ PASS — pro `family_id` isoliert, zweiter Versuch → 422 |
| Long-only + Short-only gleichzeitig gewählt | ✅ PASS — zwei unabhängige Runs, kein „kombiniert"-Ersatz |
| trader.dev-Validierung von Instrument/Timeframe erst in der Queue (PROJ-6) | N/A — PROJ-6 noch nicht gebaut; Batch-Konfiguration lässt beliebige Symbole zu (spec-konform) |
| Profiländerung nach Nutzung in einem Batch → neue Version, laufender Batch behält Original | ✅ PASS |

### Bugs

**Bug 1 — High — Standard-Batches können Daten ab 2025 enthalten (verletzt AC 10)**
- Weder `POST /batches` noch `PATCH /batches/{id}` erzwingen serverseitig eine Obergrenze für
  `period_end` bei `run_kind='standard'`. Das `max="2024-12-31"`-Attribut auf
  `<input type="date">` im Frontend (`nextjs_app/app/batches/page.tsx`) schützt nicht wirklich,
  da die Seite kein natives `<form>`-Submit nutzt — Tastatureingabe umgeht die Browser-Grenze
  vollständig, der Wert landet unverändert im React-State und wird an die API gesendet.
- Repro (Backend): `curl -X POST http://localhost:8010/batches -d
  '{"backtest_profile_id": "...", "strategy_version_ids": ["..."], "period_end": "2025-06-01"}'`
  → `201`, Batch wird mit `period_end=2025-06-01` angelegt (erwartet: 422 oder serverseitige
  Kappung auf `DEFAULT_PERIOD_END`).
- Repro (UI): `/batches` öffnen → Feld „Bis" per Tastatur auf `2026-03-15` setzen → Wert wird
  übernommen (Playwright bestätigt: `inputValue()` nach `fill()` == `2026-03-15`, kein Validierungs-
  Feedback).
- Auswirkung: Ein Standard-Batch (dessen Ergebnisse potenziell fürs Ranking verwendet werden)
  kann unbemerkt Marktdaten aus dem für Holdout/Forward-Test reservierten Zeitraum einschließen
  — genau das Look-ahead-/Kontaminations-Risiko, das die Trennung Standard/Holdout/Forward-Test
  laut Spec verhindern soll.
- Empfehlung: serverseitig in `_create_batch`/`update_batch` (`backend/app/routes/batches.py`)
  `period_end` für `run_kind='standard'` auf `<= DEFAULT_PERIOD_END` validieren (422 bei
  Verstoß), zusätzlich zur kosmetischen Frontend-Grenze.

**Bug 2 — Medium — `POST /batches` ersetzt explizit leere `instruments`/`direction_modes` silently durch Defaults**
- `backend/app/routes/batches.py`, `_create_batch()`: `resolved_instruments = instruments or
  [...]` und `resolved_modes = direction_modes or ["kombiniert"]` behandeln eine leere Liste
  (`[]`) identisch zu `None` (Python-Falsy-Falle). `PATCH /batches/{id}` macht es dagegen richtig
  (`if body.instruments is not None: …`) — die zwei Pfade verhalten sich bei identischem Input
  inkonsistent.
- Repro: `curl -X POST http://localhost:8010/batches -d '{"backtest_profile_id": "...",
  "strategy_version_ids": ["..."], "instruments": [], "direction_modes": []}'` → Response enthält
  trotzdem die 3 Default-Instrumente und `["kombiniert"]`.
- Repro (UI): `/batches` → alle Instrumente über „×" entfernen → „Entwurf speichern" (bei noch
  nicht zuvor gespeichertem Batch, also POST-Pfad) → Vorschau zeigt wieder 3 Default-Runs, ohne
  Hinweis, dass die eigene Auswahl verworfen wurde.
- Auswirkung: kein Datenverlust (`confirm_batch` blockt weiterhin leere Batches korrekt mit 422),
  aber stiller Verstoß gegen die explizite Nutzerabsicht bei der Erstanlage.
- Empfehlung: `instruments is None` statt Truthy-Check in `_create_batch()`; ggf. zusätzlich
  frontendseitige Pflichtfeld-Validierung analog zur bestehenden „mindestens eine
  Strategieversion"-Prüfung.

**Bug 3 — Medium — Profil-Dropdown zeigt beim Laden eines Batches die falsche (neueste) Profilversion an**
- Beim Laden eines bestehenden Batches über `/batches?batch={id}` wird das „Vorhandenes
  Profil"-Dropdown aus `GET /backtest-profiles` befüllt, das nur die jeweils **neueste** Version
  je `family_id` liefert. Referenziert der geladene Batch eine ältere (bereits durch Bearbeitung
  ersetzte) Profilversion — der in der Spec explizit vorgesehene Fall „Backtest-Profil wird nach
  Nutzung geändert" —, fehlt die passende `<option>`; der Browser stellt visuell trotzdem die
  einzige vorhandene (neuere) Option als ausgewählt dar.
- Repro: Profil v1 anlegen → in Batch A verwenden → Profil bearbeiten (v2 entsteht) → Batch A per
  `/batches?batch={id}` erneut öffnen → Dropdown zeigt „… (v2)" an, obwohl `batch.
  backtest_profile_id` weiterhin auf v1 zeigt (bestätigt per `select.inputValue()` in
  Playwright: entspricht der v2-ID, nicht der tatsächlich geladenen `selectedProfileId`).
- Auswirkung: keine Datenkorruption — solange der Nutzer das Dropdown nicht anfasst, bleibt der
  React-State (und damit ein „Entwurf speichern") korrekt auf v1. Der Nutzer wird jedoch visuell
  über die tatsächlich verwendete Profilversion getäuscht, was das Vertrauen in genau die
  Versionierungs-Garantie untergräbt, die dieser Edge Case explizit sicherstellen soll.
- Empfehlung: Für den Lade-Fall die tatsächlich referenzierte Profilversion (z. B. via
  `GET /backtest-profiles/{family_id}/versions`) statt der family-weiten „nur neueste"-Liste ins
  Dropdown aufnehmen, oder die historische Version als zusätzliche Option anzeigen/kennzeichnen.

### Weitere Beobachtungen (nicht blockierend)
- `refreshPreview()` in `nextjs_app/app/batches/page.tsx` schluckt jeden Fehler still
  (`catch { setPreview([]) }`) — bei einem echten Netzwerkfehler sieht der Nutzer nur eine leere
  Vorschau ohne Fehlermeldung. Low.
- Neuer Endpunkt `GET /versions` hat kein `limit`/`offset` — entspricht dem bereits bestehenden
  Muster von `/backtest-profiles` und `/drafts/{id}/versions` in diesem Solo-Nutzer-Tool, keine
  neue Regression. Low/informativ.

### Security-Audit (Red-Team)
- **Tenant-Isolation:** N/A — Projekt ist laut `backend/app/main.py`-Docstring bewusst
  Solo-Nutzer ohne Mandant/RLS/Auth; kein JWT, keine `/login`-Route vorhanden.
- **SQL-Injection:** geprüft mit `provider_symbol = "'; DROP TABLE batches; --"` — alle Queries
  parametrisiert, Payload landet unverändert als Text in der DB, keine Ausführung. PASS.
- **XSS:** geprüft mit `label = "<script>alert(1)</script>"` in Instrument-Label, dargestellt in
  Instrumente-Tabelle und Run-Vorschau — React escaped korrekt, Payload erscheint als Text, kein
  `dangerouslySetInnerHTML` im Pfad, kein Dialog ausgelöst. PASS.
- **Eingabevalidierung:** ungültiger Richtungsmodus, unbekannte `strategy_version_id`/
  `backtest_profile_id`, leere `strategy_version_ids` → jeweils korrekt 422 mit generischer
  deutscher Fallback-Meldung im Frontend (rohe Pydantic-Fehlerliste erreicht den Nutzer nicht,
  da `apiUrl`-Handler nur `detail: string` durchreicht). PASS.
- **Rate-Limiting/Auth-Bypass:** N/A, keine Auth-Endpunkte in diesem Feature.
- **Secrets-Exposure:** keine Secrets in API-Fehlerantworten oder Frontend-Bundle beobachtet.

### Regressionstests
- Volle Suite (`backend/tests`, 75 Tests inkl. PROJ-1/2/3) grün — keine Regression durch PROJ-4
  Frontend-Änderungen oder die neue `GET /versions`-Route.
- Keine zusätzlichen Tests in dieser Runde ergänzt: die bestehende `test_batches.py`-Suite (23
  Tests) deckt bereits jedes bestandene Akzeptanzkriterium ab; die drei gefundenen Bugs werden
  hier dokumentiert statt durch einen absichtlich rot bleibenden Test im Suite-Lauf festgehalten
  (kein Fix durch QA — siehe Regeln).

### Nachtest nach Bugfixes (2026-07-15)
- **Bug 1 behoben:** `POST` und `PATCH /batches` weisen Standard-Zeiträume nach dem
  2024-12-31 mit 422 zurück.
- **Bug 2 behoben:** Nur fehlende Listen erhalten Defaults; explizite leere Instrumente und
  Richtungsmodi bleiben leer.
- **Bug 3 behoben:** Beim Laden eines Batches lädt das Dropdown dessen referenzierte,
  gegebenenfalls historische Profilversion nach.
- Regression: `pytest -q` → **80 passed**; `npm run build` → **passed**.

### Production-Ready-Empfehlung: **READY**
Alle Akzeptanzkriterien bestehen nach dem Nachtest. Status auf **Approved** gesetzt.

## Deployment
__Deployed 2026-07-15__ / **Version:** v0.2.0 / **Stack:** Next.js standalone + FastAPI + PostgreSQL 16 auf Dokploy
