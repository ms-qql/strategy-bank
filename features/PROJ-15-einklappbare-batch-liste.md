# PROJ-15: Einklappbare Liste vorhandener Batches

## Status: Planned
**Created:** 2026-07-16
**Last Updated:** 2026-07-16

## Dependencies
- Requires: PROJ-4 (Batch-Konfiguration) — vorhandene Batches und deren Öffnen-Aktion bestehen bereits.

## User Stories
- Als Trader möchte ich die Liste vorhandener Batches einklappen, um mehr Platz für die aktuelle Konfiguration zu haben.
- Als Trader möchte ich die Anzahl vorhandener Batches auch im eingeklappten Zustand erkennen.
- Als Tastaturnutzer möchte ich die Liste ohne Maus ein- und ausklappen können.

## Acceptance Criteria
- [ ] Die Kachel „Vorhandene Batches“ ist beim Öffnen der Batch-Konfiguration standardmäßig eingeklappt.
- [ ] Der eingeklappte Kopf zeigt den Titel, die Anzahl der geladenen Batches und eine Schaltfläche „Batches anzeigen“.
- [ ] „Batches anzeigen“ klappt die bestehende Liste auf; „Batches ausblenden“ klappt sie wieder ein.
- [ ] Ein- und Ausklappen verändert weder Batch-Daten noch die aktuelle Batch-Konfiguration.
- [ ] Die Schaltfläche ist per Tastatur bedienbar und gibt ihren Zustand für assistive Technologien als ein- beziehungsweise ausgeklappt aus.
- [ ] Das Öffnen eines vorhandenen Batches funktioniert aus der aufgeklappten Liste unverändert.
- [ ] Der Zustand wird nicht dauerhaft gespeichert; ein neuer Seitenaufruf startet wieder eingeklappt.

## Edge Cases
- Ohne vorhandene Batches wird die Kachel wie bisher nicht angezeigt.
- Während Batches geladen werden, zeigt die Anzahl keinen veralteten Zwischenstand.
- Nach einem Ladefehler entsteht keine leere aufklappbare Kachel.
- Eine sehr lange Liste vergrößert die Seite erst, nachdem der Nutzer sie bewusst aufgeklappt hat.
- Wird ein vorhandener Batch geöffnet, erscheint dessen Detailansicht unabhängig vom vorherigen Klappzustand.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /abc-architecture_

## QA Test Results
_To be added by /abc-qa_

## Deployment
_To be added by /abc-deploy_
