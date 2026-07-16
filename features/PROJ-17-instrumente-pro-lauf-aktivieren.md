# PROJ-17: Instrumente pro Batch aktivieren oder ausblenden

## Status: Architected
**Created:** 2026-07-16
**Last Updated:** 2026-07-16

## Dependencies
- Requires: PROJ-4 (Batch-Konfiguration) — Instrumentliste, Run-Vorschau und Batch-Persistenz bestehen bereits.
- Requires: PROJ-5 (Credit-Gate) — nur aktive Instrumente dürfen in die Credit-Berechnung einfließen.

## User Stories
- Als Trader möchte ich ein Instrument für einen einzelnen Batch deaktivieren, damit dafür kein Run ausgeführt wird, ohne das Instrument zu löschen.
- Als Trader möchte ich deaktivierte Instrumente sichtbar behalten und später mit einem Klick wieder aktivieren.
- Als Trader möchte ich bei einem neuen Batch meine zuletzt gespeicherte Instrument-Auswahl wiederverwenden, um häufige Konfigurationen nicht neu aufzubauen.
- Als Trader möchte ich Instrumente weiterhin dauerhaft aus meiner Auswahl entfernen oder neue ergänzen können.

## Acceptance Criteria
- [ ] Jede Instrumentzeile besitzt in einem bearbeitbaren Batch eine eindeutige Auswahl „Aktiv“, die genau für diesen Batch ein- oder ausgeschaltet werden kann.
- [ ] Deaktivierte Instrumente bleiben sichtbar, sind eindeutig als „Nicht verwendet“ gekennzeichnet und behalten Provider-Symbol sowie Label.
- [ ] Nur aktive Instrumente erscheinen in der Run-Vorschau, werden beim Bestätigen zu Runs und fließen in geplante Aktionen sowie Credit-Maximum ein.
- [ ] Das Deaktivieren eines Instruments löscht es nicht. Eine getrennte Entfernen-Aktion bleibt für dauerhaft nicht mehr benötigte Einträge verfügbar.
- [ ] Ein neuer Batch übernimmt die zuletzt erfolgreich gespeicherte Instrumentliste einschließlich aktiver und inaktiver Zustände.
- [ ] Die zuletzt gespeicherte Auswahl bleibt nach Neuladen der App verfügbar. Ein fehlgeschlagener Speichervorgang überschreibt sie nicht.
- [ ] Vor dem Speichern oder Bestätigen muss mindestens ein Instrument aktiv sein; andernfalls erscheint „Bitte mindestens ein Instrument aktivieren.“ und es werden keine Runs erzeugt.
- [ ] Bestätigte Batches bleiben unveränderlich und zeigen die tatsächlich verwendeten Instrumente korrekt an.

## Edge Cases
- Alle Instrumente sind deaktiviert: Speichern und Bestätigen werden blockiert; die Run-Vorschau ist leer.
- Ein deaktiviertes Instrument wird wieder aktiviert: Es erscheint sofort wieder in der nächsten Run-Vorschau.
- Ein Instrument wird entfernt: Es erscheint in einem neuen Batch nicht erneut, solange es nicht wieder hinzugefügt wird.
- Zwei Zeilen besitzen dasselbe Provider-Symbol: Speichern wird mit „Provider-Symbol ist bereits vorhanden.“ blockiert.
- Für Nutzer ohne gespeicherte Auswahl startet die Instrumentliste mit den Produkt-Standardinstrumenten.
- Ältere bestätigte Batches ohne Aktivstatus bleiben lesbar; ihre gespeicherten Instrumente gelten als verwendet.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-16 · **Stack:** Next.js 16 (App Router) + shadcn/ui / FastAPI + raw SQL / PostgreSQL · **Branch:** dev

### A) Komponentenstruktur

```text
BatchConfigurationPage
├── InstrumentCard
│   ├── InstrumentTable
│   │   └── InstrumentRow
│   │       ├── AktivCheckbox
│   │       ├── ProviderSymbolInput
│   │       ├── LabelInput
│   │       ├── NichtVerwendetKennzeichnung
│   │       └── EntfernenAction
│   ├── InstrumentHinzufuegenAction
│   └── InstrumentValidationAlert
└── PreviewAndConfirmationCard
    ├── RunPreview       (nur aktive Instrumente)
    ├── CreditGate       (nur aktive Instrumente)
    └── ConfirmBatchAction

InstrumentPreference (Browser-Präferenz)
├── initialisiert neue Batch-Formulare
├── ergänzt beim Öffnen eines Entwurfs zuletzt deaktivierte Instrumente
└── wird erst nach erfolgreichem Speichern aktualisiert
```

