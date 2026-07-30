# PROJ-23: Erfolgsfaktorenanalyse

## Status: Architected
**Created:** 2026-07-30
**Last Updated:** 2026-07-30

## Dependencies
- Optional: PROJ-3 (Verifizierung und Versionierung) — liefert Kategorie, Richtung und MTS-Eignung als zusätzliche Achsen, sofern ein Ergebnis zugeordnet ist.
- Requires: PROJ-21 (HAL-Import und Ergebnis-Screening) — liefert vergleichbare Ergebnisse und die feste Erfolgsgruppe.
- Optional: PROJ-22 (Regime-Analyse) — ergänzt Regime als weitere Vergleichsdimension, blockiert die Basisanalyse aber nicht.

## Ziel

Ein gelegentlich gefahrener Analyselauf zeigt als Momentaufnahme, welche
Strategieeigenschaften in der festen Erfolgsgruppe häufiger auftreten als im
vergleichbaren Gesamtbestand. Der Lauf speichert Merkmale, Kennzahlen und die
beteiligten Strategien mit Zeitstempel und verändert nichts am Strategiebestand.
Jede Aussage bleibt durch Zähler, Nenner und Berechnungsregel nachvollziehbar.

## User Stories

- Als Trader möchte ich alle ein bis zwei Wochen einen Analyselauf starten, ohne vorher Merkmale pflegen zu müssen.
- Als Trader möchte ich zu jedem Lauf sehen, welche Strategien und Merkmale darin steckten, damit jede Zahl bis zur Einzelzeile prüfbar ist.
- Als Trader möchte ich Erfolgsquote und Lift je Merkmal sehen, damit häufige Gewinnermerkmale nicht mit allgemein häufigen Merkmalen verwechselt werden.
- Als Trader möchte ich Stichprobengröße und Median-Calmar direkt daneben sehen, damit kleine Gruppen nicht überbewertet werden.
- Als Trader möchte ich Long-only, Short-only und kombinierte Ergebnisse getrennt vergleichen, damit strukturelle Long-Tendenzen sichtbar werden.
- Als Trader möchte ich Einfachheit über getrennte Zählwerte untersuchen, ohne einen undurchsichtigen Komplexitäts- oder Composite-Score.

## Merkmalsvertrag

Merkmale werden je Analyselauf aus dem importierten Pine-Code des jeweiligen
Ergebnisses abgeleitet und im Lauf gespeichert. Sie hängen **nicht** an der
Strategie und verändern keine Strategieversion:

- `indicators[]`
- `indicator_count`
- `parameter_count`
- `entry_archetype` (abgeleitet)
- `exit_archetype` (abgeleitet)

Kategorie, Richtung und Crypto-MTS-Eignung werden, sofern das Ergebnis einer
Strategieversion zugeordnet ist, zum Laufzeitpunkt mitkopiert.

## Acceptance Criteria

### Analyselauf und Merkmalsableitung

- [ ] Der Nutzer startet einen Analyselauf mit einer Aktion; die App fragt nichts ab, was sie selbst ermitteln kann.
- [ ] Ein Analyselauf verändert weder Strategien noch Strategieversionen noch importierte Ergebnisse.
- [ ] Merkmale werden deterministisch aus dem Pine-Code des Ergebnisses abgeleitet; es läuft kein KI-Aufruf und keine manuelle Bestätigung.
- [ ] Ein Ergebnis ohne Pine-Code wird nicht ausgewertet und im Lauf als `ohne Merkmale` ausgewiesen.
- [ ] Ein Indikator zählt je Ergebnis einmal, unabhängig davon, wie oft er im Code vorkommt.
- [ ] Nicht ableitbare Archetypen bleiben `nicht verfügbar`; sie werden nicht geraten.
- [ ] Zählwerte werden getrennt angezeigt; es gibt keinen daraus gebildeten Einfachheitsscore.
- [ ] Leere Indikatorlisten sind zulässig, wenn eine Strategie ausschließlich Preis-/Zeitregeln verwendet.

