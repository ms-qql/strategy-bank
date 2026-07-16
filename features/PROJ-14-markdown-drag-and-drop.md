# PROJ-14: Markdown-Drag-and-Drop in der Quellenerfassung

## Status: Deployed
**Created:** 2026-07-16
**Last Updated:** 2026-07-16

## Dependencies
- Requires: PROJ-1 (Quellenerfassung) — bestehender Markdown-Upload und dessen Validierung bleiben verbindlich.

## User Stories
- Als Trader möchte ich eine Markdown-Datei auf ein Ablagefeld ziehen, um sie ohne Dateidialog zu erfassen.
- Als Trader möchte ich dasselbe Feld anklicken können, um bei Bedarf weiterhin den Dateidialog zu verwenden.
- Als Trader möchte ich vor dem Speichern sehen, welche Datei ausgewählt ist, um Fehlzuordnungen zu vermeiden.

## Acceptance Criteria
- [ ] Im Tab „Markdown-Datei“ ist ein klar erkennbares Ablagefeld mit dem Text „Markdown-Datei hier ablegen oder auswählen“ vorhanden.
- [ ] Das Ablegen genau einer gültigen `.md`-Datei wählt sie für den bestehenden Speichervorgang aus; es startet weder Speicherung noch Extraktion automatisch.
- [ ] Ein Klick sowie die Tastaturaktionen Enter und Leertaste auf dem fokussierten Ablagefeld öffnen den bestehenden Dateidialog.
- [ ] Während eine Datei über einer gültigen Ablagefläche gezogen wird, zeigt das Feld einen sichtbaren Aktivzustand.
- [ ] Nach der Auswahl zeigt das Feld Dateiname und Dateigröße. Eine weitere Auswahl ersetzt die vorherige Datei.
- [ ] Drag-and-Drop und Dateidialog verwenden dieselben bestehenden Regeln: genau eine `.md`-Datei, maximal 2 MB, nicht leer und valides UTF-8.
- [ ] Das Ablegen einer Datei außerhalb des Ablagefelds navigiert nicht von der App weg und öffnet die Datei nicht im Browser.
- [ ] Die Klartext-Erfassung bleibt unverändert und kann nicht gleichzeitig mit einem Datei-Upload gespeichert werden.

## Edge Cases
- Mehrere gleichzeitig abgelegte Dateien werden abgelehnt mit „Bitte genau eine Markdown-Datei ablegen.“; keine davon wird ausgewählt.
- Eine Datei ohne `.md`-Endung wird abgelehnt mit „Nur .md-Dateien werden unterstützt.“.
- Eine Datei über 2 MB oder ohne Inhalt wird mit der bereits vorhandenen deutschen Validierungsmeldung abgelehnt.
- Ein abgelegter Ordner wird wie eine ungültige Datei abgelehnt.
- Wird eine gültige Datei nach einer ungültigen Datei abgelegt, verschwindet der alte Fehler und die gültige Datei ist ausgewählt.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-16 · **Stack:** Next.js 16 (App Router) + shadcn/ui / FastAPI + PostgreSQL · **Branch:** dev

### A) Komponentenstruktur

```text
QuellenView
├── QuelleErfassenCard
│   ├── QuellenTabs
│   │   ├── KlartextEingabe (unverändert)
│   │   └── MarkdownUploadPanel
│   │       ├── MarkdownDropzone
│   │       │   └── NativerDateidialog (genau eine .md-Datei)
│   │       ├── DragAktivzustand
│   │       └── DateiauswahlZusammenfassung (Name und Größe)
│   ├── ValidierungsHinweis
│   └── QuelleSpeichernButton (bestehender Speichervorgang)
└── GlobalerDateiDropSchutz
```

Die Dropzone ersetzt im Tab „Markdown-Datei“ die sichtbare Standard-Dateieingabe,
verwendet intern aber weiterhin den nativen Dateidialog. Sie ist per Maus und
Tastatur bedienbar und zeigt einen klaren Fokus- sowie Drag-Aktivzustand. Auswahl
per Dialog und Ablegen laufen durch dieselbe Validierung und setzen denselben
Dateistatus. Eine neue gültige Datei ersetzt die vorherige; eine ungültige Auswahl
ersetzt sie nicht. Speichern und Extraktion beginnen weiterhin ausschließlich über
die vorhandene Schaltfläche.

