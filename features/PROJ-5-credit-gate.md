# PROJ-5: Credit-Gate

## Status: Planned
**Created:** 2026-07-15
**Last Updated:** 2026-07-15

## Dependencies
- Requires: PROJ-4 (Batch-Konfiguration) — liefert die Liste geplanter Runs.

Credit-Annahmen und verfügbare trader.dev-Aktionen stammen verbindlich aus `docs/trader-dev-capability-spike.md`.

## User Stories
- Als Trader möchte ich vor dem Start eines Batches die erwartete Credit-Anzahl sehen, um keine Überraschungen beim Verbrauch zu erleben.
- Als Trader möchte ich ein hartes Credit-Maximum je Batch festlegen, um versehentlich hohe Kosten zu verhindern.
- Als Trader möchte ich den Batch explizit bestätigen, bevor externe Aktionen ausgelöst werden.

## Acceptance Criteria
- [ ] Vor dem Start zeigt die App die erwartete Anzahl externer trader.dev-Aktionen (für den MVP: 1 Credit je geplantem Run, keine Schätzspanne nötig).
- [ ] Die App zeigt den aktuellen Credit-Kontostand (via `get_credits`) und den verbleibenden Bestand nach dem geplanten Batch.
- [ ] Der Nutzer legt vor dem Start ein hartes Credit-Maximum für den Batch fest (Default: exakte Anzahl geplanter Runs).
- [ ] Reicht der aktuelle Credit-Kontostand nicht für den geplanten Batch, startet der Batch nicht; verständliche Fehlermeldung mit fehlender Differenz.
- [ ] Der Nutzer muss den Batch (Runs-Liste) und das Credit-Maximum in einem expliziten Bestätigungsschritt freigeben, bevor die Queue (PROJ-6) etwas auslöst.
- [ ] Tarifhöhe, Credit-Menge und Reset-Zeitraum sind aus `get_credits` gelesene, nicht im Code fest hinterlegte Werte.
- [ ] Kein Privacy-Check ist Teil dieses Gates — die Verantwortung für ausschließlich öffentlich zulässige Strategieinhalte liegt beim Nutzer (Produktentscheidung, siehe PRD Abschnitt 4).

## Edge Cases
- Credit-Maximum wird während der Konfiguration nachträglich reduziert (weniger als geplante Runs): App verlangt Reduktion der Run-Auswahl oder Erhöhung des Maximums vor Bestätigung.
- Retry eines fehlgeschlagenen Runs (siehe PROJ-6) nach Batch-Abschluss: neue, bewusste Credit-Gate-Prüfung für genau diesen einen Run, kein automatischer Verbrauch aus dem ursprünglichen Maximum.
- `get_credits` liefert einen Fehler oder ist nicht erreichbar: Batch-Start blockiert, verständliche Fehlermeldung statt stillem Weiterlaufen mit veraltetem Stand.
- Credit-Kontostand ändert sich zwischen Anzeige und Bestätigung (z. B. durch parallele Nutzung außerhalb der App): Bestätigung prüft den Stand erneut unmittelbar vor Queue-Start.

## Technical Requirements (optional)
- Persistenz: bestätigtes Credit-Maximum und Kontostand-Snapshot zum Bestätigungszeitpunkt werden im Audit-Trail (PROJ-8) mitgespeichert.
- MVP-Planungsannahme: 1.000 Credits pro Woche. Credit-Kosten und Reset-Zeitraum werden in P1 erneut geprüft.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
