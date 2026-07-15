# PROJ-3: Verifizierung und Versionierung

## Status: Architected
**Created:** 2026-07-15
**Last Updated:** 2026-07-15

## Dependencies
- Requires: PROJ-2 (KI-Extraktion) — liefert die zu prüfenden Entwürfe.

## User Stories
- Als Trader möchte ich Regeln, Parameter und offene Unklarheiten eines Entwurfs bearbeiten, um KI-Fehlinterpretationen zu korrigieren.
- Als Trader möchte ich einen Entwurf explizit freigeben, um daraus eine unveränderliche Strategieversion zu machen.
- Als Trader möchte ich, dass eine Strategie mit offenen Unklarheiten nicht freigegeben werden kann, um keine erfundene Logik zu testen.

## Acceptance Criteria
- [ ] Jedes Feld des kanonischen Zwischenformats (PROJ-2) ist im Entwurfsstatus editierbar: Name, These, Kategorie, Richtung, Parameter, Entry-/Exit-Regel, Warm-up, Verhalten bei gleichzeitigem Entry/Exit, Reversal-Verhalten.
- [ ] Bearbeiten eines von der KI vorgeschlagenen Werts markiert diesen als nutzerbestätigt (nicht mehr „Vorschlag").
- [ ] Freigabe („Version einfrieren") ist nur möglich, wenn keine offenen Unklarheiten mehr vorhanden sind und Entry- sowie Exit-Regel als eindeutige boolesche Bedingung vorliegen.
- [ ] Freigabe erzeugt eine neue, unveränderliche Strategieversion mit eigenem `frozen_at`-Zeitstempel. Der zugrunde liegende Entwurf bleibt als Historie erhalten.
- [ ] Jede weitere Änderung an einer bereits freigegebenen Version (z. B. Parameteranpassung) erzeugt zwingend eine neue Versionsnummer, nie ein Überschreiben der bestehenden Version.
- [ ] Eine Strategie, deren Regeln nicht ohne Erfindung fehlender Logik deterministisch formulierbar sind, kann in den Status „nicht testbar" mit Begründungstext gesetzt werden — dieser Status ist von „Entwurf" und „freigegeben" unterscheidbar in der UI.
- [ ] Jede freigegebene Version zeigt lückenlos ihre Herkunft: Quelle, Quell-Hash, Extraktionsmodell, Prompt-Version, alle nutzerseitigen Änderungen gegenüber dem KI-Vorschlag.

## Edge Cases
- Nutzer versucht Freigabe trotz offener Unklarheit: Aktion blockiert, Fehlermeldung „Freigabe nicht möglich — offene Unklarheiten: [Liste]".
- Nutzer ändert eine Regel nach der Freigabe: Änderung ist nur über „Neue Version erstellen" möglich, nicht als Edit der bestehenden Version.
- Zwei Regeln widersprechen sich nach Bearbeitung (z. B. Entry- und Exit-Bedingung identisch): Warnung vor Freigabe, Freigabe bleibt aber technisch möglich (fachliche Prüfung liegt beim Nutzer) — sofern beide als eindeutige boolesche Bedingung vorliegen.
- Strategie wird als „nicht testbar" markiert, aber später doch quantifizierbar (z. B. Quelle nachträglich präzisiert): neuer Entwurf/neue Version aus PROJ-2 nötig, „nicht testbar"-Status bleibt für die alte Version bestehen.
- Warm-up-Anforderung fehlt: Freigabe blockiert bis ein Wert (auch 0) explizit gesetzt ist.

## Technical Requirements (optional)
- Versionen sind append-only in der Persistenz (kein UPDATE auf freigegebene Felder, nur INSERT neuer Version-Rows).
- Jede Version referenziert eindeutig ihren Entwurf und ihre Quelle.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-15 · **Stack:** Next.js 16 (App Router) + shadcn/ui / FastAPI + raw SQL / PostgreSQL · **Branch:** master

### A) Komponentenstruktur (UI — erweitert PROJ-2)
```
QuellenPage (app/quellen/page.tsx — aus PROJ-1/2)
└── EntwurfCard (aus PROJ-2)
    ├── StatusBadge
    └── Button "Entwurf bearbeiten" → navigiert zu /entwuerfe/{id}

EntwurfEditPage (app/entwuerfe/[id]/page.tsx — neu)
├── EntwurfKopf (Name, Status, Hinweis bei Entwurf aus Version)
├── Bearbeitungsformular
│   ├── Stammdaten: These, Kategorie, Richtung
│   ├── Regeln: Entry, Exit, Warm-up, Gleichzeitigkeit, Reversal
│   ├── Parameter: Werte bearbeiten, Vorschlag-Status erlischt
│   └── Offene Unklarheiten: sichtbar mit „Schließen“-Aktion
├── Herkunft & Änderungen (einklappbar: Quelle, Hash, Modell, Prompt, KI-Diff)
├── Versionshistorie (einklappbar: Version, Zeitpunkt, „neuen Entwurf erstellen“)
└── Aktionsleiste
    ├── sichtbare Liste der noch blockierenden Freigabe-Bedingungen
    ├── „Version freigeben“
    └── „Als nicht testbar markieren“
```

Die gleiche Seite zeigt eine freigegebene Version nur lesend, wenn sie aus der
Versionshistorie geöffnet wird. Eine separate Versions-Detailseite, eine sticky
Timeline und eine dauerhafte Provenienz-Card entfallen. Kategorie und Richtung
verwenden die vorhandenen nativen Auswahlfelder; dafür wird keine UI-Komponente
oder Abhängigkeit ergänzt.

### B) Datenmodell (Klartext)
```
strategy_drafts (aus PROJ-2, erweitert)
  + family_id: stabile ID aller Versionen derselben Strategie
  + parent_version_id: Version, aus der ein neuer Entwurf erstellt wurde (optional)
  + original_snapshot: unveränderlicher KI-Ausgangszustand für den späteren Diff
  + frozen_at und Status „freigegeben“
  - Beim ersten Entwurf ist family_id dessen eigene ID; beim Klonen wird sie übernommen.

strategy_versions (NEU, append-only)
  - Referenziert Draft und family_id; Versionsnummer ist innerhalb family_id eindeutig.
  - Enthält einen vollständigen Snapshot aller Strategiefelder, Parameter und Provenienz
    (Quelle, Quell-Hash, Extraktionsmodell, Prompt-Version, frozen_at).
  - Änderungen und Löschungen sind auf Datenbankebene gesperrt.

version_parameters (NEU, 1:n je strategy_versions, append-only)
  - Enthält die zum Freeze gültigen Parameterwerte ohne Vorschlag-Markierung.
  - Änderungen und Löschungen sind auf Datenbankebene gesperrt.

draft_open_questions (aus PROJ-2) bleibt bis zur Freigabe editierbar.
  - Beim Freeze müssen keine offenen Einträge mehr vorhanden sein; daher wird kein
    leerer Fragen-Snapshot als eigene Versionstabelle gespeichert.
```

Der KI-Ausgangszustand bleibt als ein Snapshot direkt am Entwurf erhalten. Der
Änderungs-Diff wird beim Lesen einer Version aus diesem Ausgangszustand und dem
Versionssnapshot gebildet; eine zusätzliche Spiegel- oder Diff-Tabelle ist nicht nötig.

### C) API-Form (nur Endpunkte)
```
PATCH  /drafts/{id}                    # bearbeitet Entwurfsfelder und Parameter;
                                       # geänderte Parameter sind bestätigt
DELETE /drafts/{id}/open-questions/{qid}
POST   /drafts/{id}/freeze             # Gate prüfen, unveränderliche Version erzeugen
POST   /drafts/{id}/mark-untestable    # Status="nicht testbar" + Begründung
POST   /versions/{id}/new-draft        # Klont die Version als neuen Entwurf derselben family_id
GET    /drafts/{id}/versions           # Versionshistorie der family_id
GET    /versions/{id}                  # vollständige, nur lesbare Version inkl. berechnetem KI-Diff
```

Status-Codes wie gewohnt: 200/201/204 Erfolg, 404 Draft nicht gefunden, 422 Validierungs-/Gate-Fehler
(Freeze) bzw. Foreign-Key-Verletzung (zentraler Handler aus PROJ-2).

### D) Tech-Entscheidungen (warum)
- **Versionen sind vollständige Snapshots, keine Pointer:** Nur ein eigener Snapshot schützt einen freigegebenen Stand vor späteren Entwurfsänderungen. Die Datenbank sperrt sowohl Änderungen als auch Löschungen.
- **Eine family_id ist die Versionskette:** Sie verbindet Erstentwurf und alle daraus erzeugten Entwürfe zuverlässig. Dadurch bleibt die Versionsnummer immer eindeutig und lückenlos, unabhängig von wechselnden Draft-IDs.
- **Ein Ausgangssnapshot reicht für Nachvollziehbarkeit:** Er hält den KI-Vorschlag fest; der sichtbare Diff entsteht beim Lesen. Spiegel-, Trigger- und Diff-Tabellen würden dieselben Informationen mehrfach speichern.
- **Der Entwurf bleibt der einzige Bearbeitungsort:** Nach der Freigabe erzeugt „Neue Version erstellen“ einen klonbaren Entwurf. Bereits freigegebene Versionen können nur angesehen werden.
- **Freigabe wird sofort erklärt, aber serverseitig entschieden:** Die UI zeigt offene Fragen, fehlende Regeln, fehlendes Warm-up und die ausstehende Bestätigung „Regeln sind deterministisch formuliert“ direkt an. Der Server prüft dieselben Bedingungen verbindlich. Eine eigene Regel-Sprache wird im MVP nicht gebaut.
- **Offene Fragen werden nur geschlossen, nicht versioniert:** Eine Freigabe mit offenen Fragen ist ausgeschlossen; ein Snapshot wäre daher stets leer. Neue Unklarheiten führen im MVP entweder zur Korrektur der Regeln oder zum Status „nicht testbar“.
- **Eine Detailseite statt mehrerer Ansichten:** Bearbeitung, Versionen und Herkunft erscheinen kontextbezogen auf derselben Seite. Das reduziert Navigation und vermeidet doppelte Komponenten.

### E) Abhängigkeiten
- Backend (Python): keine neuen Pakete. Bestehende Datenbank- und Exception-Helfer werden erweitert.
- Frontend (Next.js): keine neue UI-Abhängigkeit. Bestehender API-Client und Zod-Schemas erhalten die neuen Responses.
- Tests: Freigabe-Gate, Versionsnummer je family_id, gesperrte Änderung **und Löschung** einer Version sowie Versions-Diff.

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