Der globale Datei-Drop-Schutz verhindert nur bei Datei-Drag-Vorgängen die
Browser-Navigation außerhalb der Dropzone. Normale Klicks, Textauswahl und die
Klartext-Erfassung bleiben davon unberührt.

### B) Datenmodell

Das bestehende Quellenmodell bleibt unverändert:

- ID und Erfassungszeitpunkt
- unveränderter Markdown-Rohinhalt
- SHA-256-Quell-Hash
- Quelltyp `markdown_file`
- ursprünglicher Dateiname
- Extraktionsstatus

Die Dropzone hält vor dem Speichern lediglich genau eine ausgewählte Browser-Datei
mit Name und Größe im bestehenden Formularzustand. Es entstehen keine neue Tabelle,
keine Migration und kein zusätzlicher persistierter Status. Der Markdown-Inhalt
bleibt nach dem Speichern in PostgreSQL; MinIO ist für Textdateien bis 2 MB nicht
beteiligt.

### C) API-Form

Die bestehenden Endpunkte bleiben unverändert:

- `POST /sources` → ausgewählte Markdown-Datei erst beim Klick auf „Quelle speichern“ erfassen
- `GET /sources` → erfasste Quellen weiterhin in der vorhandenen Liste anzeigen
- `GET /sources/{id}` → bestehende Quelle einschließlich Rohinhalt laden

Dialogauswahl und Drag-and-Drop senden denselben bestehenden Datei-Upload an
`POST /sources`. Das Backend bleibt die verbindliche Schutzschicht für genau eine
Quelle, `.md`-Endung, maximal 2 MB, nicht leeren Inhalt und valides UTF-8. Die
Oberfläche prüft dieselben Regeln frühzeitig für eine direkte deutsche Rückmeldung;
bei Mehrfach-Drop gilt die speziell vorgegebene Meldung „Bitte genau eine
Markdown-Datei ablegen.“.

### D) Technische Entscheidungen

- **Ein gemeinsamer Auswahlweg:** Dialog und Dropzone aktualisieren denselben
  Formularzustand und nutzen dieselbe Validierung. Dadurch können die beiden
  Bedienwege nicht fachlich auseinanderlaufen.
- **Nativer Dateidialog bleibt erhalten:** Der Browser übernimmt die vertraute
  Dateiauswahl; die Dropzone ergänzt nur eine zweite Bedienmöglichkeit und benötigt
  keine Upload-Bibliothek.
- **Explizites Speichern:** Ablegen wählt nur eine Datei aus. Der bestehende Button
  bleibt die einzige Aktion, die Daten persistiert; Extraktion bleibt ein separater
  späterer Schritt.
- **Zugängliche Interaktionsfläche:** Die Dropzone ist fokussierbar, hat einen
  verständlichen Namen und reagiert auf Klick, Enter und Leertaste. Sichtbarer
  Fokus und Drag-Aktivzustand verwenden die bestehenden Design-Tokens.
- **Browser-Navigation zentral verhindern:** Datei-Drops außerhalb der Dropzone
  werden auf Seitenebene abgefangen, damit der Browser die App nicht durch die
  lokale Datei ersetzt.
- **Keine Backend- oder Storage-Erweiterung:** Transport, Validierung und Persistenz
  existieren bereits vollständig aus PROJ-1; eine zweite API oder Ablage würde nur
  parallele Logik schaffen.

### E) Abhängigkeiten

- **Frontend:** keine neuen Pakete; vorhandene React-/Next.js-, Browser- und
  shadcn/ui-Funktionen genügen
- **Backend:** keine neuen Pakete und keine Route-Änderung
- **Datenbank/Storage:** keine Migration, keine neue Tabelle, kein MinIO

