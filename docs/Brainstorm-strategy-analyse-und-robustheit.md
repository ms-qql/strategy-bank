# Brainstorm: Strategy-Analyse, Erfolgsfaktoren und Robustheit

- **Datum:** 2026-07-30
- **Status:** Verdichtet
- **Projekt:** Strategy Bank

## Session-Setup

### Thema

Die Strategy Bank soll bei rund 300 Backtest-Ergebnissen drei Entscheidungen
unterstützen:

1. Welche Strategien verdienen eine vertiefte Prüfung?
2. Welche Merkmale haben erfolgreiche Strategien gemeinsam?
3. Welche Strategien sind gegenüber Parameter-, Zeitraum-, Timeframe- und
   Assetwechseln robust?

Als vierte, unabhängige Fragestellung soll sichtbar werden, wie gut eine
Strategie zum Crypto-MTS-Forecast-Modell von `−20` bis `+20` passt.

### Ziel

Zuerst wurde ein breiter Ideenraum erzeugt. Das Ergebnis ist anschließend zu
einem umsetzbaren Feature-Konzept verdichtet worden.

### Ansatz

Empfohlene Techniken:

- First Principles für die zu treffenden Entscheidungen
- Analogical Thinking mit Talent-Scouting und Kohortenstudien
- Morphologische Analyse für gemeinsame Strategiemerkmale
- Landschaftsanalogie für Parameterrobustheit
- Failure Analysis gegen falsche Robustheit

### Kontext und Leitplanken

- Heute liegen etwa 70 Backtests als Markdown-Dokumente vor; ungefähr 200
  weitere Strategien werden erwartet.
- Die verbindliche Ergebnisquelle ist der HAL-Ordner
  `/home/dev/tools/Hal/04 Resources/Strategy_Bank/02_Backtests`.
- Backtests werden außerhalb der App in einer separaten Agent-Session
  durchgeführt. Die Strategy Bank importiert und analysiert nur deren
  Ergebnisdateien.
- Die interne Backtest-Queue und trader.dev-Ausführung gehören nicht zum
  Hauptpfad dieses Features.
- Die vorhandene App besitzt bereits einen globalen Ergebnisvergleich nach
  PROJ-7.
- PROJ-10 klassifiziert Crypto-MTS-Eignung bereits als `continuous`,
  `discrete` oder `unclear`.
- Erst vorhandene Ergebnisse übersichtlich machen, danach externe Zusatzläufe
  nur für ausgewählte Strategien erzeugen und erneut importieren.
- Gute Strategien dürfen im ersten Screening lieber zu häufig als zu selten
  erscheinen.
- Einfachheit ist ein positives Merkmal: wenige Indikatoren, Filter,
  Bedingungen und freie Parameter.
- Calmar Ratio ist das Leitsignal, weil sie Rendite und maximalen Drawdown
  verbindet.
- Kein undurchsichtiger Composite Score.

## Initiales Framing

### Entscheidungen nach fünf Minuten

Nach dem Öffnen der App soll der Nutzer beantworten können:

- Was ist meine Shortlist für die weitere Arbeit?
- Welche Strategiekategorie ist derzeit am vielversprechendsten?
- Welche Richtungen, Regime, Indikatoren und Konstruktionsmerkmale treten bei
  erfolgreichen Strategien gehäuft auf?

### Kernkennzahlen

Jede Strategie zeigt konsistent:

- Gesamtrendite
- Sortino Ratio
- Calmar Ratio
- maximalen Drawdown
- Anzahl Trades

Calmar ist die Standardsortierung und das stärkste visuelle Signal. Sortino
bleibt die zweite zentrale Qualitätskennzahl. Eine geringe Trade-Anzahl führt
nicht zum Ausblenden, sondern zu einem sichtbaren Evidenzhinweis.

### Arbeitsdefinition „erfolgreich“

Eine Strategie gehört für die Kohortenanalyse zur Erfolgsgruppe, wenn sie alle
drei Bedingungen erfüllt:

- Calmar Ratio `≥ 0,8`
- Sortino Ratio `≥ 0,5`
- mindestens `6 Trades pro getestetem Jahr`

Diese Definition dient der Gruppenanalyse. Sie ist kein Löschfilter und keine
Voraussetzung für eine manuelle Shortlist.

