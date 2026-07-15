# PROJ-9: Markdown-Export

## Status: Planned
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
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