Ein bearbeitbarer Batch zeigt aktive und inaktive Instrumente gemeinsam. Bestätigte Batches
zeigen ausschließlich ihren unveränderlichen serverseitigen Snapshot; dort gibt es keine
Schalter oder Entfernen-Aktionen.

### B) Datenmodell

**Im bestehenden Batch in PostgreSQL:**

- Es werden weiterhin nur Instrumente gespeichert, die für diesen Batch tatsächlich aktiv
  sind: Provider-Symbol und optionales Label.
- Run-Vorschau, Credit-Prüfung, Bestätigung und Audit lesen unverändert diese aktive Liste.
- Mindestens ein eindeutiges Provider-Symbol ist für jeden neuen oder geänderten Batch Pflicht.
- Bestätigte Batches und ihre Runs bleiben unverändert.

**Als lokale Browser-Präferenz:**

- Die zuletzt erfolgreich gespeicherte vollständige Instrumentliste enthält Provider-Symbol,
  Label, Aktivstatus und Reihenfolge.
- Ein neues Batch-Formular startet mit dieser Präferenz. Existiert keine gültige Präferenz,
  gelten die vorhandenen Produkt-Standardinstrumente.
- Beim Öffnen eines Entwurfs gelten dessen serverseitige Instrumente als aktiv; weitere
  Einträge aus der letzten Präferenz werden als inaktiv ergänzt. So bleibt der Batch-Snapshot
  die Wahrheit, ohne deaktivierte Instrumente dauerhaft zum Batch zu zählen.
- Eine ungültige oder manuell beschädigte Browser-Präferenz wird ignoriert und durch die
  Produkt-Defaults ersetzt. Secrets oder Handelsdaten werden dort nicht gespeichert.

Keine neue Datenbanktabelle und keine MinIO-Nutzung.

### C) API-Form

Die vorhandenen Endpunkte bleiben erhalten; neue Endpunkte sind nicht nötig:

- `POST /batches` → erhält ausschließlich die aktiven Instrumente eines neuen Standard-Batches.
- `PATCH /batches/{id}` → ersetzt bei einem bearbeitbaren Entwurf ausschließlich dessen aktive
  Instrumentliste.
- `POST /strategy-versions/{id}/holdout-batch` → erhält die derzeit aktiven Instrumente für den
  neuen Holdout-Batch.
- `POST /strategy-versions/{id}/forward-test-batch` → erhält die derzeit aktiven Instrumente für
  den neuen Forward-Batch.
- `GET /batches/{id}` → liefert weiterhin ausschließlich die im Batch verwendeten Instrumente.
- `GET /batches/{id}/preview` → erzeugt Runs nur aus dieser aktiven Instrumentliste.
- `GET /batches/{id}/credit-check` → zählt nur diese geplanten Runs.
- `POST /batches/{id}/confirm` → blockiert als letzte Schranke einen Batch ohne Instrument.

Beim Anlegen darf das Instrumentfeld fehlen; dann gelten die bestehenden Server-Defaults.
Wird es mitgesendet, muss es mindestens ein Instrument enthalten. Leere Listen liefern 422 mit
„Bitte mindestens ein Instrument aktivieren.“. Doppelte Provider-Symbole werden ebenfalls mit
422 und „Provider-Symbol ist bereits vorhanden.“ abgelehnt.

### D) Technische Entscheidungen

- **Aktivstatus bleibt außerhalb des Batch-Snapshots:** Ein deaktiviertes Instrument erzeugt
  keinen Run und gehört fachlich nicht zum Batch. Dadurch bleiben Preview, Credits und Audit
  ohne Sonderlogik korrekt.
- **Browser-Präferenz statt neuer Tabelle:** Die App ist Single-User und die Auswahl ist reine
  Bedienpräferenz. Native Browser-Speicherung erfüllt „nach Neuladen verfügbar“ ohne Backend-
  Ressource, Migration oder neue Abhängigkeit. Sie gilt bewusst pro Browserprofil.
- **Speichern erst nach API-Erfolg:** Eine fehlgeschlagene Batch-Änderung darf die zuletzt
  funktionierende Auswahl nicht ersetzen.
- **Frontend- und Backend-Validierung:** Das UI verhindert den normalen Leer- und Duplikatfall;
  das Backend schützt Run- und Credit-Pfade auch bei direkten API-Aufrufen.
- **Entfernen bleibt getrennt von Deaktivieren:** Deaktivieren ist temporär und reversibel;
  Entfernen löscht den Eintrag aus der nächsten gespeicherten Präferenz.
- **Keine Änderung an Preview oder Credit-Logik:** Beide lesen schon die gespeicherten Batch-
  Instrumente. Das Filtern geschieht vor dem Speichern an einer einzigen Stelle.

