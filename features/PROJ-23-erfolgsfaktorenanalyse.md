# PROJ-23: Erfolgsfaktorenanalyse

## Status: Planned
**Created:** 2026-07-30
**Last Updated:** 2026-07-30

## Dependencies
- Requires: PROJ-2 (KI-Extraktion) — liefert verifizierbare Regel- und Indikatorinformationen.
- Requires: PROJ-3 (Verifizierung und Versionierung) — liefert unveränderliche Strategie-Snapshots.
- Requires: PROJ-21 (HAL-Import und Ergebnis-Screening) — liefert vergleichbare Ergebnisse und die feste Erfolgsgruppe.
- Optional: PROJ-22 (Regime-Analyse) — ergänzt Regime als weitere Vergleichsdimension, blockiert die Basisanalyse aber nicht.

## Ziel

Die Strategy Bank zeigt, welche bestätigten Strategieeigenschaften in der
festen Erfolgsgruppe häufiger auftreten als im vergleichbaren Gesamtbestand.
Jede Aussage bleibt durch Zähler, Nenner und Berechnungsregel nachvollziehbar.

## User Stories

- Als Trader möchte ich verwendete Indikatoren und Regelarchetypen strukturiert bestätigen, damit die Analyse nicht auf unkontrolliertem Freitext beruht.
- Als Trader möchte ich Erfolgsquote und Lift je Merkmal sehen, damit häufige Gewinnermerkmale nicht mit allgemein häufigen Merkmalen verwechselt werden.
- Als Trader möchte ich Stichprobengröße und Median-Calmar direkt daneben sehen, damit kleine Gruppen nicht überbewertet werden.
- Als Trader möchte ich Long-only, Short-only und kombinierte Ergebnisse getrennt vergleichen, damit strukturelle Long-Tendenzen sichtbar werden.
- Als Trader möchte ich Einfachheit über getrennte Zählwerte untersuchen, ohne einen undurchsichtigen Komplexitäts- oder Composite-Score.

## Merkmalsvertrag

Jede unveränderliche Strategieversion kann folgende bestätigbare Merkmale
tragen:

- `indicators[]`
- `entry_archetype`
- `exit_archetype`
- `indicator_count`
- `filter_count`
- `condition_count`
- `parameter_count`

Kategorie, Richtung und Crypto-MTS-Eignung werden aus den bereits
versionierten Feldern wiederverwendet.

## Acceptance Criteria

### Erfassung und Bestätigung

- [ ] Merkmale gehören zu genau einer unveränderlichen Strategieversion; Änderungen erzeugen eine neue Version oder einen neuen bestätigten Merkmalssnapshot.
- [ ] Die KI darf Merkmale vorschlagen, aber Vorschlag und bestätigter Wert sind sichtbar unterscheidbar.
- [ ] Unbestätigte Vorschläge werden nicht in Erfolgsquoten, Lift oder Einfachheitsvergleiche eingerechnet.
- [ ] Der Nutzer kann vorgeschlagene Indikatoren, Entry-/Exit-Archetypen und Zählwerte vor der Bestätigung korrigieren.
- [ ] Jede Änderung eines bestätigten Merkmals setzt dessen Bestätigungsstatus zurück.
- [ ] Zählwerte werden getrennt angezeigt; es gibt keinen daraus gebildeten Einfachheitsscore.
- [ ] Leere Indikatorlisten sind zulässig, wenn die Strategie beispielsweise ausschließlich Preis-/Zeitregeln verwendet.

### Vergleichsgrundlage

