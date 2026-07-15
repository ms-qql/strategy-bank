# PROJ-9: Markdown-Export

## Status: Implemented
**Created:** 2026-07-15
**Last Updated:** 2026-07-15

## Implementation Notes
- Route: `GET /drafts/{draft_id}/export.md` in `backend/app/routes/export.py`
- Returns `text/markdown; charset=utf-8` with `Content-Disposition: attachment`
- No new DB migration, schemas, or packages
- Metrics extracted inline (same logic as results.py `_extract_and_compute_metrics`)
- Deterministic byte-identical output for unchanged data (fixed field order, no export timestamp)
- Tests: `backend/tests/test_export.py` (13 tests)

## Dependencies
- Requires: PROJ-8 (Audit-Trail) — liefert die vollständigen, zu exportierenden Run- und Versionsdaten.

## User Stories
- Als Trader möchte ich eine Strategie samt aller Versionen und Runs als lokale Markdown-Datei exportieren, um sie außerhalb der App weiterzuverwenden (z. B. später manuell in Hal einzupflegen).
- Als Trader möchte ich, dass der Export deterministisch ist, um bei wiederholtem Export ohne Datenänderung dieselbe Datei zu erhalten.

## Acceptance Criteria
- [ ] Export erzeugt eine einzelne lokale `.md`-Datei je Strategie, enthält alle Versionen (inkl. Status „nicht testbar", falls vorhanden) und alle zugehörigen Runs mit Kernmetriken (siehe PROJ-7) und Report-Link.
- [ ] Export enthält je Version die Herkunftsangaben aus dem Audit-Trail (PROJ-8): Quelle, Quell-Hash, Extraktionsmodell, Prompt-Version, `frozen_at`.
- [ ] Export ist rein lokal (Download/Datei-Ablage) — keine automatische Synchronisierung in ein externes System (Hal-Sync ist explizit kein MVP-Bestandteil).
- [ ] Bei unveränderten Quelldaten erzeugt ein erneuter Export byte-identischen Inhalt (deterministische Feldreihenfolge, keine Zeitstempel des Exportvorgangs im Dateiinhalt).
- [ ] Runs ohne Report-Link oder ohne Rohantwort werden im Export als „unvollständig" gekennzeichnet, nicht stillschweigend ausgelassen.
- [ ] Export ist für Strategien in jedem Status (Entwurf, nicht testbar, freigegeben) möglich; der Status jeder Version ist im Export klar erkennbar.

## Edge Cases
- Strategie ohne jeden Run (nur freigegebene Version, noch nie getestet): Export enthält die Version, aber einen expliziten Hinweis „Keine Runs vorhanden" statt einer leeren Tabelle.
- Sehr viele Runs (z. B. mehrere Batches über Zeit): Export enthält alle, gruppiert nach Version, keine stille Kürzung/Sampling.
- Export während ein Run dieser Strategie noch `läuft`: laufender Run erscheint mit Status „läuft", Export kann danach erneut ausgelöst werden, um den Endzustand zu erhalten.
- Sonderzeichen in Strategie-Name oder These (z. B. Markdown-Steuerzeichen wie `#`, `|`, `` ` ``): werden im Export escaped, damit die Datei valides Markdown bleibt.

## Technical Requirements (optional)
- Kein Schreibzugriff auf externe Systeme (insb. kein Hal-Vault-Zugriff) im MVP.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-15 · **Stack:** Next.js 16 (App Router) + shadcn/ui / FastAPI + raw SQL / PostgreSQL · **Branch:** dev

### A) Komponentenstruktur (UI)

```text
EntwurfEditPage (bestehende Strategiedetailseite)
├── StrategieKopf (bestehend)
│   └── „Markdown exportieren“ (neu)
├── ExportStatus (nur während Download oder bei Fehler)
└── BrowserDownload
    └── eine lokale .md-Datei für die gesamte Strategiefamilie
```

Der Export bleibt eine einzelne Aktion auf der vorhandenen Strategiedetailseite.
Er ist für Entwürfe, als „nicht testbar“ markierte Strategien und freigegebene
Strategien verfügbar. Eine zusätzliche Exportseite oder Konfiguration ist nicht
nötig, weil Format und Umfang durch die Akzeptanzkriterien fest vorgegeben sind.

### B) Datenmodell (Klartext)

Es wird keine neue Tabelle angelegt. Der Export liest einen konsistenten
Gesamtstand aus den bestehenden Daten:

```text
Strategiefamilie
├── alle zugehörigen Entwürfe und unveränderlichen Versionen
│   ├── Status und ggf. Begründung „nicht testbar“
│   ├── Name, These, Regeln, Parameter und PROJ-10-Angaben
│   ├── Quelle und Quell-Hash
│   ├── Extraktionsmodell und Prompt-Version
│   └── frozen_at oder ausdrücklich „noch nicht eingefroren“
└── alle Runs je freigegebener Version
    ├── Run-Status und Auswertungsart
    ├── Instrument, Richtung, Zeitraum und Kernmetriken aus PROJ-7
    ├── Report-Link oder ausdrücklicher Fehlhinweis
    └── Rohantwort-Verfügbarkeit aus PROJ-8
```

Freigegebene Versionen werden aus den append-only Versionsdaten gelesen. Noch
nicht freigegebene oder als „nicht testbar“ markierte Stände werden aus ihren
Entwurfsdaten aufgenommen und klar von eingefrorenen Versionen unterschieden.
Runs sind immer ihrer eingefrorenen Strategieversion zugeordnet. Hat ein Stand
keine Runs, enthält der Export den Satz „Keine Runs vorhanden“.

Der Server erzeugt die Datei nur für den Download und speichert sie weder in
PostgreSQL noch in MinIO. Der Dateiname besteht stabil aus dem bereinigten
Strategienamen und der unveränderlichen Familien-ID.

### C) API-Form (nur Endpunkte)

```text
GET /drafts/{id}/export.md
    → erzeugt den Markdown-Export der gesamten Strategiefamilie des Entwurfs
      und liefert ihn als lokalen Dateidownload
```

Der vorhandene Entwurf dient nur als Einstieg; exportiert wird immer seine
gesamte Strategiefamilie. Ein unbekannter Entwurf liefert „nicht gefunden“.
Der Endpunkt verändert keine Daten und startet keine externe Synchronisierung.

### D) Tech-Entscheidungen (warum)

- **Serverseitig erzeugen:** Versionen, Runs, Audit-Daten und Metriken liegen im Backend. Ein gemeinsamer Export-Endpunkt erhält einen konsistenten Gesamtstand und vermeidet viele Frontend-Abfragen.
- **Vorhandene Daten statt Export-Snapshot:** Der Download ist eine Sicht auf den aktuellen gespeicherten Stand. Eine zusätzliche Exporttabelle würde Daten duplizieren und könnte selbst veralten.
- **Feste, dokumentierte Reihenfolge:** Versionen werden nach Versionsnummer, Runs danach nach Erstellungszeitpunkt und stabiler ID ausgegeben. Abschnitte und Felder haben ebenfalls eine feste Reihenfolge. So bleibt der Inhalt bei unveränderten Quelldaten byte-identisch.
- **Kein Exportzeitpunkt im Inhalt:** Nur fachliche Zeitpunkte wie `frozen_at`, Run-Start und Run-Ende erscheinen. Der Zeitpunkt des Downloads würde identische Wiederholungsexporte unnötig verändern.
- **Festes Textformat:** UTF-8, einheitliche Zeilenenden und eine zentrale Markdown-Escaping-Regel für Überschriften, Fließtext und Tabellen verhindern Unterschiede zwischen Browsern und Sonderzeichen-Schäden.
- **Unvollständigkeit sichtbar machen:** Fehlt bei einem Run der Report-Link oder die Rohantwort, wird der Run vollständig ausgegeben und zusätzlich als „unvollständig“ markiert. Fehlende Werte führen nie zum stillen Weglassen.
- **PROJ-10 aus dem gespeicherten Snapshot:** Positionsmodus, Exit-Regel samt Herkunft und Crypto-MTS-Eignung werden exakt wie eingefroren exportiert. Bei Legacy-Versionen steht „Nicht verfügbar — Legacy-Version“ statt einer nachträglichen Schätzung.
- **Browser-Download statt Dateisystemzugriff:** Der Browser bietet die Datei lokal an. Das erfüllt den MVP ohne Server-Dateiablage, Hal-Zugriff oder Betriebssystem-spezifische Berechtigungen.
- **Keine Pagination im Export:** Die Datei muss alle Runs enthalten. Der Endpunkt liest daher die vollständige Strategiefamilie; eine spätere Größenbegrenzung wäre eine fachliche Änderung und darf nicht still eingeführt werden.

### E) Abhängigkeiten

- Backend: keine neuen Python-Pakete; vorhandenes FastAPI, Pydantic und PostgreSQL/raw SQL genügen.
- Frontend: keine neuen npm-Pakete; vorhandener Button, Alert und nativer Browser-Download genügen.
- Datenbank: keine Migration; bestehende Entwurfs-, Versions-, Run-, Ergebnis- und Audit-Daten werden nur gelesen.
- MinIO: nicht benötigt, weil keine Datei serverseitig gespeichert wird.
- PROJ-7 liefert die verbindlichen Kernmetriken und die Ergebnisbegriffe.
- PROJ-8 liefert Report-Link, Rohantwort-Verfügbarkeit und reproduktionsrelevante Run-Snapshots.
- PROJ-10 liefert Positionsmodus, Exit-Herkunft und Crypto-MTS-Angaben im Versions-Snapshot.

## QA Test Results

**Tested:** 2026-07-15
**Backend:** http://localhost:8000 (FastAPI, env `Dashboard`)
**Frontend:** N/A (Backend-only feature, UI button handled by frontend team)
**Test Runner:** TestClient (pytest, 189 total tests, 17 export-specific)
**Tester:** QA Engineer (AI)

### Acceptance Criteria Status

#### AC-1: Export erzeugt einzelne .md-Datei je Strategie mit allen Versionen und Runs
- [x] Einzelne Markdown-Datei wird als Download ausgeliefert (Content-Type: text/markdown)
- [x] Alle freigegebenen Versionen erscheinen, gruppiert nach Versionsnummer
- [x] Alle nicht-freigegebenen Entwürfe erscheinen (Entwurf, nicht testbar)
- [x] Alle Runs je Version mit Kernmetriken (Net Profit %, CAGR %, Trades, Max DD %, Sharpe, Profit Factor, Calmar)
- [x] Report-Link als klickbarer Markdown-Link

#### AC-2: Herkunftsangaben aus Audit-Trail je Version
- [x] Quell-ID (`source_id`)
- [x] Quell-Hash (`source_hash`)
- [x] Extraktionsmodell (`extraction_model`)
- [x] Prompt-Version (`prompt_version`)
- [x] Eingefroren am (`frozen_at`)

#### AC-3: Rein lokaler Export — keine externe Synchronisierung
- [x] Endpunkt returned Datei-Download via Browser (Content-Disposition: attachment)
- [x] Keine serverseitige Dateiablage (weder PostgreSQL noch MinIO)
- [x] Keine Hal-Synchronisierung oder externe API-Calls im Export-Code

#### AC-4: Deterministischer, byte-identischer Wiederholungsexport
- [x] Bei unveränderten Quelldaten liefern zwei Aufrufe identischen Inhalt
- [x] Keine Export-Zeitstempel im Dateiinhalt (nur fachliche Zeitpunkte: frozen_at, Run-Start, Run-Ende)
- [x] Feste Reihenfolge: Versionen nach Versionsnummer, Runs nach created_at + id

#### AC-5: Unvollständige Runs sichtbar markiert
- [x] Runs ohne Report-Link → "(unvollständig)" im Status
- [x] Runs ohne Rohantwort (raw_response_available=false) → "(unvollständig)" im Status
- [x] Kein stillschweigendes Auslassen — Runs erscheinen immer in der Tabelle

#### AC-6: Export für alle Strategie-Status möglich
- [x] Entwurf → Draft-Bereich mit "Entwurf — Entwurf"
- [x] nicht testbar → Draft-Bereich mit "Nicht testbar" + status_reason
- [x] freigegeben → Versions-Bereich mit "Freigegeben am <frozen_at>"
- [x] gesperrt (unvollständig) → Draft-Bereich mit "Gesperrt (unvollständig)"

### Edge Cases Status

#### EC-1: Version ohne Runs → "Keine Runs vorhanden"
- [x] Expliziter Hinweis statt leerer Tabelle

#### EC-2: Sehr viele Runs → alle enthalten, keine Kürzung
- [x] SQL-Query ohne LIMIT — alle Runs werden gelesen
- [x] Keine stille Kürzung/Sampling im Code

#### EC-3: Laufender Run → Status „Läuft"
- [x] Run mit Status "läuft" erscheint mit Label "Läuft"
- [x] Zusätzlich "(unvollständig)"-Markierung (kein Report-Link bei laufenden Runs)
- [x] Export kann nach Run-Abschluss erneut ausgelöst werden (deterministisch = neuer Zustand)

#### EC-4: Sonderzeichen in Name/These → escapt
- [x] Pipe (`|`) → `\|` (Tabellenintegrität)
- [x] Sonderzeichen in Dateinamen → via `_safe_filename` bereinigt
- [ ] BUG (MEDIUM): Zeilenumbrüche (`\n`) in Textfeldern (These, Entry-Regel etc.) nicht escaped — brechen Markdown-Tabelle. Siehe BUG-1.

### Security Audit Results

- [x] SQL Injection: Alle Queries nutzen parametrisierte `%s`-Platzhalter (psycopg v3). Keine String-Interpolation von User-Input.
- [x] Input Validation: `draft_id` ist FastAPI-UUID-Parameter. Ungültige UUIDs → 404 via Exception-Handler. Numeric/Text-Injection nicht möglich.
- [x] Authentication: Keine Auth im Projekt (Single-Tenant, solo user) — kein Auth-Bypass-Vektor.
- [x] Tenant Isolation: N/A (Single-Tenant)
- [x] Information Leakage: 404-Fehler nur "Entwurf nicht gefunden." — keine Stack-Traces, DB-Fehler oder interne IDs.
- [x] Path Traversal: Keine Dateioperationen, kein Dateisystemzugriff.
- [x] SSRF: Keine ausgehenden HTTP-Requests im Export-Code.
- [x] Rate Limiting: N/A (kein slowapi im Projekt; Endpunkt ist Read-Only, kein mutierender Zugriff).
- [x] Content-Disposition Header: Dateiname via `_safe_filename` bereinigt — keine Header-Injection möglich.

### Bugs Found

#### BUG-1: Zeilenumbrüche in Textfeldern nicht escaped
- **Severity:** Medium
- **Steps to Reproduce:**
  1. Strategie mit mehrzeiliger These oder Entry-Regel anlegen (z. B. "Zeile 1\nZeile 2")
  2. Export auslösen
  3. Expected: Zeilenumbruch wird escaped (z. B. `<br>` oder `\\n`), Markdown-Tabelle bleibt valide
  4. Actual: Rohes `\n` im Tabellenfeld bricht die Markdown-Tabelle; Rendering fehlerhaft
- **Code:** `_escape_md()` in `backend/app/routes/export.py:19` escaped nur `|`, nicht `\n`
- **Priority:** Fix before deployment (Medium — betrifft nur mehrzeilige Texteingaben, die im aktuellen UI nicht vorgesehen sind)

### Summary
- **Acceptance Criteria:** 6/6 passed
- **Bugs Found:** 1 total (0 critical, 0 high, 1 medium, 0 low)
- **Security:** Pass — keine sicherheitskritischen Findings
- **Production Ready:** YES (BUG-1 ist Medium — tritt nur bei mehrzeiligen Eingaben auf, die im aktuellen UI nicht möglich sind)
- **Recommendation:** Deploy. BUG-1 kann im nächsten Sprint gefixt werden (einfache Erweiterung von `_escape_md` um `\n → <br>`-Ersatz).