## Divergenz: Ideensammlung

### Screening und Übersicht

**[Screening #1] Breiter Kandidatentrichter**  
_Concept:_ Nur eindeutig unbrauchbare Ergebnisse werden ausgeblendet; alle
anderen bleiben sortier- und filterbar.  
_Novelty:_ „Noch nicht ausreichend geprüft“ wird nicht mit „schlecht“
verwechselt.

**[Screening #2] Downside statt Bruttorendite**  
_Concept:_ Calmar und Sortino stehen vor Net Return.  
_Novelty:_ Eine spektakuläre, aber kaum handelbare Equity-Kurve gewinnt nicht
automatisch.

**[Screening #3] Evidenz getrennt von Potenzial**  
_Concept:_ Die Trade-Anzahl beeinflusst einen Evidenzhinweis, nicht die
Sichtbarkeit.  
_Novelty:_ Ein potenziell guter Kandidat mit kleiner Stichprobe bleibt erhalten.

**[Screening #4] Niedrige-Aktivität-Fleck**  
_Concept:_ Weniger als sechs Trades je Testjahr erzeugen einen auffälligen
Marker mit erklärendem Tooltip.  
_Novelty:_ Die Warnung beschreibt die Datenlage, ohne statistische Sicherheit
vorzutäuschen.

**[Übersicht #1] Fünf-Kennzahlen-Scouting-Card**  
_Concept:_ Eine kompakte Darstellung zeigt ausschließlich Gesamtrendite,
Sortino, Calmar, Max Drawdown und Trades.  
_Novelty:_ Karten-, Tabellen- und Detailansicht verwenden dieselbe
Informationshierarchie.

**[Übersicht #2] Calmar als Leitsignal**  
_Concept:_ Standardsortierung und stärkste Hervorhebung folgen der Calmar
Ratio.  
_Novelty:_ Rendite wird unmittelbar mit dem dafür ertragenen Drawdown
verbunden.

**[Übersicht #3] Manuelle Shortlist statt Gewinnerautomat**  
_Concept:_ Der Nutzer markiert Strategien mit einem Stern für die weitere
Arbeit. Ein Filter zeigt zusätzlich automatisch die feste Erfolgsgruppe.  
_Novelty:_ Fachliche Auswahl und reproduzierbare Schwellen bleiben getrennt.

**[Übersicht #4] Erklärbare Badges**  
_Concept:_ Kleine Marker zeigen niedrige Aktivität, unvollständige Daten,
abweichendes Backtest-Profil, Ergebnisart und noch ungeprüfte Robustheit.  
_Novelty:_ Warnungen verändern keine Kennzahl und verstecken keine Zeile.

**[Übersicht #5] HAL als Ergebnis-Inbox**  
_Concept:_ Die App liest standardisierte Markdown-Ergebnisse aus dem
HAL-Backtest-Ordner ein und aktualisiert daraus die Ergebnisansicht
idempotent.  
_Novelty:_ Backtest-Erzeugung und Ergebnisanalyse bleiben bewusst getrennte,
einfach austauschbare Arbeitsabläufe.

**[Übersicht #6] Import-Provenienz**  
_Concept:_ Jede Ergebniszeile kennt Quelldatei, Datei-Hash und Importzeitpunkt.
Eine unveränderte Datei wird nicht erneut angelegt; eine geänderte Datei wird
als aktualisierte Importversion erkannt.  
_Novelty:_ Die App kann Daten aus einem Ordner zuverlässig wiederholt einlesen,
ohne doppelte Strategien zu erzeugen.

### Erfolgsfaktoren und Vergleich

**[Erfolgsanalyse #1] Feste Qualitätskohorte**  
_Concept:_ Strategien oberhalb der drei Mindestwerte werden mit allen anderen
vergleichbaren Strategien verglichen.  
_Novelty:_ Die Definition ändert sich nicht automatisch mit der Anzahl der
Strategien.

**[Erfolgsanalyse #2] Erfolgsquote pro Kategorie**  
_Concept:_ Für Trendfolge, Mean Reversion, Breakout, Momentum und weitere
vorhandene Kategorien wird `Erfolgreiche / Getestete` gezeigt.  
_Novelty:_ Die Kategorie mit den meisten Strategien gewinnt nicht allein durch
ihre Größe.

**[Erfolgsanalyse #3] Lift statt bloßer Häufigkeit**  
_Concept:_ Für jedes Merkmal wird gezeigt, wie viel häufiger es in der
Erfolgsgruppe vorkommt als im Gesamtbestand.  
_Novelty:_ „Viele Gewinner nutzen RSI“ ist nur relevant, wenn RSI nicht ohnehin
fast überall verwendet wird.

**[Erfolgsanalyse #4] Stichprobengröße immer daneben**  
_Concept:_ Jede Quote zeigt Zähler und Nenner, beispielsweise `8/17
erfolgreich`.  
_Novelty:_ Kleine Gruppen können keine beeindruckenden Prozentwerte ohne
Kontext erzeugen.

**[Erfolgsanalyse #5] Long/Short-Matrix**  
_Concept:_ Kategorien und Indikatoren werden getrennt nach `long-only`,
`short-only` und `kombiniert` ausgewertet.  
_Novelty:_ Die App kann sichtbar machen, ob ein Ansatz nur von der strukturellen
Long-Tendenz des Marktes lebt.

**[Erfolgsanalyse #6] Merkmals-Chips statt Freitextsuche**  
_Concept:_ Richtung, Kategorie, Indikatoren, Entry-Typ, Exit-Typ, Filter und
MTS-Eignung werden als strukturierte Merkmale erfasst.  
_Novelty:_ Gemeinsame Eigenschaften werden berechenbar statt nur in Notizen
auffindbar.

**[Erfolgsanalyse #7] Einfachheitsvergleich**  
_Concept:_ Erfolgsquoten werden nach Anzahl Indikatoren, Filtern, Parametern und
Regelbedingungen aufgeschlüsselt.  
_Novelty:_ Die Hypothese „einfacher ist besser“ wird empirisch prüfbar.

**[Erfolgsanalyse #8] Regime-Beitrag**  
_Concept:_ P&L und Trades werden nach klar definierten Marktregimen zerlegt.  
_Novelty:_ Eine Strategie gilt nicht pauschal als gut, wenn ihr Gewinn fast nur
aus einem Bullen- oder Hochvolatilitätsregime stammt.

**[Erfolgsanalyse #9] Asset-Regime einmal berechnen**  
_Concept:_ Eine versionierte Regime-Zeitreihe wird grundsätzlich je
Asset, Timeframe und Regimemodell berechnet und anschließend von allen
Strategieanalysen wiederverwendet.  
_Novelty:_ Dasselbe Marktregime muss nicht für jede Strategie erneut
berechnet werden.

**[Erfolgsanalyse #10] Regimemodell versionieren**  
_Concept:_ Der spätere Pine-Code erhält eine Modellversion. Änderungen erzeugen
eine neue Regime-Zeitreihe, statt historische Zuordnungen still umzuschreiben.  
_Novelty:_ Ergebnisvergleiche bleiben reproduzierbar, obwohl die
Regimedefinition weiterentwickelt wird.

**[Erfolgsanalyse #11] Keine Kausalitätsbehauptung**  
_Concept:_ Die UI nennt Ergebnisse „Zusammenhänge“ oder „häufige Merkmale“, nie
„Ursachen“.  
_Novelty:_ Explorative Muster werden nicht als statistisch bewiesene
Handelsregeln verkauft.

### Einfachheit und Crypto MTS

**[Merkmale #1] Einfachheitsprofil**  
_Concept:_ Anzahl Indikatoren, Filter, Bedingungen und freie Parameter werden
separat gezeigt.  
_Novelty:_ Komplexität wird sichtbar, ohne einen fragwürdigen Einzelscore zu
erfinden.

**[MTS #1] Unabhängige Forecast-Achse**  
_Concept:_ MTS-Eignung erscheint neben der Performance, beeinflusst aber nicht
das Calmar-Ranking.  
_Novelty:_ Eine gute diskrete Strategie wird nicht abgewertet, nur weil sie
keinen natürlichen kontinuierlichen Rohwert besitzt.

**[MTS #2] Diskrete Baseline**  
_Concept:_ Jede deterministische Zielposition kann ohne Zusatzlauf auf Long
`+10`, Flat `0`, Short `−10` abgebildet werden.  
_Novelty:_ Die vorhandene Strategie bleibt mathematisch unverändert und
verbraucht keinen weiteren Backtest-Credit.

**[MTS #3] Natürlicher kontinuierlicher Rohwert**  
_Concept:_ Kontinuierliche Eignung verlangt einen kausalen, vorzeichenbehafteten
Stärkewert, etwa volatilitätsnormalisierten Momentum- oder Trendabstand.  
_Novelty:_ Die App erfindet keine falsche Präzision aus einem rein binären
Ereignis.

**[MTS #4] Forecast-Variante separat testen**  
_Concept:_ Eine echte `−20…+20`-Transformation wird als eigene versionierte
Strategievariante gegen die diskrete Baseline getestet.  
_Novelty:_ Die dynamische Positionsgröße wird nicht mit der ursprünglichen
100-%-Positionsstrategie vermischt.

### Robustheit und Overfitting

**[Robustheit #1] Plateau statt Optimum**  
_Concept:_ Gesucht werden stabile Parameternachbarschaften, nicht der beste
Einzelwert.  
_Novelty:_ Die Plateau-Mitte ist wichtiger als die lokale Calmar-Spitze.

**[Robustheit #2] Generalisierungsleiter**  
_Concept:_ Zusatzprüfungen laufen in der Reihenfolge Parameter, Zeitabschnitte,
Timeframes, Assets.  
_Novelty:_ In der externen Backtest-Session werden teure Tests nur für
Kandidaten der vorherigen Stufe ausgeführt; die App importiert anschließend
deren Dateien.

**[Robustheit #3] Qualität und Stabilität trennen**  
_Concept:_ Ein flaches Plateau gilt nur dann als gut, wenn seine typischen
Ergebnisse weiterhin die Qualitätsuntergrenzen erfüllen.  
_Novelty:_ „Stabil schlecht“ wird nicht als robust ausgezeichnet.

**[Robustheit #4] Parameter-Heatmap**  
_Concept:_ Für zwei gewählte Parameter zeigt eine Heatmap Calmar; der
Ausgangspunkt ist markiert. Für einen Parameter reicht eine Linie.  
_Novelty:_ Schmale Spitzen und breite Plateaus sind ohne Statistikjargon
erkennbar.

**[Robustheit #5] Nachbarschaftszusammenfassung**  
_Concept:_ Zusätzlich zur Grafik werden Median, schlechster Wert, Spannweite
und Anteil der Varianten oberhalb der Qualitätsgrenzen gezeigt.  
_Novelty:_ Eine kompakte Zusammenfassung bleibt auch bei drei oder mehr
Parametern nutzbar.

**[Robustheit #6] Regime-Dominanz-Warnung**  
_Concept:_ Eine Strategie wird markiert, wenn ein einzelner Zeitabschnitt den
Großteil des Ergebnisses erzeugt.  
_Novelty:_ Ein guter Gesamtwert kann instabile Teilperioden nicht verbergen.

**[Robustheit #7] Kosten-Stresstest**  
_Concept:_ Gebühren und Slippage werden moderat verschärft.  
_Novelty:_ Praktische Fragilität wird unabhängig von Parameterstabilität
sichtbar.

**[Robustheit #8] Auswahlbias-Warnung**  
_Concept:_ Die Zahl der erzeugten und betrachteten Varianten wird gespeichert
und angezeigt.  
_Novelty:_ Ein Gewinner aus sehr vielen Versuchen erhält den notwendigen
Suchkontext.

**[Robustheit #9] Robustheitsstatus statt Scheingenauigkeit**  
_Concept:_ Die Übersicht zeigt `nicht geprüft`, `fragil`, `gemischt` oder
`robust`; die Detailansicht erklärt die Einzelbefunde.  
_Novelty:_ Ein verständlicher Status ersetzt keinen transparenten
Kennzahlenblick.

## Konvergenz

### Theme 1: Ergebnis-Screener

Der Einstieg ist eine neue Importstrecke vor der vorhandenen
PROJ-7-Ergebnisansicht:

```text
HAL 02_Backtests/*.md
        ↓
Markdown validieren und normalisieren
        ↓
idempotent über Dateipfad + Inhaltshash importieren
        ↓
strukturierte Ergebnisdaten
        ↓
Ergebnis-Screener
```

Die bestehende Ergebnisansicht wird weiterverwendet, aber nicht mehr
ausschließlich aus intern ausgeführten Runs gespeist. Importierte HAL-Ergebnisse
sind ein gleichwertiger, klar gekennzeichneter Ergebnistyp.

Minimaler Ausbau:

- HAL-Ergebnisdateien einlesen und Parserfehler pro Datei anzeigen.
- Importierte Ergebnisse über Quelldatei und Hash nachvollziehbar machen.
- Sortino Ratio als zusätzliche Ergebniskennzahl aufnehmen.
- Standardmäßig nach Calmar absteigend sortieren.
- Aktivitätsschwelle in `Trades pro Jahr` ausdrücken; Startwert `6`.
- Niedrige Aktivität als auffälligen Fleck/Badge zeigen.
- Schnelle Filter für:
  - Erfolgsgruppe
  - manuelle Shortlist
  - Kategorie
  - Richtung
  - Instrument und Timeframe
  - MTS-Eignung
  - Robustheitsstatus
- Calmar, Sortino, Return, Max Drawdown und Trades als dominante Spalten
  beibehalten.

Die bestehende Trennung nach Profil beziehungsweise einheitlichen Testfaktoren
bleibt zwingend. Nur Dateien mit vergleichbarem Asset, Timeframe, Zeitraum,
Gebühren- und Sizing-Modell dürfen gemeinsam ausgewertet werden.

### Theme 2: Erfolgsfaktoren

Eine zweite Ansicht innerhalb des Ergebnisbereichs vergleicht die feste
Erfolgsgruppe mit der Vergleichsgruppe.

Sie beantwortet:

- Welche Kategorie besitzt die höchste Erfolgsquote?
- Funktionieren Strategien überwiegend Long, Short oder kombiniert?
- Welche Indikatoren und Regeltypen weisen positiven oder negativen Lift auf?
- Sind einfache Strategien häufiger erfolgreich als komplexe?
- Wie groß ist die jeweilige Stichprobe?

Empfohlene Darstellung:

| Merkmal | Erfolgreich | Gesamt | Erfolgsquote | Lift | Median Calmar |
|---|---:|---:|---:|---:|---:|
| Trendfolge | 8 | 17 | 47 % | 1,4× | 0,96 |
| long-only | 15 | 31 | 48 % | 1,6× | 1,02 |
| RSI | 4 | 22 | 18 % | 0,6× | 0,61 |

Die Tabelle ist aussagekräftiger und kleiner als ein eigenes Chart pro Merkmal.
Ein Balken in den Quote- und Lift-Zellen genügt als visuelle Hilfe.

### Theme 3: Regime-Analyse

Die Regime-Betrachtung ist kein spätes Zusatzdiagramm, sondern der erste
Vertiefungsschritt nach dem Screening.

Sobald der Pine-Code für die Regimeberechnung vorliegt, werden zwei technische
Varianten geprüft:

1. **Bevorzugt: Regime-Zeitreihe einmal je Asset/Timeframe/Modellversion
   berechnen und speichern.** Alle Strategien referenzieren dieselben
   zeitgestempelten Regime.
2. Regime bei jeder Strategieanalyse erneut berechnen. Diese Variante ist nur
   sinnvoll, wenn das Regime von Strategieparametern abhängt oder die
   Zwischenergebnisse nicht exportierbar sind.

Die erste Variante ist der Default, weil Marktregime grundsätzlich eine
Eigenschaft des Marktes und nicht der einzelnen Strategie sind. Die endgültige
Entscheidung fällt erst nach Sichtung des Pine-Codes und seines Ausgabeformats.

Die Ansicht zeigt je Strategie und Regime:

- Trades
- Net Return beziehungsweise P&L-Beitrag
- Calmar und Sortino, sofern pro Regime belastbar berechenbar
- maximalen Drawdown
- Anteil am Gesamtergebnis
- Warnung bei zu kleiner Stichprobe

Die übergreifende Faktorenansicht kann danach beispielsweise beantworten:
„Trendfolge erreicht die Qualitätsgrenzen vor allem in Trend-/Hochvolatilitäts-
Regimen, Mean Reversion dagegen in Seitwärtsregimen.“

### Theme 4: Strategie-Detail und Robustheitslabor

Die Detailansicht einer ausgewählten Strategie erhält:

- Kernkennzahlen und Evidenzhinweis
- strukturierte Merkmale
- diskrete beziehungsweise kontinuierliche MTS-Eignung
- Robustheitsstatus je Prüfstufe
- Parameterlinie oder Zwei-Parameter-Heatmap
- Vergleich von Originalwert, Plateau-Median und schlechtester Nachbarvariante
- Ergebnisse nach Zeitabschnitt, Timeframe und Asset

Die App startet keine Zusatzläufe. Sie kann eine prüfbare Variantenliste für
die manuelle Shortlist exportieren; Parameter-, Timeframe- und Assettests
werden in einer separaten Session ausgeführt und als weitere HAL-Dateien
zurückimportiert.

### Theme 5: Crypto-MTS-Eignung

MTS bleibt eine separate Qualitätsachse:

1. `continuous`: natürlicher kontinuierlicher Stärkewert vorhanden
2. `discrete`: sichere Abbildung auf `+10 / 0 / −10`
3. `unclear`: verlässliche Ableitung fehlt

Für kontinuierliche Kandidaten folgt später ein eigener Workflow:

- sichtbare `raw_score_rule`
- Nutzerbestätigung
- kausale Skalierung mit ausschließlich vergangenen Bars
- Clipping auf `±20`
- eigene Strategieversion
- eigener Backtest gegen die diskrete Baseline

## Priorisierung

| Priorität | Baustein | Wirkung | Aufwand | Begründung |
|---|---|---:|---:|---|
| P0 | HAL-Ergebnisimport | sehr hoch | mittel | Ohne Import gibt es keine verlässliche Ergebnisquelle |
| P0 | Ergebnis-Screener erweitern | sehr hoch | klein | Nutzt vorhandene PROJ-7-Seite |
| P0 | Sortino + Trades/Jahr + Calmar-Default | sehr hoch | klein | Entspricht direkt dem Auswahlprozess |
| P1 | Regime-Datenvertrag und Regime-Ansicht | sehr hoch | mittel | Regime sind zentral für die Bewertung erfolgreicher Ansätze |
| P1 | Strukturierte Merkmale und Erfolgsfaktoren | hoch | mittel | Beantwortet die Kategorie- und Gemeinsamkeitsfragen |
| P1 | Manuelle Shortlist | hoch | klein | Steuert selektive Folgeprüfungen |
| P2 | Parameter-Nachbarschaft und Heatmap | sehr hoch | mittel bis hoch | Liefert den ersten echten Robustheitsnachweis |
| P2 | Zeitabschnitt-/Timeframe-/Asset-Leiter | hoch | hoch | Prüft Generalisierung stufenweise |
| P3 | Kontinuierliche MTS-Forecast-Varianten | hoch | hoch | Verändert Positionsgrößen und braucht eigene Tests |

## Empfohlene Umsetzungssequenz

### Phase 1: HAL-Import und Screening

1. Markdown-Vertrag der Dateien unter `02_Backtests` festhalten.
2. Dateiimport mit Pflichtfeldern, verständlichen Parserfehlern und Inhaltshash
   bauen.
3. Sortino aus den HAL-Dateien in den Ergebnisvertrag übernehmen.
4. Ergebnisansicht standardmäßig nach Calmar sortieren.
5. Aktivität als Trades pro Jahr berechnen und bei `< 6` markieren.
6. Erfolgsgruppenfilter mit den drei festen Mindestwerten ergänzen.
7. Manuelle Shortlist pro Strategieversion ermöglichen.
8. Bestehende MTS-Eignung in Filter und Zeile anzeigen.

**Erfolgskriterium:** Der Nutzer kann 300 Runs in höchstens fünf Minuten auf
eine nachvollziehbare Arbeitsliste reduzieren, ohne dass Kandidaten mit
wenigen Trades unsichtbar werden.

### Phase 2: Regime-Analyse

1. Den später gelieferten Pine-Regime-Code und seine Parameter prüfen.
2. Einen versionierten Regime-Datenvertrag definieren:
   `Asset + Timeframe + Timestamp + Regime + Modellversion`.
3. Bevorzugt die Regime-Zeitreihe einmal je Asset, Timeframe und Modellversion
   erzeugen und speichern.
4. Strategieergebnisse anhand ihrer Trades beziehungsweise Equity-Beiträge
   diesen Regimen zuordnen.
5. Regime-Kennzahlen und Regime-Dominanz in Übersicht und Detail anzeigen.

**Erfolgskriterium:** Für jede Strategie ist sichtbar, in welchen Regimen sie
Geld verdient, verliert oder mangels Trades nicht beurteilt werden kann.

### Phase 3: Gemeinsame Erfolgsfaktoren

1. Vorhandene Kategorie, Richtung und MTS-Eignung aus dem eingefrorenen
   Strategie-Snapshot nutzen.
2. Wenige zusätzliche strukturierte Merkmale extrahieren:
   - verwendete Indikatoren
   - Anzahl Indikatoren
   - Anzahl Filter
   - Anzahl Parameter
   - Entry-Archetyp
   - Exit-Archetyp
3. Merkmale vor Nutzung bestätigbar machen; keine stillen KI-Fakten.
4. Kohortentabelle mit Erfolgsquote, Lift, Stichprobengröße und Median Calmar
   bauen.

**Erfolgskriterium:** Für jede Aussage wie „Trendfolge ist besser“ zeigt die
App direkt Zähler, Nenner und relative Abweichung zur Vergleichsgruppe.

### Phase 4: Parameterrobustheit

1. Für manuell ausgewählte Strategien eine kleine Variantenliste exportieren.
2. Die Varianten außerhalb der App backtesten und als HAL-Ergebnisse ablegen.
3. Importierte Varianten der Basisstrategie zuordnen.
4. Bei zwei Parametern eine kleine vollständige Matrix vergleichen.
5. Plateau-Median, schlechteste Variante, Spannweite und Erfolgsanteil
   berechnen.
6. Ausgangspunkt in Linie oder Heatmap markieren.
7. Status `fragil`, `gemischt` oder `robust` aus transparenten Regeln ableiten.

**Erfolgskriterium:** Eine schmale Spitze ist auf einen Blick von einem breiten,
qualitativ guten Plateau unterscheidbar.

### Phase 5: Generalisierung und MTS

1. Prüfmatrizen für Zeitabschnitte, Timeframes, Assets und Kosten exportieren.
2. Externe Ergebnisse nach jeder Stufe aus HAL importieren und bewerten.
3. Nur stabile Kandidaten in die nächste externe Prüfstufe übernehmen.
4. Kontinuierliche MTS-Forecast-Regel nur für bestätigte `continuous`-Kandidaten
   als neue Version definieren, extern testen und wieder importieren.

**Erfolgskriterium:** Die App trennt klar zwischen lokaler
Parameterstabilität, zeitlicher Stabilität, Portabilität und
Forecast-Eignung.

## Minimales fachliches Modell

HAL-Ergebnisdateien sind die Quelle der Wahrheit für Backtestresultate;
vorhandene Strategieversionen bleiben die Quelle der Wahrheit für die
Strategiedefinition. Zusätzlich werden nur fachlich neue Informationen
benötigt:

```text
Importiertes Backtest-Ergebnis
  - Quelldatei und Inhaltshash
  - Importzeitpunkt und Parserstatus
  - Strategiebezug oder noch unzugeordnet
  - Asset, Timeframe, Zeitraum und Testannahmen
  - Parameter
  - Kernkennzahlen und Long/Short-Breakdown
  - Report-Link und Pine-Code-Verweis

Strategiemerkmale je unveränderlicher Strategieversion
  - indicators[]
  - entry_archetype
  - exit_archetype
  - indicator_count
  - filter_count
  - parameter_count
  - bestätigt / unbestätigt

Manuelle Auswahl
  - strategy_version_id
  - shortlisted

Robustheitskampagne
  - Basis-Strategieversion und Basis-Run
  - Prüfstufe: parameter | period | timeframe | asset | costs
  - erzeugte Varianten und deren Runs
  - transparenter Status aus den Resultaten

Regime-Zeitreihe
  - Asset und Timeframe
  - Timestamp und Regime
  - Regimemodell-Version
```

Für Phase 1 ist keine neue Analyseplattform und kein Data Warehouse nötig. Die
bestehende `/results`-Antwort und Ergebnisansicht können um importierte
HAL-Ergebnisse erweitert werden.

## Risiken und Gegenmaßnahmen

| Risiko | Gegenmaßnahme |
|---|---|
| Produktivserver kann lokalen HAL-Vault nicht lesen | Transport explizit wählen: Ordner-/ZIP-Upload, erreichbare Spiegelung oder Deployment mit Vault-Zugriff |
| Eine HAL-Datei wird mehrfach eingelesen | Idempotenz über normalisierten Pfad und Inhaltshash |
| Markdown-Datei ist unvollständig oder abweichend | Pflichtfelder validieren, Datei einzeln als fehlerhaft anzeigen, übrigen Import fortsetzen |
| Kategorien oder Indikatoren werden falsch extrahiert | Vorschläge sichtbar bestätigen; Snapshot versionieren |
| Kleine Gruppen erzeugen spektakuläre Quoten | Zähler/Nenner immer anzeigen; keine Kausalitätsbegriffe |
| Unterschiedliche Profile werden vermischt | Bestehende PROJ-7-Profiltrennung unverändert erzwingen |
| Niedrige Trade-Anzahl wird als „schlecht“ missverstanden | Evidenzbadge statt Ausschluss |
| Flache, aber schlechte Landschaft gilt als robust | Qualitätsuntergrenzen zusätzlich zur Stabilität prüfen |
| Zu viele Parameterkombinationen erhöhen Backtestaufwand | Nur Shortlist, kleine Nachbarschaften, stufenweiser Trichter |
| Regime werden nachträglich passend definiert | Regimeregel vor dem Vergleich festlegen und versionieren |
| Kontinuierlicher Forecast nutzt Zukunftsdaten | Nur vergangene abgeschlossene Bars zur Skalierung |
| MTS-Eignung wird mit Strategiequalität verwechselt | Separate Achse, kein Einfluss auf Calmar-Ranking |

## Offene Entscheidungspunkte

Vor Implementierung der jeweiligen Phase sind noch zu entscheiden:

1. Wie gelangen HAL-Dateien zur produktiven App, die den lokalen Vault heute
   nicht direkt erreichen kann: manueller Ordner-/ZIP-Import, synchronisierte
   Spiegelung oder verändertes Deployment?
2. Wie werden HAL-Dateien zuverlässig einer bestehenden Strategieversion
   zugeordnet: stabiler Identifier im Markdown, Quellenlink oder zunächst
   normalisierter Name?
3. Welche Felder des aktuellen Markdown-Formats sind verpflichtend und welche
   dürfen fehlen?
4. Soll die manuelle Shortlist an Strategieversion oder einzelnen Run gebunden
   sein? Empfehlung: Strategieversion, mit sichtbaren zugehörigen Runs.
5. Welche zusätzlichen Merkmale lassen sich deterministisch aus dem bestehenden
   Snapshot ableiten und welche benötigen eine neue bestätigte KI-Extraktion?
6. Welche Ausgabe liefert der angekündigte Pine-Regime-Code: Regime je Bar,
   Trades je Regime oder bereits aggregierte Kennzahlen?
7. Ist das Regimemodell ausschließlich von Asset und Timeframe abhängig?
   Falls ja, wird es einmal berechnet und wiederverwendet.
8. Welche relativen oder absoluten Parameterabstände bilden die erste
   Nachbarschaft?
9. Welche transparenten Regeln trennen `fragil`, `gemischt` und `robust`?
10. Welche Timeframes und Assets gehören zur ersten Generalisierungsstufe?

## Empfohlener nächster Schritt

Als nächstes sollte aus **Phase 1 (HAL-Import und Screening)** eine
Requirements-Spezifikation entstehen. Die Regime-Spezifikation folgt, sobald
der Pine-Code und sein Ausgabeformat vorliegen. Erfolgsfaktoren, Robustheit und
MTS bleiben getrennte Folgefeatures; ihre Backtests laufen außerhalb der App
und werden wieder über HAL importiert.
