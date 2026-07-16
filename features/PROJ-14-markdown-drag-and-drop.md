# PROJ-14: Markdown-Drag-and-Drop in der Quellenerfassung

## Status: Architected
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

## QA Test Results
_To be added by /abc-qa_

## Deployment
_To be added by /abc-deploy_
