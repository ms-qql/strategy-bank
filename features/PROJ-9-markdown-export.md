# PROJ-9: Markdown-Export

## Status: Architected
**Created:** 2026-07-15
**Last Updated:** 2026-07-15

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
_To be added by /qa_

## Deployment
_To be added by /deploy_