## Implementation Notes
- `nextjs_app/components/quellen/markdown-dropzone.tsx` (neu): kapselt Dropzone + versteckten nativen Dateidialog. Klick, Enter, Leertaste öffnen den Dialog. Drag-Over zeigt Aktivzustand, Drop prüft früh (eine Datei, `.md`, ≤ 2 MB, nicht leer) und meldet Fehler über den bestehenden Alert-Pfad.
- `nextjs_app/components/quellen/quellen-view.tsx`: ersetzt das sichtbare `<Input type="file" />` durch die Dropzone; bestehende `datei`-State und `handleSubmit` bleiben verbindlich. Neuer Window-Listener verhindert Browser-Navigation bei Datei-Drops außerhalb der Dropzone, lässt Klicks, Textauswahl und Nicht-Datei-Drags unberührt.
- Validierung läuft früh clientseitig mit identischen Meldungen wie der bestehende Dialog (`Nur .md-Dateien werden unterstützt.`, `Quelle enthält keinen Inhalt.`, `Datei überschreitet das Größenlimit von 2 MB.`); die Spezialmeldung `Bitte genau eine Markdown-Datei ablegen.` greift ausschließlich bei Mehrfach-Drop.

## QA Test Results

**Tested:** 2026-07-16
**Backend:** http://localhost:8200 (FastAPI, `Dashboard`-env, strategy_bank)
**Frontend:** http://localhost:3120 (`next start`, prod build)
**Tester:** QA Engineer (AI) — Playwright 1.61.1 (headless Chromium)
**Harness:** `screenshots/test/proj14-dropzone.cjs` (16 Tests, 0 fehlgeschlagen, 2 Re-Runs idempotent)

### Acceptance Criteria Status

#### AC-1: Ablagefeld mit Pflichttext sichtbar
- [x] Tab „Markdown-Datei" zeigt Dropzone mit Text „Markdown-Datei hier ablegen oder auswählen"
- [x] Icon (`file-up`) und Hinweis „Genau eine .md-Datei, maximal 2 MB." als Sekundärtext
- Screenshot: `screenshots/test/proj14-ac1-dropzone.png`

#### AC-2: Drop wählt aus, kein Auto-Save / Auto-Extract
- [x] Drop einer gültigen `.md`-Datei setzt den Auswahlzustand (Summary `Ausgewählt: valid.md (1 KB)` sichtbar)
- [x] Quellenliste unverändert, kein POST auf `/sources`, keine Extraktion angestoßen
- Screenshot: `screenshots/test/proj14-ac2-selected.png`

#### AC-3: Klick + Enter + Leertaste öffnen Dateidialog
- [x] Klick auf Dropzone löst `filechooser` aus
- [x] Enter auf fokussierter Dropzone löst `filechooser` aus
- [x] Leertaste auf fokussierter Dropzone löst `filechooser` aus
- Hinweis: Pro Trigger in eigenem Browser-Kontext (sonst blockt das Schließen des ersten Choosers den zweiten)

#### AC-4: Sichtbarer Aktivzustand während Drag
- [x] `data-drag-active` wechselt von `false` → `true` bei `dragover`
- [x] Visuell: Rahmen in `primary` (teal), Hintergrund `primary/10`
- Screenshot: `screenshots/test/proj14-ac4-drag-active.png`

#### AC-5: Name + Größe sichtbar, neue Auswahl ersetzt
- [x] Erste Auswahl `first.md` sichtbar
- [x] Zweite Auswahl `second.md` ersetzt die erste; nur noch `second.md` sichtbar
- [x] Größenangabe in KB gerundet

#### AC-6: Gemeinsame Regeln für Drop und Dialog
- [x] Falsche Endung (`foo.txt`) → `Nur .md-Dateien werden unterstützt.`
- [x] Leere Datei (`empty.md`, 0 Bytes) → `Quelle enthält keinen Inhalt.`
- [x] > 2 MB → `Datei überschreitet das Größenlimit von 2 MB.`
- Hinweis: UTF-8-Prüfung läuft verbindlich im Backend (`source_text = raw_bytes.decode("utf-8")`)

#### AC-7: Drop außerhalb navigiert nicht
- [x] `drop` auf `<main>` löst keine Navigation aus, URL bleibt `/quellen`
- [x] Window-Listener ruft `preventDefault()` nur für echte Datei-Drags (`dataTransfer.types.includes("Files")`); Klicks und Textauswahl unberührt

#### AC-8: Klartext-Erfassung unverändert, keine Kombination mit Datei
- [x] Text im Klartext-Tab bleibt beim Wechsel auf Datei-Tab erhalten
- [x] Wechsel zurück liefert den ursprünglichen Text unverändert
- [x] Speichern funktioniert weiterhin (Regression-Test PROJ-1: Quelleneintrag wuchs nach Speichern)

