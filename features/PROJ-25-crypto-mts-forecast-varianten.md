# PROJ-25: Crypto-MTS-Forecast-Varianten

## Status: Planned
**Created:** 2026-07-30
**Last Updated:** 2026-07-30

## Dependencies
- Requires: PROJ-10 (Positions-, Exit- und Crypto-MTS-Kompatibilitätsmodell) — liefert Zielposition und bestätigte Eignung.
- Requires: PROJ-21 (HAL-Import und Ergebnis-Screening) — importiert Baseline- und Forecast-Ergebnisse.
- Requires: PROJ-24 (Robustheitslabor) — liefert bestätigte Kandidaten und vergleichbare externe Testvarianten.

## Ziel

Eine als `kontinuierlich geeignet` bestätigte Strategie kann eine eigene,
kausale Crypto-MTS-Forecast-Variante mit Werten von `−20` bis `+20` erhalten.
Die Variante wird versioniert und separat gegen die unveränderte diskrete
`+10 / 0 / −10`-Baseline bewertet.

## User Stories

- Als Crypto-MTS-Nutzer möchte ich eine natürliche kontinuierliche Rohwertregel sehen und bestätigen, damit keine falsche Signalpräzision erfunden wird.
- Als Trader möchte ich Skalierungsfenster, Verzögerung und Clipping nachvollziehen, damit Zukunftsdaten ausgeschlossen bleiben.
- Als Trader möchte ich die Forecast-Variante als eigene Strategieversion behandeln, damit ihre dynamische Positionsgröße nicht mit der Baseline vermischt wird.
- Als Trader möchte ich Forecast und diskrete Baseline unter identischem Backtest-Profil vergleichen, damit Performanceunterschiede der Transformation zugeordnet werden können.
- Als Trader möchte ich diskrete oder unklare Strategien unverändert behalten, damit kontinuierliche Scores nicht erzwungen werden.

## Forecast-Vertrag

Für Bar `t` gilt:

1. `raw_score_t` stammt aus einer bestätigten, vorzeichenbehafteten und kausal
   berechenbaren Regel.
2. Die Skalierungsbasis ist der Mittelwert der absoluten, von null
   verschiedenen Rohwerte der 35 vorherigen abgeschlossenen Bars
   `t-35 … t-1`.
3. Sind noch keine 35 Vorbars oder keine gültigen von null verschiedenen Werte
   vorhanden, ist der Forecast `0`.
4. Sonst gilt
   `forecast_t = clip(raw_score_t / scaling_base_t × 10, -20, +20)`.
5. Der Forecast wird um eine Bar verzögert für die folgende Rendite
   beziehungsweise Position verwendet.

## Acceptance Criteria

### Eignung und Bestätigung

- [ ] Nur eine Strategieversion mit bestätigter Eignung `kontinuierlich geeignet` kann eine Forecast-Variante erzeugen.
- [ ] `diskret kompatibel` und `unklar` bleiben ohne kontinuierliche Variante; die UI bietet keine erzwungene Umwandlung an.
- [ ] Jede Variante zeigt die vollständige `raw_score_rule`, ihre Herkunft und alle verwendeten Parameter.
- [ ] Eine KI-vorgeschlagene Rohwertregel ist bis zur ausdrücklichen Nutzerbestätigung gesperrt.
- [ ] Die UI bezeichnet den Wert als `Signalstärke`, niemals als `Confidence` oder Wahrscheinlichkeit.
- [ ] Die Bestätigung erzeugt eine neue unveränderliche Strategieversion; die Baseline wird nicht verändert.

### Kausalität und Skalierung

- [ ] Die Skalierungsbasis verwendet ausschließlich die 35 vorherigen abgeschlossenen Bars und schließt die aktuelle Bar aus.
- [ ] Die ersten 35 Bars liefern Forecast `0`.
- [ ] Nullwerte werden bei der Berechnung des mittleren Absolutwerts nicht einbezogen.
- [ ] Bei leerem Fenster, Skalierungsbasis `0`, `NaN` oder unendlichem Rohwert ist der Forecast `0`.
- [ ] Positive Rohwerte erzeugen nichtnegative, negative Rohwerte nichtpositive Forecasts.
- [ ] Jeder Forecast wird auf einschließlich `−20` und `+20` begrenzt.
- [ ] Für die Performancezuordnung wird der Forecast um genau eine Bar verzögert.
- [ ] Full-Sample-Min/Max, rückblickend berechnete Gesamtskalare und Daten nach Bar `t` sind unzulässig.
- [ ] Export und Versionsansicht dokumentieren Fensterlänge `35`, Zielmittelwert `10`, Clipping `±20` und Verzögerung `1 Bar`.

### Externer Test und Vergleich

- [ ] Die App exportiert die bestätigte Forecast-Variante für eine separate Backtest-Session, startet aber selbst keinen Zusatzlauf.
- [ ] Das Forecast-Ergebnis wird über PROJ-21 als eigener Run derselben Varianten-Version importiert.
- [ ] Ein Vergleich ist nur zulässig, wenn diskrete Baseline und Forecast-Variante Asset, Timeframe, Zeitraum, Gebühren, Slippage und Kapitalmodell teilen.
- [ ] Die Vergleichsansicht zeigt mindestens Net Return, Calmar, Sortino, Max Drawdown und Trade-Anzahl beziehungsweise Positionswechsel beider Varianten nebeneinander.
- [ ] Abweichende Profile werden sichtbar getrennt und nicht zu einer Verbesserung oder Verschlechterung verrechnet.
- [ ] Die Forecast-Eignung beeinflusst weder das allgemeine Calmar-Ranking noch die PROJ-21-Erfolgsgruppe.

## Edge Cases

- Der Rohwert ist über das gesamte 35-Bar-Fenster null: Forecast bleibt `0`.
- Ein extremer Rohwert überschreitet die Skalierung stark: Forecast wird exakt auf `+20` beziehungsweise `-20` begrenzt.
- Im Fenster fehlen einzelne Bars: Nur tatsächlich vorhandene abgeschlossene Bars zählen; bis 35 gültige Vorbars vorliegen, bleibt der Forecast `0`.
- Die bestätigte Rohwertregel wird geändert: Es entsteht eine neue Variante; bestehende Forecasts und Ergebnisse bleiben unverändert.
- Baseline oder Forecast-Ergebnis fehlt: Die vorhandene Seite bleibt sichtbar, der Paarvergleich zeigt `Vergleich unvollständig`.
- Eine diskrete Strategie besitzt nachträglich eine natürliche Rohwertregel: Erst eine neue bestätigte Strategieversion darf als kontinuierlich geeignet eingestuft werden.

## Non-Goals

- Keine automatische Erfindung kontinuierlicher Rohwertregeln.
- Keine nachträgliche Kalibrierung auf den vollständigen Backtestzeitraum.
- Keine Wahrscheinlichkeits- oder Confidence-Aussage.
- Keine Vermischung von Baseline und dynamischer Positionsgrößenvariante.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