- [ ] Die Analyse arbeitet immer innerhalb genau einer direkt vergleichbaren PROJ-21-Profilgruppe.
- [ ] Die Erfolgsgruppe verwendet unverändert Calmar `≥ 0,8`, Sortino `≥ 0,5` und mindestens `6 Trades pro getestetem Jahr`.
- [ ] Varianten oder wiederholte Importe desselben aktuellen Ergebnisses werden innerhalb einer Analyse nicht doppelt gezählt.
- [ ] Ein Ergebnis ohne bestätigte Merkmale bleibt im Ergebnis-Screener sichtbar, wird aber in der Merkmalsanalyse als `Merkmale unbestätigt` ausgeschlossen.
- [ ] Aktive Filter und die Anzahl einbezogener beziehungsweise ausgeschlossener Ergebnisse werden über der Analyse angezeigt.

### Kohortentabelle

- [ ] Die Tabelle zeigt je Merkmalswert mindestens `Erfolgreich`, `Gesamt`, `Erfolgsquote`, `Lift` und `Median Calmar`.
- [ ] `Erfolgsquote` ist `erfolgreiche Ergebnisse mit Merkmal / alle Ergebnisse mit Merkmal`.
- [ ] `Lift` ist `Merkmalsanteil in der Erfolgsgruppe / Merkmalsanteil im gesamten aktiven Vergleichsbestand`.
- [ ] Ist ein Nenner `0`, wird der Wert als `nicht verfügbar` angezeigt und nicht durch `0` oder unendlich ersetzt.
- [ ] Zähler und Nenner werden immer gemeinsam angezeigt, beispielsweise `8/17 erfolgreich`.
- [ ] Die Tabelle ist nach Erfolgsquote, Lift, Stichprobengröße und Median Calmar sortierbar; nicht verfügbare Werte stehen am Ende.
- [ ] Balken in Quote- und Lift-Zellen dürfen die Zahlen unterstützen, aber nicht ersetzen.
- [ ] Kategorien, Richtung, Indikatoren, Entry-Archetyp, Exit-Archetyp, MTS-Eignung und die vier Einfachheitszählwerte sind auswählbare Analyseachsen.
- [ ] Richtung kann als Matrix `long-only`, `short-only`, `kombiniert` dargestellt werden.
- [ ] PROJ-22-Regime dürfen nur ergänzt werden, wenn Modellversion und Datenabdeckung für die aktive Vergleichsgruppe einheitlich sind.

### Sprache und Interpretation

- [ ] Die UI verwendet `Zusammenhang`, `häufiges Merkmal` oder `Lift`; sie bezeichnet kein Merkmal als Ursache für Erfolg.
- [ ] Es gibt keinen Composite Score, keine automatische Strategieempfehlung und keine versteckte Mindeststichprobe.
- [ ] Kleine Gruppen bleiben sichtbar; ihre Stichprobengröße wird nicht durch eine pauschale Qualitätsfarbe verdeckt.

## Edge Cases

- Die Erfolgsgruppe ist leer: Erfolgsquote ist `0/N`, Lift bleibt nicht verfügbar und die UI erklärt „Keine Ergebnisse erfüllen die aktuelle Erfolgsdefinition.“
- Alle Ergebnisse gehören zur Erfolgsgruppe: Lift ist für jedes vorhandene Merkmal `1,0`; die App behauptet keine Differenzierung.
- Ein Indikator kommt mehrfach in einer Strategie vor: Er zählt für die Merkmalsprävalenz einmal, nicht pro Verwendung.
- Ein Ergebnis besitzt mehrere Indikatoren: Es trägt zu jeder passenden Indikatorzeile bei; die Zeilensummen müssen deshalb nicht der Zahl der Strategien entsprechen.
- Nur eine Strategie enthält ein Merkmal und ist erfolgreich: `1/1` wird gezeigt, ohne statistische Signifikanzbehauptung.
- Ein Merkmalswert wird nachträglich korrigiert: Historische Auswertungen mit altem Snapshot bleiben nachvollziehbar.

## Non-Goals

- Keine Kausalitätsanalyse oder statistische Signifikanzprüfung.
- Kein automatisches Regel-Mining aus Performancekurven.
- Kein frei wachsender unbestätigter Tag-Bestand.
- Kein Gesamtwert für Einfachheit oder Strategiequalität.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