### Edge Cases Status

#### EC-1: Mehrere Dateien gleichzeitig
- [x] Drop von 2 Dateien → `Bitte genau eine Markdown-Datei ablegen.` (Spezialtext)
- [x] Keine Datei wird ausgewählt (`getSelectedFileSummary` = null)

#### EC-2: Falsche Endung
- [x] Abgelehnt mit `Nur .md-Dateien werden unterstützt.`

#### EC-3: > 2 MB oder leer
- [x] Bestehende deutsche Meldungen greifen (siehe AC-6)

#### EC-4: Ordner-Drop
- [x] Leere `dataTransfer.files` (Folder-Zugriff nicht möglich) → `Nur .md-Dateien werden unterstützt.`

#### EC-5: Valide nach invalide
- [x] Vorheriger Fehler `Nur .md-Dateien…` wird durch valides Drop entfernt
- [x] Gültige Datei ist sichtbar ausgewählt

### Security Audit Results
- [x] XSS via Dateiname: React rendert Dateinamen als Textknoten; `body.textContent` enthält den Original-String, `body.innerHTML` enthält ihn escaped; kein gerendertes `<img onerror>`-Element
- [x] XSS via Datei-Inhalt: Inhalt wird nur an Backend gesendet; UI rendert keinen Markdown-Body (Datei-Inhalt ist nicht im DOM)
- [x] Kein `dangerouslySetInnerHTML` mit User-Daten (nur statisches Theme-Script in `app/layout.tsx`)
- [x] Globales Drop-Handling: Verhindert Browser-Navigation ohne Klicks / Textauswahl / Nicht-Datei-Drags zu blockieren
- [x] Tab-Wechsel räumt Fehlerzustand (kein Stale-State-Risiko zwischen Tabs)
- N/A Auth / Tenants: Solo-App laut Backend-Kommentar (`main.py: "kein Mandant/RLS"`)

### Regression
- [x] PROJ-1: Klartext-Speichern funktioniert (neuer Quelleneintrag erscheint in Tabelle)
- [x] Bestehende Quellenliste, Extraktions-Buttons, Entwurfskarten unverändert
- [x] Sidebar-Navigation (Quellen / Backtests / Ergebnisse / Einstellungen) nicht betroffen
- [x] Tab-Wechsel `Text einfügen` ↔ `Markdown-Datei` ohne Datenverlust

### Responsive
- [x] 375 px (Mobile): Dropzone zentriert, Text umbricht sauber
- [x] 768 px (Tablet): Dropzone voll sichtbar
- Screenshots: `proj14-responsive-mobile.png`, `proj14-responsive-tablet.png`

### Bugs Found

Keine.

### Summary
- **Acceptance Criteria:** 8/8 passed
- **Edge Cases:** 5/5 passed
- **Security:** Pass (XSS via Dateiname + Inhalt ausgeschlossen, Tab-Wechsel-State sauber)
- **Regression:** Pass (PROJ-1-Klartext-Pfad funktional)
- **Responsive:** Pass (375 / 768 / 1440)
- **Production Ready:** YES
- **Recommendation:** Deploy via `/abc-deploy`

### Test-Harness
`node screenshots/test/proj14-dropzone.cjs` — 16 assertions, idempotent, headless Chromium 1440×900 (plus 375/768 für Responsive). Voraussetzungen: Next.js `next start -p 3120` mit `BACKEND_URL=http://localhost:8200` und FastAPI-Backend auf `:8200`.

## Deployment
**Deployed:** 2026-07-16, Version v0.2.24.
**Inhalt:** `MarkdownDropzone`-Komponente (`nextjs_app/components/quellen/markdown-dropzone.tsx`) ersetzt das reine `<input type="file">` in der Quellenerfassung durch Drag-and-Drop + Klick-Fallback; globaler Fensterschutz verhindert Browser-Navigation bei Datei-Drop außerhalb der Zone.
**Commit:** `7af10d6 feat(PROJ-14): Markdown drag-and-drop dropzone in Quellen view` (plus vorgelagerte Design-/QA-Commits `c6b6b77`, `1c33e2c`).
**Push:** `origin/main` (Auto-Deploy auf Dokploy, `docker-compose.dokploy.yml`).
