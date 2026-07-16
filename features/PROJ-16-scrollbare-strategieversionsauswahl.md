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
**Erstellt:** 2026-07-16 · **Stack:** Next.js + shadcn/ui; bestehendes FastAPI + PostgreSQL unverändert · **Branch:** dev

### A) Komponentenstruktur

```text
BatchConfigurationPage
└── StrategyVersionsCard
    ├── CardHeader
    │   ├── Titel „Strategieversionen"
    │   └── Beschreibung „Nur freigegebene Versionen sind wählbar."
    └── CardContent
        ├── EmptyState (wenn keine freigegebene Version vorhanden ist)
        └── Scrollbare Versionsliste (höchstens 50 % der Browserhöhe)
            └── StrategyVersionRow
                ├── Checkbox
                ├── Strategiename
                ├── Versionsnummer
                └── Freigabedatum
```

Nur die Versionsliste wird scrollbar. Titel, Beschreibung und nachfolgende
Konfigurationskarten bleiben im normalen Seitenfluss sichtbar. Bei wenigen Versionen wächst die
Liste nur mit ihrem Inhalt; auf kleinen Browserhöhen bleibt mindestens eine vollständige Zeile
bedienbar.

### B) Datenmodell

Es werden keine neuen Daten gespeichert. Die Seite verwendet weiterhin:

- die bereits geladenen freigegebenen Strategieversionen mit ID, Name, Versionsnummer und
  Freigabedatum;
- die bestehende Liste ausgewählter Strategieversions-IDs als einzige Quelle für den
  Auswahlzustand;
- den bestehenden Batch-Status, um Checkboxen nach der Bestätigung zu sperren.

Scrollposition und Sichtbarkeit einer Zeile verändern den Auswahlzustand nicht. Nach einem
erneuten Laden bleiben alle weiterhin vorhandenen, vom Batch referenzierten IDs ausgewählt.
PostgreSQL und MinIO sind von dieser Änderung nicht betroffen.

### C) API-Form

Keine neuen oder geänderten Endpunkte:

- `GET /versions` → lädt weiterhin alle freigegebenen Strategieversionen.
- `GET /batches/{id}` → liefert beim Öffnen eines Batches weiterhin dessen ausgewählte IDs.
- `POST /batches` und `PATCH /batches/{id}` → erhalten weiterhin dieselben ausgewählten IDs.
- `GET /batches/{id}/preview` → berechnet die Run-Vorschau weiterhin unverändert.

### D) Tech-Entscheidungen

- **Bestehende Karte erweitern statt neue Auswahlkomponente bauen:** Das Feature ändert nur die
  Darstellung einer bereits funktionierenden Mehrfachauswahl. So bleiben Auswahlregeln,
  Speichern und Run-Vorschau unberührt.
- **Nativer innerer Scrollbereich:** Maus, Trackpad und Tastatur funktionieren ohne eigene
  Scrolllogik. Die Checkboxen bleiben in ihrer normalen Tab-Reihenfolge und per Leertaste
  bedienbar.
- **Höhenbegrenzung relativ zur Browserhöhe:** Die Liste beansprucht höchstens die geforderten
  50 Prozent der sichtbaren Höhe. Eine Mindesthöhe verhindert, dass auf kleinen Fenstern keine
  vollständige Zeile mehr erreichbar ist.
- **Keine Virtualisierung:** Alle Versionen bleiben gleichzeitig Teil der Seite. Das bewahrt
  native Tastaturbedienung und Auswahlzustand und vermeidet zusätzliche Komplexität für die
  derzeit vollständig geladene Liste.
- **Lange Namen bleiben innerhalb der Zeile:** Der Namensbereich darf die Karte nicht
  verbreitern; bei Platzmangel wird der Text innerhalb der verfügbaren Breite umgebrochen oder
  gekürzt, während Versionsnummer und Checkbox bedienbar bleiben.
- **Bestätigte Batches bleiben scrollbar:** Nur die Auswahl ist gesperrt; Lesen und Navigieren
  durch alle ausgewählten Versionen bleiben möglich.

### E) Abhängigkeiten

- Frontend: keine neuen Pakete; vorhandene Next.js-, Tailwind- und shadcn/ui-Bausteine reichen.
- Backend: keine Änderungen und keine neuen Python-Pakete.
- Datenbank/Dateispeicher: keine Migration und keine MinIO-Nutzung.

## QA Test Results
_To be added by /abc-qa_

## Deployment
_To be added by /abc-deploy_
