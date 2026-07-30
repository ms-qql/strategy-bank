# PROJ-24: Robustheitslabor

## Status: Planned
**Created:** 2026-07-30
**Last Updated:** 2026-07-30

## Dependencies
- Requires: PROJ-21 (HAL-Import und Ergebnis-Screening) — liefert Shortlist, Basisresultate und importierte Varianten.
- Requires: PROJ-3 (Verifizierung und Versionierung) — liefert unveränderliche Basis- und Variantenbezüge.
- Optional: PROJ-22 (Regime-Analyse) — liefert Regime-Dominanz als ergänzenden Befund.

## Ziel

Für manuell ausgewählte Strategien werden externe Robustheitsprüfungen
vorbereitet, wieder importiert und transparent ausgewertet. Qualität und
Stabilität bleiben getrennt; ein stabiles schlechtes Ergebnis gilt nicht als
robust.

## User Stories

- Als Trader möchte ich für eine shortlisted Strategie eine kleine, explizite Variantenliste exportieren, damit externe Backtests reproduzierbar ausgeführt werden können.
- Als Trader möchte ich importierte Varianten eindeutig einer Baseline und Prüfstufe zuordnen, damit keine Ergebnisse aus verschiedenen Kampagnen vermischt werden.
- Als Trader möchte ich bei einem Parameter eine Linie und bei zwei Parametern eine Heatmap sehen, damit schmale Spitzen und breite Plateaus erkennbar werden.
- Als Trader möchte ich Parameter, Zeiträume, Timeframes, Assets und Kosten stufenweise prüfen, damit nur tragfähige Kandidaten weitere Tests erhalten.
- Als Trader möchte ich Median, schlechtesten Wert, Spannweite, Erfolgsanteil und Suchumfang sehen, damit der Robustheitsstatus nachvollziehbar bleibt.

## Fachlicher Kampagnenvertrag

Eine Robustheitskampagne enthält:

- Basis-Strategieversion und Basis-Ergebnis
- Prüfstufe: `parameter`, `period`, `timeframe`, `asset` oder `costs`
- explizit gewählte Varianten
- Anzahl erzeugter und tatsächlich betrachteter Varianten
- zugeordnete importierte Ergebnisse
- Status: `nicht geprüft`, `fragil`, `gemischt` oder `robust`

## Acceptance Criteria

### Kampagne und Varianten

- [ ] Nur eine manuell shortlisted Strategieversion kann eine neue Robustheitskampagne starten.
- [ ] Der Nutzer wählt zu variierende Werte explizit; die App erzeugt keinen unbegrenzten oder automatischen Parameter-Sweep.
- [ ] Jede exportierte Variante enthält Kampagnen-ID, Basis-Strategieversion, Prüfstufe, geänderte Werte, unveränderte Kontrollwerte und erwartetes Vergleichsprofil.
- [ ] Der Export ist als lesbare Variantenliste für eine separate Agent-Session verfügbar; die App startet keine Backtests.
- [ ] Importierte Varianten werden über Kampagnen- und Varianten-Identifier automatisch zugeordnet.
- [ ] Fehlen Identifier, darf die App einen Zuordnungsvorschlag machen; ohne eindeutigen Treffer ist eine manuelle Bestätigung erforderlich.
- [ ] Ergebnisse mit abweichenden, nicht zur Variante gehörenden Testfaktoren werden als `nicht vergleichbar` markiert und nicht ausgewertet.
- [ ] Erzeugte, importierte, fehlende und ausgeschlossene Varianten werden zahlenmäßig angezeigt.

### Parameterrobustheit

