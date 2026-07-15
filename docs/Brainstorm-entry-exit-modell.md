# Brainstorm: Entry-/Exit-Modell für Strategy Bank

**Datum:** 2026-07-15  
**Status:** Konvergiert – Empfehlung zur Übernahme in Requirements/Architektur

## Session-Setup

- **Thema:** Strategien mit dauerhaftem Long/Short-Wechsel von Strategien mit einzelnen Entry-Signalen und späterem Flat-Exit unterscheiden.
- **Ziel:** Einen reproduzierbaren Standard-Exit für Strategien ohne eigenen Exit festlegen und sauber in Extraktion, Verifizierung, Versionierung und Backtest einbauen.
- **Ansatz:** Praktische, progressive Analyse: fachliche Achsen trennen, Exit-Kandidaten vergleichen, kleinste tragfähige Architektur festlegen.
- **Kontext:** Solo-Nutzer; Next.js/FastAPI/PostgreSQL; Pine-Script-v5-Ausführung über trader.dev; Default-Timeframe 4 Stunden; freigegebene Strategieversionen sind unveränderliche Snapshots.
- **Randbedingungen:** Keine still erfundene Quellenregel, gleiche Backtest-Annahmen für Vergleichbarkeit, symmetrische Long-/Short-Logik, kein unnötiger Varianten- oder Parameter-Sweep.

## Initial Framing

Das bisherige Modell behandelt jede Strategie so, als müsse sie eine eigene `entry_rule` und `exit_rule` aus der Quelle besitzen. Das passt nicht zu zwei real unterschiedlichen Signalmodellen:

1. **Positionssignal / Stop-and-Reverse:** Das Signal bestimmt die Zielposition `long` oder `short`. Ein SMA-Crossover kann direkt zwischen beiden wechseln; im kombinierten Lauf ist die Strategie praktisch immer investiert.
2. **Entry plus Flat-Exit:** Ein Long- oder Short-Signal eröffnet eine Position. Ohne separates Exit-Signal bleibt die Position fälschlich unbegrenzt offen. Ein Exit muss die Zielposition wieder auf `flat` setzen.

Die bestehende `direction` (`kombiniert`, `long-only`, `short-only`) beschreibt nur, welche Handelsrichtungen erlaubt sind. Sie darf nicht gleichzeitig das Positionsverhalten ausdrücken.

Die herangezogene Markdown-Quelle „Entry and Exit Confessions of a Champion Trader“ enthält elf Exit-Bausteine. Sie empfiehlt den **Timed Exit** als einfachsten ersten Test; als weitere Kandidaten nennt sie unter anderem ATR-Trailing, Percentile Exit und Profit Protector.

## Divergenz

### Fachliches Modell

