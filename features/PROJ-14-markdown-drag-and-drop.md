# PROJ-14: Markdown-Drag-and-Drop in der Quellenerfassung

## Status: Planned
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
_To be added by /abc-architecture_

## QA Test Results
_To be added by /abc-qa_

## Deployment
_To be added by /abc-deploy_
