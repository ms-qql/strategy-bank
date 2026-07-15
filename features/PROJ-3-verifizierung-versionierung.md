# PROJ-3: Verifizierung und Versionierung

## Status: Planned
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
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
