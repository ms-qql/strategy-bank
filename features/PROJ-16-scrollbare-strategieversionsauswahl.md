# PROJ-16: Scrollbare Strategieversionsauswahl im Backtest

## Status: Planned
**Created:** 2026-07-16
**Last Updated:** 2026-07-16

## Dependencies
- Requires: PROJ-4 (Batch-Konfiguration) — Auswahl freigegebener Strategieversionen besteht bereits.

## User Stories
- Als Trader möchte ich auch bei vielen Strategieversionen alle Einträge erreichen, ohne dass die Auswahl den restlichen Backtest verdrängt.
- Als Trader möchte ich mehrere weit auseinanderliegende Versionen auswählen können, ohne Auswahlzustände beim Scrollen zu verlieren.
- Als Tastaturnutzer möchte ich durch die gesamte Liste navigieren und Einträge auswählen können.

## Acceptance Criteria
- [ ] Nur die Liste innerhalb der Kachel „Strategieversionen“ scrollt vertikal, sobald ihr Inhalt die verfügbare Höhe überschreitet.
- [ ] Die sichtbare Listenhöhe beträgt höchstens 50 Prozent der Browserhöhe; Überschrift und Beschreibung der Kachel bleiben außerhalb des Scrollbereichs sichtbar.
- [ ] Alle geladenen Strategieversionen bleiben über den inneren Scrollbereich erreichbar.
- [ ] Ausgewählte Versionen behalten ihren Zustand beim Scrollen, beim Verlassen des sichtbaren Bereichs und beim Zurückscrollen.
- [ ] Maus, Trackpad und Tastatur können den inneren Scrollbereich bedienen; Checkboxen bleiben per Tab und Leertaste erreichbar.
- [ ] Bei wenigen Einträgen erscheint kein unnötiger Scrollbalken und die aktuelle Darstellung bleibt kompakt.
- [ ] Die Änderung beeinflusst weder die Auswahlregeln noch die erzeugte Run-Vorschau.

## Edge Cases
- Bei keiner freigegebenen Strategieversion bleibt der vorhandene Leerzustand sichtbar.
- Ein einzelner sehr langer Strategiename vergrößert nicht die Breite der Seite; er bleibt innerhalb der Zeile lesbar oder wird gekürzt dargestellt.
- Nach dem Nachladen oder Aktualisieren der Liste bleiben weiterhin vorhandene ausgewählte IDs ausgewählt.
- Auf kleinen Browserhöhen bleibt mindestens eine vollständig bedienbare Strategiezeile sichtbar.
- Ein bestätigter Batch zeigt die gesperrte Auswahl weiterhin scrollbar und vollständig lesbar.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /abc-architecture_

## QA Test Results
_To be added by /abc-qa_

## Deployment
_To be added by /abc-deploy_