### Läufe und Nachvollziehbarkeit

- [ ] Jeder Lauf speichert seinen Zeitpunkt, die Erfolgsdefinition und die Zahl der einbezogenen und ausgeschlossenen Ergebnisse.
- [ ] Jeder Lauf listet die einbezogenen Ergebnisse mit Strategiename und den zu diesem Zeitpunkt abgeleiteten Merkmalen.
- [ ] Frühere Läufe bleiben unverändert lesbar, auch wenn später Ergebnisse hinzukommen oder sich ändern.
- [ ] Ein Lauf kann gelöscht werden; das entfernt keine Ergebnisse und keine Strategiedaten.

### Vergleichsgrundlage

- [ ] Die Analyse arbeitet immer innerhalb genau einer direkt vergleichbaren PROJ-21-Profilgruppe.
- [ ] Die Erfolgsgruppe verwendet unverändert Calmar `≥ 0,8`, Sortino `≥ 0,5` und mindestens `6 Trades pro getestetem Jahr`.
- [ ] Varianten oder wiederholte Importe desselben aktuellen Ergebnisses werden innerhalb einer Analyse nicht doppelt gezählt.
- [ ] Ein Ergebnis ohne ableitbare Merkmale bleibt im Ergebnis-Screener sichtbar, wird aber im Analyselauf als `ohne Merkmale` ausgeschlossen.
- [ ] Aktive Filter und die Anzahl einbezogener beziehungsweise ausgeschlossener Ergebnisse werden über der Analyse angezeigt.

### Kohortentabelle

- [ ] Die Tabelle zeigt je Merkmalswert mindestens `Erfolgreich`, `Gesamt`, `Erfolgsquote`, `Lift` und `Median Calmar`.
- [ ] `Erfolgsquote` ist `erfolgreiche Ergebnisse mit Merkmal / alle Ergebnisse mit Merkmal`.
- [ ] `Lift` ist `Merkmalsanteil in der Erfolgsgruppe / Merkmalsanteil im gesamten aktiven Vergleichsbestand`.
- [ ] Ist ein Nenner `0`, wird der Wert als `nicht verfügbar` angezeigt und nicht durch `0` oder unendlich ersetzt.
- [ ] Zähler und Nenner werden immer gemeinsam angezeigt, beispielsweise `8/17 erfolgreich`.
- [ ] Die Tabelle ist nach Erfolgsquote, Lift, Stichprobengröße und Median Calmar sortierbar; nicht verfügbare Werte stehen am Ende.
- [ ] Balken in Quote- und Lift-Zellen dürfen die Zahlen unterstützen, aber nicht ersetzen.
- [ ] Kategorie, Richtung, Indikatoren, Entry-Archetyp, Exit-Archetyp, MTS-Eignung, Indikatorzahl und Parameterzahl sind auswählbare Analyseachsen.
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
- Ein Ergebnis wird nach einem Lauf erneut importiert oder korrigiert: Der alte Lauf behält seine Zahlen; erst ein neuer Lauf zeigt den neuen Stand.
- Ein Ergebnis ist keiner Strategieversion zugeordnet: Es zählt trotzdem mit; die achsen aus der Strategieversion (Kategorie, Richtung, MTS) sind für diese Zeile `nicht verfügbar`.

## Non-Goals

- Keine Kausalitätsanalyse oder statistische Signifikanzprüfung.
- Kein automatisches Regel-Mining aus Performancekurven.
- Kein frei wachsender unbestätigter Tag-Bestand.
- Kein Gesamtwert für Einfachheit oder Strategiequalität.
- Keine Merkmalspflege an Strategien oder Strategieversionen; die Analyse ist reine Beobachtung.
- Kein KI-Aufruf und kein Bestätigungs-Workflow für Merkmale.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-30 · **Stack:** Next.js 16 (App Router, shadcn/ui) + FastAPI + PostgreSQL (Dokploy, single-tenant) · **Branch:** dev

### Grundidee