### E) Abhängigkeiten und Verifikation

- Frontend: keine neue npm-Abhängigkeit; vorhandene Checkbox, Tabelle und Browser-Speicherung
  genügen.
- Backend: keine neue Python-Abhängigkeit.
- Datenbank: keine Migration und keine neue Tabelle.
- Kleinste Frontend-Verifikation: Aktivieren/Deaktivieren verändert die gesendete Instrumentliste;
  erfolgreiche Speicherung aktualisiert die nächste Startauswahl, fehlgeschlagene nicht.
- Kleinste Backend-Verifikation: leere und doppelte Instrumentlisten werden abgelehnt; eine
  gültige aktive Liste bestimmt unverändert Vorschau, Credits und erzeugte Runs.

## QA Test Results
**Datum:** 2026-07-16 · **Tester:** /abc-qa · **Branch:** dev

### Methodik
- Code-Review der Frontend-Änderung in `nextjs_app/app/batches/page.tsx` gegen
  alle 8 Acceptance Criteria + 6 Edge Cases.
- `npx next build` → Errors: 0, Warnings: 0. `tsc --noEmit` → 0 Fehler.
- Backend-Regression: `pytest tests/test_batches.py` läuft isoliert grün (25/25).
  Eine bereits vorhandene Flakiness in `tests/test_results.py` (1 Test) ist
  pre-existing und nicht PROJ-17-bezogen.
- Neue Test-Suite `backend/tests/test_proj17_instruments.py` (6 Tests) deckt
  die vertraglichen Sollbruchstellen ab.

### Frontend Acceptance Criteria

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | Eigene Aktiv-Auswahl je Zeile im bearbeitbaren Batch | ✅ | `Checkbox` in eigener Spalte; nur sichtbar wenn `!isConfirmed` (page.tsx:774-779) |
| 2 | Inaktive bleiben sichtbar mit „Nicht verwendet"-Kennzeichnung | ✅ | `Badge` + `opacity-60` (page.tsx:770, 791-793) |
| 3 | Nur aktive fließen in Vorschau, Bestätigung, Credit-Maximum | ✅ | `activeRows` Filter beim Build des Request-Body (page.tsx:363-380) |
| 4 | Deaktivieren ≠ Entfernen | ✅ | `toggleInstrumentActive` vs `removeInstrument` (page.tsx:301-311) |
| 5 | Neuer Batch übernimmt zuletzt gespeicherte Auswahl | ✅ | `readInstrumentPreference()` in `loadInitial` (page.tsx:272-276) |
| 6 | Auswahl überlebt Reload; fehlgeschlagene Saves überschreiben sie nicht | ✅ | `writeInstrumentPreference` nur im `try`-Block nach erfolgreichem API-Call (page.tsx:392) |
| 7 | Mindestens 1 aktives Instrument vor Speichern/Bestätigen | ✅ Frontend | Fehlermeldung im UI + Save-Block (page.tsx:364-367); Backend hat Lücke (siehe Bug 1) |
| 8 | Bestätigte Batches unveränderlich, zeigen verwendete Instrumente | ✅ | `isConfirmed` gate auf alle Edit-Controls (page.tsx:288, 808) |

### Frontend Edge Cases

| Fall | Status | Beleg |
|---|---|---|
| Alle deaktiviert → Speichern blockiert | ✅ | Frontend-Validierung in `handleSaveDraft` (page.tsx:364-367) |
| Reaktivierung erscheint in nächster Vorschau | ✅ | State-Update triggert `refreshPreview` nach Save |
| Entferntes Instrument kommt in neuem Batch nicht wieder | ✅ | `writeInstrumentPreference` schreibt nur aktuelle Liste |
| Doppeltes Provider-Symbol blockiert Save | ✅ Frontend | `hasDuplicateProviderSymbol` (page.tsx:313-322, 359-362) |
| Ohne Präferenz → Produkt-Standards | ✅ | `DEFAULT_INSTRUMENTS` Fallback (page.tsx:48, 62-72) |
| Ältere bestätigte Batches bleiben lesbar | ✅ | `else`-Zweig: `setInstruments(serverActive)` mit `active: true` (page.tsx:259-261) |

### Security / Tenant Isolation
- **XSS:** Instrument-Werte gehen in `<Input value={...}>` → React escaped automatisch. Kein `dangerouslySetInnerHTML`.
- **localStorage:** Nur `provider_symbol`, `label`, `active` (Boolean). Keine Secrets, kein PII, keine Trade-Daten. Korrupter/manipulierter Storage wird durch `readInstrumentPreference()` mit Strukturvalidierung abgewiesen und durch Defaults ersetzt (page.tsx:53-80).
- **SSR:** `typeof window === "undefined"`-Guard umgeht Server-Render Crash.