**[Modell #1] Fehlenden Exit direkt mit Text auffüllen**  
_Concept:_ Bei der Extraktion wird jede leere Exit-Regel automatisch durch einen Standardtext ersetzt.  
_Novelty:_ Kleinste Änderung am bisherigen Schema, aber Herkunft und tatsächliche Quellenregel werden vermischt.

**[Modell #2] Zwei Positionsmodi**  
_Concept:_ `position_mode` unterscheidet `signal_reversal` und `entry_exit`. Richtung bleibt eine unabhängige Achse.  
_Novelty:_ Bildet den tatsächlichen Positions-Lebenszyklus ab, ohne eine neue Regel-Engine einzuführen.

**[Modell #3] Einheitliches Zielpositionssignal**  
_Concept:_ Jede Strategie erzeugt intern nur noch `+1`, `0` oder `-1`; Entry und Exit sind bloß Wege zu diesem Zielwert.  
_Novelty:_ Sehr sauberes Ausführungsmodell, würde aber das bestehende Zwischenformat und die UI stärker umbauen als aktuell nötig.

### Default-Exit

**[Exit #1] Timed Exit nach 10 Bars**  
_Concept:_ Eine Position wird nach zehn abgeschlossenen Bars geschlossen, sofern sie nicht vorher durch eine explizite Regel beendet wird.  
_Novelty:_ Markt- und richtungsneutral, nur ein Parameter, leicht prüfbar und aus der vorhandenen Quelle abgeleitet.

**[Exit #2] ATR-Trailing-Exit**  
_Concept:_ Long schließt unter dem höchsten Kurs seit Entry minus `3 × ATR(14)`; Short spiegelbildlich über dem tiefsten Kurs plus `3 × ATR(14)`.  
_Novelty:_ Passt sich Volatilität und langen Trends an, bewertet aber nicht nur den Entry, sondern stark auch die Trendstruktur.

**[Exit #3] Gegensignal als Exit**  
_Concept:_ Das nächste entgegengesetzte Entry-Signal schließt die Position, ohne zwingend eine Gegenposition zu eröffnen.  
_Novelty:_ Nutzt vorhandene Signale, funktioniert aber nicht bei Strategien, die nur eine Richtung definieren.

**[Exit #4] Kategorieabhängiger Default**  
_Concept:_ Trendfolge erhält ATR-Trailing, Mean Reversion einen RSI-/MA-Exit und saisonale Strategien einen Timed Exit.  
_Novelty:_ Fachlich plausibler, führt aber schon vor dem ersten vergleichbaren Baseline-Test mehrere Annahmen und Parameter ein.

**[Exit #5] Nutzer muss immer wählen**  
_Concept:_ Fehlende Exit-Regeln blockieren weiterhin die Freigabe, bis ein Exit manuell gewählt wurde.  
_Novelty:_ Maximale Transparenz, aber keine echte Standardisierung und unnötige Bedienarbeit bei vielen Entry-Bausteinen.

### Provenienz und Versionierung

**[Provenienz #1] Herkunft am Exit speichern**  
_Concept:_ `exit_rule_origin` unterscheidet `source`, `system_default` und `user`.  
_Novelty:_ Ein Blick zeigt, ob der Exit aus dem Buch, aus dem System oder aus einer Nutzerentscheidung stammt.

**[Provenienz #2] Default erst beim Backtest dynamisch einsetzen**  
_Concept:_ Die Strategieversion bleibt ohne Exit; der jeweils aktuelle globale Default wird beim Run ergänzt.  
_Novelty:_ Spart Snapshot-Felder, zerstört aber Reproduzierbarkeit, sobald sich der Default ändert.

**[Provenienz #3] Aufgelösten Exit einfrieren**  
_Concept:_ Beim Freeze werden Exit-Regel, Herkunft und Parameter vollständig in den bestehenden Versions-Snapshot geschrieben.  
_Novelty:_ Globaler Default kann später geändert werden, ohne alte Ergebnisse umzudeuten.

## Konvergenz

### Vergleich der Exit-Kandidaten

Bewertung von 1 (schwach) bis 5 (stark):

| Exit | Vergleichbarkeit | Richtungs-/Marktneutralität | Einfachheit | Trend-Eignung | Wenige Freiheitsgrade | Summe |
|---|---:|---:|---:|---:|---:|---:|
| Timed Exit, 10 Bars | 5 | 5 | 5 | 2 | 5 | **22** |
| ATR-Trailing, 3×ATR(14) | 3 | 5 | 3 | 5 | 3 | **19** |
| Gegensignal | 3 | 2 | 4 | 3 | 5 | **17** |
| Kategorieabhängig | 2 | 3 | 1 | 5 | 1 | **12** |

### Entscheidung

**Systemdefault für Entry-only-Strategien: Timed Exit nach 10 Bars.**

Begründung:

- Der erste standardisierte Test soll primär die Qualität des Entry-Signals vergleichen. Ein identischer Haltezeitraum isoliert diese Wirkung besser als ein eigener, zustandsbehafteter Trailing-Mechanismus.
- Zehn Bars sind in der vorhandenen Quelle der konkrete Ausgangswert für Daveys bevorzugten Baseline-Exit.
- Die Regel ist symmetrisch für Long und Short, deterministisch und mit dem aktuellen Bar-Close-/Next-Open-Vertrag einfach umsetzbar.
- Beim 4-Stunden-Default entspricht sie 40 Stunden Haltedauer. Der Wert bleibt sichtbar und versioniert; er ist keine Behauptung, dass zehn Bars für alle Strategien optimal sind.

**ATR-Trailing wird nicht Systemdefault, sondern erster späterer Vergleichs-Exit.** Für Trendfolge ist er wahrscheinlich fachlich passender. Als globaler Default würde er aber Entry- und Exit-Qualität stärker vermischen und zwei zusätzliche Parameter (`ATR length`, `ATR multiple`) einführen.

## Empfohlenes fachliches Modell

### 1. Zwei unabhängige Achsen

| Achse | Werte | Bedeutung |
|---|---|---|
| `direction` | `kombiniert`, `long-only`, `short-only` | Welche Richtungen der Run eröffnen darf |
| `position_mode` | `signal_reversal`, `entry_exit` | Ob das Signal direkt die Gegenposition setzt oder ein separater Flat-Exit nötig ist |

### 2. Exit-Auflösung

Die Reihenfolge ist fest und benötigt keine komplexe Regel-Engine:

1. `signal_reversal`: Gegensignal schließt und eröffnet im kombinierten Run direkt die Gegenposition.
2. `entry_exit` mit expliziter Quellenregel: Quellen-Exit verwenden.
3. `entry_exit` ohne Quellenregel: `Timed Exit nach 10 Bars` einsetzen und als `system_default` markieren.

Im `long-only`- bzw. `short-only`-Run eröffnet ein Gegensignal keine verbotene Gegenposition. Es schließt nur die bestehende Position; der Run bleibt bis zum nächsten erlaubten Entry flat. „Immer investiert“ gilt daher nur für einen kombinierten Stop-and-Reverse-Run.

### 3. Minimale Datenänderung

Zum bestehenden Draft-/Snapshot-Modell genügen:

- `position_mode`: `signal_reversal | entry_exit`
- `exit_rule_origin`: `source | system_default | user`
- `exit_rule` bleibt die vollständig aufgelöste, lesbare Regel.
- Der Wert `10` und die Einheit `bars` werden über die bereits vorhandenen Strategieparameter gespeichert.

Eine eigene `exit_strategies`-Tabelle ist für den ersten Default nicht nötig. Sie wird erst sinnvoll, wenn mehrere Exit-Bausteine tatsächlich auswählbar oder systematisch als Matrix getestet werden sollen.

## Einbau in den vorhandenen Ablauf

### Extraktion

- Prompt um `position_mode` ergänzen.
- Bei ausdrücklich beschriebenem Stop-and-Reverse/SMA-Wechsel `signal_reversal` setzen.
- Bei Entry-only oder explizitem Flat-Exit `entry_exit` setzen.
- Fehlender Quellen-Exit sperrt `entry_exit` nicht mehr automatisch; stattdessen wird der Default vorgeschlagen.
- Die KI darf den Default nicht als Quelleninhalt zitieren.

### Verifizierung

- UI zeigt `Positionsmodus` separat von `Richtung`.
- Exit-Anzeige erhält ein sichtbares Badge: `Aus Quelle`, `Systemdefault` oder `Vom Nutzer`.
- Bei automatisch erkanntem `position_mode` muss der Nutzer ihn vor Freeze bestätigen, weil eine Fehlklassifikation das gesamte Exposure verändert.
- Der Timed-Exit-Wert `10 Bars` ist editierbar; eine Änderung setzt die Herkunft auf `user`.

### Freeze und Versionierung

- Beim Freeze wird der Exit einmal aufgelöst.
- Snapshot enthält `position_mode`, konkrete `exit_rule`, `exit_rule_origin` und Exit-Parameter.
- Eine spätere Änderung des globalen Defaults betrifft nur neue Entwürfe bzw. neue Versionen.

### Pine-/Backtest-Ausführung

- `signal_reversal`, kombiniert: Opposite Signal schließt die aktuelle Position und eröffnet die Gegenposition.
- `entry_exit`: Exit auf dem Schlusskurs der zehnten Bar nach Entry erkennen; Ausführung wie alle anderen Signale am nächsten verfügbaren Bar-Open.
- Kein intrabar Stop-Order-Sonderweg für den Baseline-Exit.
- Pro Strategieversion entsteht weiterhin genau ein Run je Instrument/Richtungsmodus; keine automatische Entry×Exit-Testmatrix.

## Akzeptanzkriterien für die spätere Umsetzung

1. Eine kombinierte SMA-Crossover-Strategie kann als `signal_reversal` ohne künstlichen 10-Bar-Exit freigegeben werden.
2. Eine Entry-only-Strategie ohne Quellen-Exit erhält sichtbar den Systemdefault `Exit nach 10 Bars`.
3. Ein expliziter Quellen-Exit hat immer Vorrang vor dem Systemdefault.
4. Richtung und Positionsmodus sind getrennt editier- und versionierbar.
5. Ein geänderter globaler Default verändert keine freigegebene Version und keinen bestehenden Run.
6. Long und Short verwenden dieselbe Bar-Zählung spiegelbildlich.
7. Im Long-only-Run darf ein Short-Signal eine Long-Position schließen, aber keine Short-Position eröffnen; spiegelbildlich für Short-only.
8. UI und Export zeigen eindeutig, woher der Exit stammt.
9. Der erste Exit erfolgt nach exakt zehn vollständig seit Entry vergangenen Bars und wird gemäß Backtest-Profil am nächsten Bar-Open ausgeführt.

## Risiken und Gegenmaßnahmen

- **Timed Exit passt fachlich nicht optimal zu jeder Strategie.** Gegenmaßnahme: als neutrale Baseline kennzeichnen, nicht als „optimalen“ Exit.
- **Fehlerhafte Positionsmodus-Erkennung verändert Exposure massiv.** Gegenmaßnahme: Nutzerbestätigung vor Freeze.
- **Off-by-one bei der Bar-Zählung.** Gegenmaßnahme: ein kleiner ausführbarer Test mit Entry-Bar, zehn Halte-Bars und erwartetem Fill-Bar.
- **Default wird mit Quellenregel verwechselt.** Gegenmaßnahme: `exit_rule_origin` und fehlender Quellenbeleg für Systemdefaults explizit unterstützen.
- **Spätere Variantenexplosion.** Gegenmaßnahme: im ersten Schritt genau einen Default; keine automatische Exit-Matrix.

## Top-Prioritäten und Aktionsplan

### Priorität 1: Fachvertrag aktualisieren

- **Nächster Schritt:** PRD sowie PROJ-2/3/6 um `position_mode`, Exit-Herkunft und Auflösungsreihenfolge ergänzen.
- **Risiko:** Begriffe „Richtung“, „Reversal“ und „Exit“ bleiben sonst widersprüchlich.
- **Erfolg:** Alle drei Beispielpfade (SMA-Reversal, Entry mit Quellen-Exit, Entry mit Default-Exit) sind in Akzeptanzkriterien beschrieben.

### Priorität 2: Extraktion und Freeze anpassen

- **Nächster Schritt:** Schema/Prompt/Normalisierung ändern; Default spätestens vor Freeze auflösen und snapshotten.
- **Risiko:** Bestehende Entwürfe benötigen einen sicheren Default für das neue Feld.
- **Erfolg:** Alte und neue Versionen bleiben lesbar; keine fehlende Exit-Regel blockiert berechtigte Entry-only-Strategien.

### Priorität 3: Ausführung mit einem Grenzfalltest absichern

- **Nächster Schritt:** Pine-Übersetzung für den 10-Bar-Exit und Richtungsmodus-Verhalten ergänzen.
- **Risiko:** Bar-Zählung und Reversal am selben Bar können kollidieren.
- **Erfolg:** Reproduzierbarer Test beweist Entry-Bar, Exit-Signal-Bar und tatsächlichen Fill-Bar.

## Empfohlene Reihenfolge

1. Requirements/PRD ändern.
2. Architektur für die betroffenen Features aktualisieren.
3. Datenmodell, Extraktion und Verifizierungs-UI implementieren.
4. Freeze-/Snapshot-Logik implementieren.
5. Pine-Übersetzung und den kleinsten End-to-End-Test ergänzen.
6. Erst nach echten Baseline-Ergebnissen entscheiden, ob ATR-Trailing als auswählbarer zweiter Exit nötig ist.

## Offene Entscheidungspunkte

- Soll der Default langfristig global konfigurierbar sein oder bewusst als Produktkonstante `10 Bars` starten? Empfehlung: zunächst Produktkonstante; Konfiguration erst bei einem zweiten realen Default-Bedarf.
- Soll ATR-Trailing später manuell auswählbar oder automatisch nur für Trendfolge vorgeschlagen werden? Empfehlung: manuell auswählbar; keine Kategorieautomatik ohne empirischen Nachweis.

## Ergänzung: Crypto-MTS-Forecast

**Entscheidung:** Der normale Strategie-Backtest bleibt unverändert der erste Qualitätsnachweis. Strategy Bank bewertet sofort die Crypto-MTS-Eignung, führt aber noch keine automatische kontinuierliche Forecast-Transformation aus.

### Vorhandener Crypto-MTS-Vertrag

Crypto MTS erwartet pro Bar einen Forecast:

- positiv = Long
- `0` = Flat
- negativ = Short
- mittlerer absoluter Zielwert = `10`
- Begrenzung = `−20 … +20`
- Positionsskalierung = `forecast / 10`

Die Skala ist damit **Signalstärke und Positionsgröße**, keine statistisch kalibrierte Confidence oder Eintrittswahrscheinlichkeit.

### Sofortige Kompatibilität ohne zweiten Backtest

Jede deterministische Strategie mit aufgelöster Zielposition kann direkt abgebildet werden:

```text
Long  → +10
Flat  →   0
Short → −10
```

Weil `forecast / 10` dann genau `+1 / 0 / −1` ergibt, ist dieser diskrete Crypto-MTS-Adapter mathematisch identisch zum normalen 100-%-Strategie-Backtest. Er benötigt keinen zusätzlichen trader.dev-Run und keinen weiteren Credit.

### Eignungsklassen

| Einstufung | Kriterium |
|---|---|
| `kontinuierlich geeignet` | Es existiert ein natürlicher, vorzeichenbehafteter und kausal berechenbarer Stärkewert, z. B. `(fast_sma − slow_sma) / volatility`. |
| `diskret kompatibel` | Long/Flat/Short ist eindeutig, aber eine kontinuierliche Stärke wäre zusätzliche erfundene Logik. |
| `unklar` | Regel ist diskretionär, nicht kausal oder noch nicht deterministisch ausführbar. |

Die Einstufung wird angezeigt, aber nicht als Performance-Score behandelt. `diskret kompatibel` ist kein Qualitätsnachteil; viele Event-, Kalender- und Candlestick-Strategien besitzen legitimerweise keine natürliche kontinuierliche Stärke.

### Spätere kontinuierliche Transformation

Für geeignete Strategien wird später eine eigene, nutzerbestätigte Forecast-Regel versioniert. Beispiel SMA-Crossover:

```text
raw_score = (fast_sma − slow_sma) / volatility
```

Die Skalierung muss exakt dem kausalen Crypto-MTS-Vertrag folgen:

- Skalierungsbasis nur aus den 35 vorherigen abgeschlossenen Kerzen
- aktuelle Kerze ausgeschlossen
- erste 35 Kerzen neutral
- Nullwerte nicht in den mittleren Absolutwert einrechnen
- Zielwert `10`, anschließend Clipping auf `±20`
- Forecast für die Rendite um eine Bar verzögert verwenden
- kein Full-Sample-Min/Max und kein rückblickend berechneter Gesamtskalar

Der kontinuierliche Forecast ist eine eigene Strategievariante, weil seine Magnitude die Positionsgröße und damit die Performance verändert. Er wird später gegen die diskrete `±10/0`-Baseline verglichen und nicht mit ihr vermischt.

### Minimale Produktauswirkung jetzt

1. Bestehenden Entry-/Exit-Backtest unverändert ausführen.
2. Aus der verifizierten Regel eine der drei Eignungsklassen ableiten und vor Freeze bestätigen lassen.
3. Für `diskret kompatibel` den Adapter `position × 10` als späteren Crypto-MTS-Exportvertrag festhalten.
4. Für `kontinuierlich geeignet` zunächst nur die Eignung anzeigen; noch keine Stärkeregel automatisch erfinden oder testen.
5. Erst in einer späteren Feature-Version eine optionale `raw_score_rule` samt Herkunft und eigener Version ergänzen.

### Akzeptanzkriterien der Sofortstufe

1. Jede testbare Strategie erhält genau eine sichtbare Crypto-MTS-Einstufung.
2. SMA-/Indikator-Distanzen dürfen als `kontinuierlich geeignet` vorgeschlagen werden, benötigen aber Nutzerbestätigung.
3. Strategien ohne natürliche Stärkefunktion werden als `diskret kompatibel`, nicht als ungeeignet markiert.
4. Der diskrete Adapter erzeugt `+10 / 0 / −10` aus der aufgelösten Zielposition.
5. Für die diskrete Einstufung wird kein zusätzlicher Backtest-Run erzeugt.
6. UI und Export nennen den Wert „Signalstärke“, nicht „Confidence“.
7. Keine KI darf ohne sichtbare Bestätigung eine kontinuierliche Stärkeregel ergänzen.

### Aktualisierte Reihenfolge

1. Entry-/Exit- und Positionsmodus-Vertrag umsetzen.
2. Crypto-MTS-Eignung als kleine zusätzliche Verifizierungsangabe ergänzen.
3. Normale Strategie-Baselines testen.
4. Ergebnisse und reale Importanforderungen aus Crypto MTS beobachten.
5. Erst danach kontinuierliche Forecast-Regeln und deren separaten Backtest bauen.