- [ ] Bei genau einem variierten Parameter zeigt die Detailansicht Calmar über den gewählten Werten als Linie und markiert den Basiswert.
- [ ] Bei genau zwei variierten Parametern zeigt sie eine vollständige Matrix als Heatmap und markiert die Basiszelle.
- [ ] Bei drei oder mehr Parametern gibt es keine mehrdimensionale Grafik; die tabellarische Zusammenfassung bleibt verfügbar.
- [ ] Angezeigt werden mindestens Median Calmar, schlechtester Calmar, Calmar-Spannweite sowie Anteil der Varianten, die alle PROJ-21-Qualitätsgrenzen erfüllen.
- [ ] Fehlende Matrixzellen sind sichtbar und werden nicht interpoliert.
- [ ] Ein Status bleibt `nicht geprüft`, solange weniger als drei gültige Varianten zusätzlich zur Basis vorliegen oder die explizit geplante Matrix unvollständig ist.
- [ ] `robust` gilt, wenn mindestens `70 %` der gültigen Varianten alle Qualitätsgrenzen erfüllen, der Median-Calmar mindestens `0,8` beträgt und für jeden variierten Parameter mindestens ein erfolgreicher Wert auf beiden Seiten des Basiswerts liegt.
- [ ] `fragil` gilt, wenn weniger als `40 %` der gültigen Varianten alle Qualitätsgrenzen erfüllen.
- [ ] Alle übrigen vollständigen Kampagnen erhalten `gemischt`.
- [ ] Der Status wird zusammen mit den verwendeten Schwellen und Einzelwerten erklärt; er ersetzt keine Kennzahl.

### Generalisierungsleiter

- [ ] Die vorgesehenen Stufen werden getrennt geführt: Parameter → Zeitabschnitte → Timeframes → Assets → Kosten.
- [ ] Eine neue Stufe darf nur bewusst durch den Nutzer angelegt werden; es gibt keinen automatischen externen Folgelauf.
- [ ] Für Zeitraum, Timeframe, Asset und Kosten enthält jede Variante genau die geänderte Dimension und hält alle übrigen Vergleichsfaktoren konstant.
- [ ] Ein Kosten-Stresstest speichert die ausdrücklich gewählten Gebühren- und Slippage-Werte; `moderat erhöht` ohne Zahlen ist nicht zulässig.
- [ ] Jede Stufe zeigt ihren eigenen Status und dieselben transparenten Qualitätsanteile; Status verschiedener Stufen werden nicht zu einem Score verrechnet.
- [ ] Die Übersicht unterscheidet lokale Parameterstabilität, zeitliche Stabilität, Timeframe-Portabilität, Asset-Portabilität und Kostenstabilität.
- [ ] Eine Strategie wird nur als insgesamt `robust` bezeichnet, wenn jede vom Nutzer als erforderlich markierte Stufe den Status `robust` besitzt; ungeprüfte Stufen bleiben sichtbar.

### Auswahl- und Regimerisiken

- [ ] Anzahl erzeugter und betrachteter Varianten wird dauerhaft gespeichert und angezeigt.
- [ ] Die UI warnt vor Auswahlbias, wenn nur ein Teil der erzeugten Varianten importiert oder betrachtet wurde.
- [ ] Eine vorhandene PROJ-22-Regime-Dominanz wird als separater Befund angezeigt und verändert den Robustheitsstatus nicht heimlich.

## Edge Cases

- Der Basiswert liegt am Rand der gewählten Parametermenge: `robust` ist nicht erreichbar, weil keine erfolgreiche Nachbarschaft auf beiden Seiten belegt ist.
- Die schlechteste Variante besitzt keinen Calmar-Wert: Sie zählt nicht als erfolgreich und wird als fehlende Qualitätsmessung ausgewiesen.
- Zwei importierte Dateien beanspruchen dieselbe Varianten-ID: Nur die aktuelle Importversion zählt; der Konflikt bleibt im Audit-Trail sichtbar.
- Eine Assetvariante verwendet einen synthetischen Proxy statt desselben Produkttyps: Sie wird als abweichender Testfaktor gekennzeichnet.
- Alle Varianten sind ähnlich, aber unterschreiten die Qualitätsgrenzen: Status ist `fragil`, nicht `robust`.
- Eine Kampagne wird nach Export verändert: Bereits importierte Ergebnisse bleiben an die exportierte Kampagnenversion gebunden.

## Non-Goals

- Keine automatische Parameteroptimierung oder Gewinnerauswahl.
- Kein versteckter Robustheits-Composite-Score.
- Keine automatische Eskalation in die nächste externe Prüfstufe.
- Keine statistische Garantie zukünftiger Performance.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