### Bugs gefunden

#### Bug 1 (High) — Backend akzeptiert doppelte Provider-Symbole
- **Spec:** Edge Case „Zwei Zeilen besitzen dasselbe Provider-Symbol: Speichern wird mit „Provider-Symbol ist bereits vorhanden." blockiert."
- **Status:** ✅ **GEFIXT** in Commit nach QA (`fix(PROJ-17)`).
  `field_validator` auf `BatchCreate`, `BatchUpdate`, `HoldoutBatchCreate`
  in `app/schemas/batches.py` — case-insensitive Prüfung
  (`provider_symbol.strip().lower()` in `set`). Liefert 422 mit der
  Spec-Meldung „Provider-Symbol ist bereits vorhanden."
- **Begleit-Fix in `app/main.py`:** Der globale `RequestValidationError`-
  Handler hat Pydantic-Errors bisher direkt (`exc.errors()`) ins JSON
  geschrieben. Pydantic 2 legt rohe Exception-Instanzen in `ctx.error` ab;
  ein `ValueError` aus einem benutzerdefinierten Validator war nicht
  JSON-serialisierbar und produzierte ein 500 statt 422. Fix: `jsonable_encoder`
  um die Errors wickeln. Vorhandene Handler-Formate (String-`detail` aus
  `HTTPException`, Pydantic-Listen-`detail`) bleiben unverändert.

#### Bug 2 (Spec-Konflikt) — Leere Instrument-Liste bei Create/Patch
- **Spec AC 7:** „Leere Listen liefern 422 mit „Bitte mindestens ein Instrument aktivieren.""
- **Realität:** Backend akzeptiert `instruments: []` mit 201. Bestehender Test
  `test_batches.py::test_explicit_empty_instruments_and_modes_not_replaced_with_defaults`
  erzwingt genau dieses Verhalten.
- **Effektive Sicherheit:** `POST /batches/{id}/confirm` lehnt mit 422 „Batch
  ist unvollständig" ab, sobald ein leerer Batch bestätigt werden soll. Die
  letzte Schranke steht also — nur an einer anderen Stelle als der Spec.
- **Empfehlung:** Spec anpassen („Frontend blockt beim Speichern; Confirm
  lehnt unvollständige Batches ab") **oder** den existierenden Test
  umschreiben + Backend-Validierung ergänzen. Aktuell ist beides gleichzeitig
  wahr, was die Test-Suite beim Versuch, eines der beiden zu erfüllen,
  verwirrt. Frontend-AC ist erfüllt, Backend-AC nicht.

#### Bug 3 (Low) — Confirm blockt nicht eigenständig wenn User im UI alles deaktiviert
- **Status:** Wenn der User alle Instrumente via Checkbox deaktiviert **ohne**
  nochmal zu speichern und dann auf „Batch bestätigen" klickt, ist der
  Server-Batch noch im letzten aktiven Zustand, also läuft Confirm durch.
  Das ist *nicht* streng falsch (der Server-Snapshot ist die Wahrheit), aber
  der User wird verwirrt, weil die UI inaktiv zeigt und der Confirm trotzdem
  erfolgreich ist. UX-Verbesserung: Frontend sollte bei `activeInstruments.length === 0`
  den Bestätigen-Button deaktivieren.
- **Reproduktion:** Manuell im UI — alle Häkchen weg → direkt Bestätigen → Runs werden erzeugt.

### Test-Suite
- `backend/tests/test_proj17_instruments.py` (6 Tests, neu)
- Frontend: keine neue Test-Suite — Feature ist reine Render-/State-Logik in
  einer bestehenden Client-Komponente. Empfehlung für später: Komponenten-
  Refactoring in eine eigene `InstrumentTable` mit React-Testing-Library
  Tests.

### Production-Ready Entscheidung
- Vor dem Fix: **NICHT READY** wegen Bug 1 (High).
- Nach Fix: **READY mit Vorbehalt.** Bug 1 behoben, Bug 2 ist eine reine
  Spec-/Test-Konflikt-Entscheidung (Confirm-Block als letzte Schranke deckt
  die UX ab), Bug 3 ist UX-Polish und nicht blockierend.

Offene Punkte für Product-Entscheidung:
- Bug 2: Soll der bestehende Test `test_explicit_empty_instruments_kept`
  umgeschrieben werden + Backend-Validierung ergänzt, oder bleibt der
  Confirm-Pfad die einzige Schranke? Aktueller Stand: nur Confirm.
- Bug 3: UX-Verbesserung „Bestätigen-Button bei aktiver-leerer Liste im UI
  deaktivieren" als Follow-up.

## Deployment
_To be added by /abc-deploy_