Ein Analyselauf ist eine **Momentaufnahme**: Knopf drücken, die App liest alle
aktuellen importierten Ergebnisse, leitet aus deren Pine-Code die Merkmale ab, speichert
das Ergebnis mit Zeitstempel und zeigt die Kohortentabelle. Der Lauf ist ein reiner
Lesevorgang — Strategien, Strategieversionen und Importe werden nicht angefasst.

Das passt zur Nutzung: alle ein bis zwei Wochen einmal ausführen, ansehen, alte Läufe
vergleichen. Kein Pflegeaufwand zwischen den Läufen.

### A) Komponentenstruktur

Eine neue Seite, sonst nichts:

```
ErfolgsfaktorenSeite
├── AnalyseStartenAktion („Analyse jetzt fahren")
├── LaufListe (chronologisch)
│   └── LaufZeile → Zeitpunkt · „54 von 68 Ergebnissen ausgewertet" · Löschen
└── LaufDetail (nach Auswahl eines Laufs)
    ├── LaufKopf: Zeitpunkt · Erfolgsdefinition im Klartext · einbezogen/ausgeschlossen
    │             mit Ausschlussgründen („ohne Pine-Code", „nicht vergleichbar")
    ├── AchsenWahl (Indikator · Entry-Archetyp · Exit-Archetyp · Kategorie · Richtung ·
    │               MTS-Eignung · Indikatorzahl · Parameterzahl)
    ├── KohortenTabelle
    │   └── je Zeile: Merkmalswert · „8/17 erfolgreich" · Erfolgsquote · Lift · Median Calmar
    └── BeteiligteStrategien (welche Ergebnisse mit welchen Merkmalen im Lauf steckten,
                              aufklappbar, damit jede Zahl bis zur Einzelzeile prüfbar bleibt)
```

Keine Merkmalspflege-Oberfläche, kein Bestätigungsschritt, keine Eingriffe in bestehende
Seiten außer einem Sidebar-Eintrag.

### B) Datenmodell (Klartext)

Zwei Tabellen, beide vollständig getrennt von Strategien und Importen:

**Analyselauf**
- Zeitpunkt, verwendete Erfolgsdefinition, Zahl der einbezogenen und ausgeschlossenen
  Ergebnisse mit Gründen
- löschbar; das Löschen berührt nichts außerhalb des Laufs

**Lauf-Zeile** — eine je einbezogenem Ergebnis, eingefroren zum Laufzeitpunkt:
- Strategiename und, falls zugeordnet, ein Verweis auf die Strategieversion (nur als Link
  zum Nachschlagen, nicht als Abhängigkeit)
- die zum Laufzeitpunkt geltenden Kennzahlen: Calmar, Sortino, Trades pro Jahr, Erfolg ja/nein
- die abgeleiteten Merkmale: Indikatorliste, Indikatorzahl, Parameterzahl,
  Entry-Archetyp, Exit-Archetyp
- die mitkopierten Felder aus der Strategieversion, falls vorhanden: Kategorie, Richtung,
  MTS-Eignung

Die Kohortentabelle wird beim Anzeigen aus diesen Zeilen gerechnet, nicht zusätzlich
gespeichert. Dieselben Zeilen ergeben immer dieselben Zahlen, und jede Achse lässt sich
ohne neuen Lauf auswerten.

### C) API-Zuschnitt

```
POST   /analysis/runs           → neuen Lauf erzeugen (liest, schreibt nur den Lauf)
GET    /analysis/runs           → Liste der Läufe mit Zeitpunkt und Umfang
GET    /analysis/runs/{id}      → Lauf mit Kohortentabelle für die gewählte Achse
                                  und den beteiligten Ergebnissen
DELETE /analysis/runs/{id}      → Lauf verwerfen
```

Vier Endpunkte, keine Änderung an bestehenden Routen.

### D) Technische Entscheidungen (mit Begründung)

1. **Der Lauf ist die Einheit, nicht das Merkmal.** Alles, was eine Auswertung ausmacht,
   liegt in einem Lauf: Merkmale, Kennzahlen, Erfolgsdefinition, Zeitpunkt. Damit ist ein
   alter Lauf für immer nachvollziehbar, ohne dass irgendwo anders etwas versioniert
   werden muss.
2. **Strategien und Strategieversionen bleiben unberührt.** Keine neuen Felder, keine neuen
   Versionen, keine Bestätigungskennzeichen. Die Analyse ist Beobachtung, kein Eingriff —
   und kann deshalb nie etwas kaputt machen, was für Backtests gebraucht wird.
3. **Merkmale kommen deterministisch aus dem Pine-Code.** Der Code liegt seit PROJ-21 je
   Ergebnis in der Datenbank und sagt exakt, welche Indikatoren gerechnet und wie viele
   Eingabeparameter definiert wurden. Kein KI-Aufruf, keine Kosten, bei gleichem Code
   immer dasselbe Ergebnis.
4. **Archetypen werden aus typischen Code-Mustern abgeleitet, sonst bleiben sie leer.**
   Ein Kreuzen zweier Linien, ein Ausbruch über ein Hoch, ein fester Stop, ein Trailing-Stop
   oder ein Ausstieg auf Gegensignal sind im Code klar erkennbar. Alles andere bleibt
   ausdrücklich „nicht verfügbar" — geraten wird nichts.
5. **Kein Bestätigungs-Workflow.** Bei 68 Strategien wäre das die eigentliche Arbeit des
   Features gewesen, für eine Auswertung, die alle ein bis zwei Wochen läuft. Falsche
   Ableitungen fallen in der aufklappbaren Einzelzeilen-Ansicht auf; das reicht für eine
   Beobachtungsanalyse.
6. **Die Zahlen kommen aus dem Lauf, nicht aus der Live-Datenbank.** Ein Lauf von vor zwei
   Wochen zeigt den Stand von vor zwei Wochen, auch wenn seither importiert wurde. Genau
   das ist der Zweck einer Momentaufnahme.
7. **Die Kohortentabelle wird gerechnet, nicht gespeichert.** Sonst müsste jede Achse
   einzeln abgelegt werden und ein neuer Achsenwunsch bräuchte einen neuen Lauf.
8. **Ein Lauf umfasst eine Vergleichsgruppe.** Ergebnisse mit abweichendem Asset,
   Timeframe oder Gebührenmodell werden ausgeschlossen und als solche gezählt — sonst
   erschienen Unterschiede der Testbedingungen als Merkmalswirkung. Heute liegt ohnehin
   der gesamte Bestand auf BTCUSDT 4h.
9. **Je Strategieversion zählt das aktuelle Ergebnis einmal.** Ältere Importversionen und
   Dubletten fallen vor der Auswertung weg, damit ein mehrfach hochgeladenes Ergebnis die
   Statistik nicht doppelt gewichtet.
10. **Nenner null ergibt „nicht verfügbar".** Weder null noch unendlich — beides wäre eine
    Aussage, die die Daten nicht hergeben.
11. **Keine Kausalsprache, keine Signifikanz, kein Score.** Die Tabelle zeigt Zähler,
    Nenner, Quote, Lift und Median-Calmar. `1/1` steht als `1/1` da.

### E) Abhängigkeiten

- Backend: keine neuen Pakete. Die Merkmalsableitung ist Mustererkennung über den bereits
  gespeicherten Pine-Text.
- Frontend: keine neuen Pakete.
- Datenbank: eine Migration mit zwei Tabellen und einem Index auf den Lauf.

### F) Auswirkungen und Reihenfolge

- Einzige Voraussetzung ist PROJ-21: importierte Ergebnisse mit Pine-Code und Kennzahlen.
  PROJ-2, PROJ-3 und PROJ-22 werden nur gelesen, wenn vorhanden, und blockieren nichts.
- Bestehende Seiten ändern sich nicht; die Sidebar bekommt einen Eintrag „Erfolgsfaktoren".
- Aufwand liegt fast vollständig in der Merkmalsableitung aus Pine — der Rest ist eine
  Tabelle über zwei Datenbanktabellen.


## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
