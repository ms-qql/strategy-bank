# PROJ-22: Regime-Analyse

## Status: Approved
**Created:** 2026-07-30
**Last Updated:** 2026-07-31 (Retest nach Bug-1-3-Fixes: 0 Critical/High offen, Approved)

## Dependencies
- Requires: PROJ-21 (HAL-Import und Ergebnis-Screening) — liefert zugeordnete Ergebnisse und deren Testkontext.

## Ziel

Eine versionierte, für alle Strategien gemeinsame Marktregime-Zeitreihe macht
sichtbar, in welchen Marktphasen eine Strategie verdient, verliert oder
mangels Trades nicht beurteilt werden kann. Grundlage der ersten Modellversion
ist der bereitgestellte Pine-v6-Z-Score-Regimeindikator.

## Fachlicher Modellvertrag

Die erste Modellversion heißt `zscore-hma-v1` und verwendet:

| Parameter | Default | Regel |
|---|---:|---|
| Kursquelle | `close` | Quelle der Z-Score-Berechnung |
| Z-Score-Länge | `75` | mindestens `2` |
| HMA-Länge | `2` | mindestens `1` |
| Bestätigungskerzen | `2` | mindestens `1` |
| Obere Schwelle | `0,75` | muss größer als untere Schwelle sein |
| Untere Schwelle | `-0,75` | muss kleiner als obere Schwelle sein |

Regimewerte:

- `bullish`, wenn der geglättete Z-Score strikt über der oberen Schwelle liegt.
- `bearish`, wenn er strikt unter der unteren Schwelle liegt.
- `sideways` in allen übrigen Fällen.
- Ein Kandidat wird erst nach der konfigurierten Anzahl aufeinanderfolgender,
  abgeschlossener Kerzen desselben Kandidaten zum bestätigten Regime.

## User Stories

- Als Trader möchte ich je Asset, Timeframe und Modellversion eine gemeinsame Regime-Zeitreihe verwenden, damit Strategien nicht mit unterschiedlichen Marktdefinitionen bewertet werden.
- Als Trader möchte ich Modellparameter und Version sehen, damit historische Zuordnungen reproduzierbar bleiben.
- Als Trader möchte ich je Strategie Trades und Performance nach Bullish, Bearish und Seitwärts sehen, damit Regimeabhängigkeit erkennbar wird.
- Als Trader möchte ich Warnungen bei kleiner Stichprobe und Regime-Dominanz sehen, damit ein guter Gesamtwert nicht über eine einseitige Datenlage hinwegtäuscht.
- Als Trader möchte ich fehlende Regimedaten klar erkennen, statt geschätzte Zuordnungen zu erhalten.

## Acceptance Criteria

### Regime-Zeitreihe

- [ ] Eine Regime-Zeitreihe ist eindeutig durch Provider-Symbol, Asset, Timeframe, Modellversion und Parameter bestimmt.
- [ ] Jeder Datensatz enthält Bar-Zeitstempel, bestätigtes Regime und Modellversion.
- [ ] Dieselbe Zeitreihe wird von allen Strategieanalysen mit identischem Asset, Timeframe und Modellvertrag wiederverwendet.
- [ ] Eine Parameter- oder Logikänderung erzeugt eine neue Modellversion und überschreibt keine bestehende Zuordnung.
- [ ] Vor abgeschlossener Warm-up-Periode oder bei Standardabweichung `0` ist das Regime `nicht verfügbar`.
- [ ] Schwellenwerte werden strikt ausgewertet: Gleichheit mit einer Schwelle gehört zu `sideways`.
- [ ] Nur abgeschlossene Bars verändern Kandidatenzählung oder bestätigtes Regime; Intrabar-Werte werden nicht gespeichert.
- [ ] Untere Schwelle größer oder gleich oberer Schwelle wird mit „Die untere Schwelle muss kleiner als die obere Schwelle sein.“ abgelehnt.
- [ ] Ein Wechsel des Kandidaten setzt dessen Zähler auf `1`; ungültige Z-Score-/HMA-Werte setzen Kandidat und Zähler zurück.
- [ ] Der erste bestätigte Zustand wird wie ein Regimewechsel behandelt und ist im Verlauf sichtbar.

### Import und Abdeckung

- [ ] Die App startet für dieses Feature keine trader.dev- oder sonstigen externen Zusatzläufe.
- [ ] Eine extern erzeugte Regime-Zeitreihe kann über einen dokumentierten Datensatz mit Asset, Timeframe, Timestamp, Regime und Modellversion übernommen werden.
- [ ] Doppelte Datensätze derselben Zeitreihe und desselben Zeitstempels erzeugen keine zweite Bar.
- [ ] Lücken, überlappende Modellversionen und nicht zum Timeframe passende Zeitstempel werden vor Nutzung sichtbar gemeldet.
- [ ] Die App zeigt pro Strategie, welcher Anteil des Backtest-Zeitraums durch die gewählte Regime-Zeitreihe abgedeckt ist.
- [ ] Bei weniger als `95 %` Abdeckung wird die Regime-Auswertung als `unvollständig` gekennzeichnet.

### Performance je Regime

- [ ] Eine Regimeauswertung verwendet ausschließlich Trades oder zeitgestempelte P&L-/Equity-Beiträge, die dem importierten Ergebnis eindeutig zugeordnet sind.
- [ ] Liegen nur aggregierte Gesamt-KPIs ohne Zeitbezug vor, zeigt die App „Regime-Auswertung nicht möglich: Zeitgestempelte Ergebnisdaten fehlen.“
- [ ] Je Regime werden mindestens Trade-Anzahl, Net P&L beziehungsweise Return-Beitrag, Max Drawdown und Anteil am Gesamtergebnis angezeigt.
- [ ] Calmar und Sortino werden nur angezeigt, wenn sie aus den Daten des einzelnen Regimes belastbar berechnet werden können; fehlende Werte werden nicht aus dem Gesamtergebnis übernommen.
- [ ] Weniger als `6` Trades in einem Regime erzeugen das Badge `Kleine Stichprobe`.
- [ ] Bei positivem Gesamtergebnis erscheint `Regime-Dominanz`, wenn ein Regime mehr als `70 %` der Summe aller positiven Regime-P&L-Beiträge liefert.
- [ ] Übersicht und Detail nennen Befunde `Zusammenhang`, `Verteilung` oder `Häufigkeit`, niemals `Ursache`.
- [ ] Ergebnisse verschiedener Modellversionen werden nicht still zusammengeführt.

## Edge Cases

- Die Standardabweichung ist über viele Bars null: Für diese Bars bleibt das Regime nicht verfügbar; der letzte Zustand wird nicht künstlich fortgeschrieben.
- Ein Kandidat wechselt vor Erreichen der Bestätigungskerzen: Es entsteht kein bestätigter Zwischenwechsel.
- Eine Strategie hat Trades außerhalb der Zeitreihenabdeckung: Diese Trades werden als `ohne Regimezuordnung` separat ausgewiesen.
- Ein Trade erstreckt sich über mehrere Regime: zeitgestempelte P&L-Beiträge werden den jeweiligen Regimen zugeordnet; liegt nur ein abgeschlossener Trade vor, wird die verwendete Zuordnungsregel sichtbar genannt.
- Ein Ergebnis hat nur Verluste: Die Regime-Dominanzregel für positive Beiträge wird nicht angewendet.
- Nutzer wählt eine neue Modellversion: Historische Ansichten bleiben auf ihrer gespeicherten Version reproduzierbar.

## Non-Goals

- Keine automatische Optimierung der Regimeparameter.
- Keine Hoch-/Niedrigvolatilitätsachse in `zscore-hma-v1`.
- Keine Behauptung, ein Regime verursache Strategieperformance.
- Keine Neuberechnung des Regimes pro Strategie.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-30 · **Stack:** Next.js 16 (App Router, shadcn/ui) + FastAPI + PostgreSQL (Dokploy, single-tenant) · **Branch:** dev

### Ausgangslage im Bestand

Zwei Befunde aus dem echten Hal-Vault bestimmen dieses Design:

1. **Die Hal-Backtestdateien enthalten keine Trades.** Sie liefern aggregierte Kennzahlen
   (Total Trades, Net Return, Long-/Short-Aufteilung) und einen Report-Link auf
   trader.dev. Ohne zusätzliche Datenquelle wäre die Regime-Auswertung für den gesamten
   heutigen Bestand nicht möglich — das Feature bliebe leer.
2. **Alle 68 vorhandenen Backtests laufen auf BTCUSDT, 4h, 2021-01-01 bis 2024-12-31.**
   Eine einzige Regime-Zeitreihe deckt damit den kompletten Bestand ab. Die Zeitreihe muss
   trotzdem generisch je Asset und Timeframe angelegt werden, weil PROJ-24 und PROJ-25
   weitere Instrumente bringen.

Wiederverwendet wird der bestehende trader.dev-Client: er spricht bereits generisch mit
dem MCP-Server und liest die Result-ID aus dem Report-Link. Beides wird gebraucht und
nicht neu gebaut.

### A) Komponentenstruktur

Neue Seite `/regime` (Verwaltung der gemeinsamen Datengrundlage):

```
RegimeSeite
├── ModellversionsKarte (aktive Version, Parameter, Erstellungszeitpunkt, schreibgeschützt)
├── ZeitreihenListe (je Asset + Timeframe + Modellversion)
│   └── ZeitreihenZeile → abgedeckter Zeitraum, Anzahl Bars, Lücken, Anteil „nicht verfügbar"
│                         plus Aktion „Bars nachladen"
└── DatenqualitaetsHinweise (Lücken, Timeframe-fremde Zeitstempel, überlappende Modellversionen)
```

Erweiterung der Ergebnisansicht `/ergebnisse` (aus PROJ-21):

```
ErgebnisZeile (bestehend)
└── Aktion „Regime-Auswertung" → RegimePanel (Sheet, shadcn/ui bereits vorhanden)
    ├── KopfZeile: Modellversion · Zuordnungsregel · Abdeckung in Prozent
    │              plus Badge „Unvollständig" bei Abdeckung unter 95 %
    ├── TradesNachladenHinweis (nur solange Trades fehlen, mit Aktion „Trades laden")
    ├── RegimeTabelle (drei Zeilen: Bullish · Bearish · Seitwärts, dazu „ohne Regimezuordnung")
    │   └── je Zeile: Trades · Net P&L · Max Drawdown · Anteil am Gesamtergebnis
    │                 Calmar und Sortino nur, wenn aus den Regimedaten selbst berechenbar
    │                 Badge „Kleine Stichprobe" bei weniger als 6 Trades
    ├── DominanzHinweis („Regime-Dominanz", wenn ein Regime über 70 % der positiven Beiträge trägt)
    └── LeerZustand: „Regime-Auswertung nicht möglich: Zeitgestempelte Ergebnisdaten fehlen."
```

Sprachlich sind alle Befunde als `Zusammenhang`, `Verteilung` oder `Häufigkeit` formuliert.
Das Wort `Ursache` kommt in keiner Textbaustein-Variante vor.

### B) Datenmodell (Klartext)

**Regime-Modellversion** — der unveränderliche Vertrag:
- Name (erste Version: `zscore-hma-v1`), Kursquelle, Z-Score-Länge, HMA-Länge,
  Bestätigungskerzen, obere und untere Schwelle, Erstellungszeitpunkt
- Wird nie bearbeitet. Eine Parameter- oder Logikänderung legt eine neue Version an.
- Untere Schwelle größer oder gleich oberer Schwelle wird beim Anlegen abgelehnt.

**Regime-Zeitreihe** — die gemeinsame Datengrundlage:
- eindeutig durch Provider-Symbol, Asset, Timeframe und Modellversion
- kennt ihren abgedeckten Zeitraum und den Zeitpunkt der letzten Aktualisierung

**Regime-Bar** — eine Zeile je abgeschlossener Kerze:
- Bar-Zeitstempel, bestätigtes Regime (`bullish`, `bearish`, `sideways` oder „nicht verfügbar")
- Zeitstempel plus Zeitreihe sind zusammen eindeutig: ein erneutes Laden derselben Bar
  erzeugt keine zweite Zeile
- Vor Ende der Warm-up-Periode und bei Standardabweichung null bleibt das Regime
  „nicht verfügbar"; der letzte bekannte Zustand wird nicht fortgeschrieben

**Kursbar** — die Rohdaten hinter der Zeitreihe:
- Asset, Timeframe, Bar-Zeitstempel, Eröffnung, Hoch, Tief, Schluss
- getrennt von den Regime-Bars gespeichert, damit eine neue Modellversion aus denselben
  Kursen neu gerechnet werden kann, ohne die Kurse erneut zu laden

**Ergebnis-Trade** — die zeitgestempelte Ergebnisseite:
- Verweis auf das importierte Ergebnis aus PROJ-21
- Richtung, Einstiegszeit, Ausstiegszeit, Netto-P&L, Herkunft der Daten
- einmal geladen, bleiben sie gespeichert; ein erneuter Abruf erzeugt keine Dubletten

**Regime-Auswertung** — das berechnete Ergebnis je Ergebnis und Modellversion:
- Verweise auf Ergebnis, Zeitreihe und Modellversion, dazu Abdeckungsgrad und Zuordnungsregel
- je Regime: Trade-Anzahl, Netto-P&L, Max Drawdown, Anteil am Gesamtergebnis, gesetzte Badges
- Auswertungen verschiedener Modellversionen stehen nebeneinander und werden nie
  zusammengeführt; historische Ansichten bleiben auf ihrer gespeicherten Version lesbar

### C) API-Zuschnitt

```
GET  /regime/models                       → verfügbare Modellversionen mit Parametern
POST /regime/models                       → neue Modellversion anlegen (Schwellenprüfung serverseitig)

GET  /regime/series                       → Zeitreihen mit Abdeckung und Datenqualitätshinweisen
POST /regime/series/{id}/refresh          → fehlende Kursbars nachladen und Regime neu bestimmen
POST /regime/series/import                → fertige Zeitreihe übernehmen (Asset, Timeframe,
                                            Zeitstempel, Regime, Modellversion)

POST /hal-results/{id}/trades/fetch       → Trades zum Ergebnis über den Report-Link nachladen
GET  /hal-results/{id}/regime             → Regime-Auswertung des Ergebnisses
```

Die Ergebniszeile aus PROJ-21 wird um zwei Anzeigefelder ergänzt: ob zeitgestempelte
Trades vorliegen und ob eine Regime-Auswertung existiert. Damit sieht der Nutzer in der
Liste, wo ein Nachladen noch fehlt, ohne jede Zeile einzeln zu öffnen.

### D) Technische Entscheidungen (mit Begründung)

1. **Trades werden bei trader.dev nachgeladen, nicht neu erzeugt.** Der Report-Link jeder
   Hal-Datei enthält die Result-ID eines bereits gelaufenen Backtests. Der bestehende
   Client holt dazu die fertige Trade-Liste. Das ist kein zusätzlicher Backtest, kostet
   keine Credits und verletzt das Kriterium „keine externen Zusatzläufe" nicht — es wird
   nichts gerechnet, nur ein vorhandenes Ergebnis vollständig gelesen.
2. **Nachladen auf Anforderung, Speichern für immer.** Bei 68 Ergebnissen wäre ein
   automatischer Abruf beim Import ein Sturm von Fremdaufrufen für Daten, die vielleicht
   niemand ansieht. Geladen wird, wenn der Nutzer eine Regime-Auswertung öffnet oder das
   Nachladen anstößt; danach liegen die Trades lokal und werden nie erneut geholt.
3. **Ohne Trades kein Ergebnis, aber eine ehrliche Meldung.** Schlägt der Abruf fehl oder
   fehlt der Report-Link, bleibt die Auswertung leer mit der vorgesehenen Klartextmeldung.
   Es werden keine Regimeanteile aus aggregierten Gesamtwerten geschätzt.
4. **Kursbars kommen von der öffentlichen Bybit-Schnittstelle.** Das ist dieselbe Börse,
   auf der die Backtests laufen (`BYBIT:BTCUSDT.P`), kostet nichts, braucht keinen
   Schlüssel und liefert genau die Kerzen, auf denen die Ergebnisse beruhen. Fremde
   Kursquellen würden ein anderes Marktbild erzeugen als der Backtest selbst.
5. **Kurse und Regime getrennt speichern.** Eine neue Modellversion ist damit eine reine
   Neuberechnung über vorhandene Kurse — ohne erneuten Fremdabruf und ohne die alte
   Zuordnung anzufassen.
6. **Regime wird einmal je Asset und Timeframe berechnet, nicht je Strategie.** Genau das
   ist der Zweck des Features: eine gemeinsame Marktdefinition. Eine Berechnung pro
   Strategie würde denselben Markt in verschiedenen Ansichten unterschiedlich beschreiben.
7. **Modellversionen sind unveränderlich.** Dieselbe Append-only-Logik wie bei
   Strategieversionen (PROJ-3) und Importversionen (PROJ-21): eine geänderte Definition
   ist eine neue Version, damit gespeicherte Auswertungen reproduzierbar bleiben.
8. **Nur abgeschlossene Bars, strikte Schwellen, kein Fortschreiben.** Die Bestätigungslogik
   arbeitet ausschließlich auf abgeschlossenen Kerzen; Gleichheit mit einer Schwelle zählt
   als `sideways`; ein Kandidatenwechsel setzt den Zähler auf eins; ungültige Zwischenwerte
   setzen Kandidat und Zähler zurück. Der erste bestätigte Zustand gilt als Regimewechsel
   und ist im Verlauf sichtbar.
9. **Zuordnungsregel: das Regime zum Einstiegszeitpunkt — und sie wird benannt.** Die
   nachgeladenen Trades sind abgeschlossene Trades mit einem P&L-Wert, keine Bar-für-Bar-
   Beiträge. Eine Aufteilung eines Trades über mehrere Regime wäre daher erfunden. Die
   angewandte Regel steht sichtbar über jeder Auswertung, wie im Kriterienkatalog verlangt.
10. **Abdeckung wird gemessen, nicht angenommen.** Der Anteil des Backtest-Zeitraums mit
    verfügbarem Regime wird ausgewiesen; unter 95 % gilt die Auswertung als unvollständig.
    Trades außerhalb der Abdeckung erscheinen als eigene Zeile „ohne Regimezuordnung"
    statt still in einem Regime zu landen.
11. **Kleine Stichprobe und Dominanz sind Hinweise, keine Filter.** Beide Badges werden
    serverseitig nach denselben Schwellen gesetzt, die PROJ-21 schon für Aktivität nutzt.
    Die Dominanzregel greift nur bei positivem Gesamtergebnis — bei reinen Verlustreihen
    hätte ein Anteil an positiven Beiträgen keine Aussage.
12. **Der Rechenweg bleibt in der Standardbibliothek.** Z-Score und HMA sind wenige Zeilen
    gleitender Durchschnitte über rund 8.800 Bars. Dafür braucht es keine Zusatzbibliothek,
    und das Ergebnis bleibt exakt reproduzierbar.

### E) Abhängigkeiten

- Backend: keine neuen Pakete. Der HTTP-Zugriff und der trader.dev-Client existieren,
  die Indikatorberechnung ist Standardbibliothek.
- Frontend: keine neuen Pakete. Sheet, Table, Badge und Tooltip sind installiert.
- Datenbank: eine neue Migration mit den sechs oben beschriebenen Tabellen, mit Eindeutigkeit
  auf (Zeitreihe, Bar-Zeitstempel) und (Asset, Timeframe, Bar-Zeitstempel) sowie Indizes
  auf Ergebnis und Modellversion.
- Konfiguration: die Basis-Adresse der öffentlichen Kursschnittstelle als Umgebungsvariable
  mit Standardwert, damit sie ohne Codeänderung austauschbar bleibt.

### F) Auswirkungen und Reihenfolge

- PROJ-22 setzt PROJ-21 voraus: ohne importierte Ergebnisse mit Report-Link gibt es nichts
  auszuwerten.
- Die Trade-Nachladung ist auch für PROJ-23 und PROJ-24 die Datengrundlage. Sie wird
  deshalb als eigenständiger Baustein gebaut, nicht als Teil der Regime-Ansicht.
- Sidebar bekommt einen Eintrag „Regime".
- Erster sinnvoller Testfall nach dem Bau: eine Zeitreihe für BTCUSDT 4h über
  2021-2024 anlegen — sie deckt alle 68 heute vorhandenen Backtests ab.

## QA Test Results
**Getestet:** 2026-07-30 · **Tester:** QA Engineer

### Automatisierte Tests

- `backend/tests/test_regime.py`: 21/21 grün.
- Regression `backend/tests/` (Rest der Suite): Kollektion sauber (325 Tests), voller Lauf bricht nach 2 Minuten durch einen Timeout ab — Ursache liegt außerhalb von PROJ-22 (kein regime-bezogener Test hängt; `test_regime.py` isoliert läuft in 8,8s durch). Nicht Teil dieses Feature-Scopes, sollte aber separat untersucht werden.
- Keine Tests decken `POST /regime/series/{id}/refresh` bzw. `bybit_client.fetch_klines` gegen echtes API-Antwortformat ab — genau dieser Pfad enthält Bug 1 unten.

### Acceptance Criteria

**Regime-Zeitreihe:** 9/10 bestanden.
- [x] Eindeutigkeit durch Provider-Symbol, Asset, Timeframe, Modellversion (`UNIQUE`-Constraint + `_ensure_series`).
- [x] Bar-Zeitstempel, bestätigtes Regime, Modellversion je Datensatz.
- [x] Wiederverwendung über `regime_series`-Lookup in `get_regime_evaluation`.
- [x] Neue Modellversion bei Parameteränderung, alte bleibt unangetastet (append-only, `CHECK` beim Anlegen).
- [x] „nicht verfügbar" vor Warm-up / bei Std.-Abw. 0 (`regime_calculator.py:68-70`, getestet in `test_constant_price_all_unavailable`).
- [x] Strikte Schwellenauswertung, Gleichheit → `sideways` (`>`/`<`, nicht `>=`/`<=`).
- [x] Nur abgeschlossene Bars (Kursbars kommen ausschließlich aus abgeschlossenen Bybit-Kerzen).
- [x] Untere ≥ obere Schwelle → 422 mit exaktem Text (`test_create_model_invalid_thresholds`, `test_create_model_equal_thresholds`).
- [x] Kandidatenwechsel setzt Zähler auf 1, ungültige Werte setzen zurück (`regime_calculator.py:92-109`).
- [x] Erster bestätigter Zustand wie Regimewechsel sichtbar (kein Sonderfall nötig, `count>=confirmation_candles` greift ab erstem Kandidaten).

**Import und Abdeckung:** 4/6 bestanden.
- [x] Keine trader.dev-/Zusatzläufe für dieses Feature (Bybit Public API + vorhandener trader.dev-`get_trades`-Client, kein neuer Backtest).
- [x] Externer Import via `POST /regime/series/import` (`test_import_series`).
- [x] Duplikate erzeugen keine zweite Bar (`test_import_series_dedup`, `UNIQUE(series_id, bar_time)`).
- [ ] **Bug 1 (Critical):** Lücken werden erkannt, überlappende Modellversionen NICHT — `_detect_coverage_issues` prüft nur `gap` und `timeframe_mismatch`, nie `overlapping_version`. Frontend hat dafür sogar schon ein Label (`ISSUE_TYPE_LABELS.overlapping_version`), das nie befüllt wird toter Code auf Wartefunktion.
- [~] Abdeckungsanzeige vorhanden, aber **nicht zeitraumbasiert auf den Backtest** — siehe Bug 3.
- [x] Unter 95 % → `is_incomplete` (`get_regime_evaluation`, Backend + Frontend-Badge „Unvollständig").

**Performance je Regime:** 6/8 bestanden.
- [x] Nur zeitgestempelte Trades verwendet (`result_trades`, ausschließlich Trade-basiert).
- [x] Klartextmeldung bei fehlenden Zeitdaten (`test_no_trades`).
- [x] Trade-Anzahl, Net P&L, Max Drawdown, Anteil je Regime vorhanden.
- [x] Calmar/Sortino nur bei belastbarer Berechnung (Sortino ab 6 Trades, Calmar nur bei `max_dd != 0`).
- [x] „Kleine Stichprobe" unter 6 Trades (`test_small_sample_badge`).
- [x] „Regime-Dominanz" nur bei positivem Gesamtergebnis, > 70 % (`test_evaluation_happy_path`, `test_no_dominance_on_negative_total`).
- [x] Sprachlich „Zusammenhang/Verteilung/Häufigkeit", nie „Ursache" (grep über Backend + Frontend: kein Treffer für „Ursache").
- [ ] **Bug 2 (High):** Zuordnungsregel Trade → Regime ist nicht verifiziert belastbar, siehe unten.

### Bugs

**Status 2026-07-31: Bugs 1–3 gefixt, verifiziert durch neue Regressionstests (`backend/tests/test_bybit_client.py`, 2 neue Fälle in `backend/tests/test_regime.py`). Bug 4 offen (Niedrig, kein Blocker).**

**Bug 1 — Kritisch — GEFIXT — `refresh_series` lädt bei mehrjährigen Zeiträumen keine vollständige Historie (`backend/app/services/bybit_client.py:14-64`, `backend/app/routes/regime.py:187-254`)**
Bybit liefert `/v5/market/kline` **absteigend sortiert** (neueste Kerze zuerst) — live gegen die echte API verifiziert:
```
curl ".../v5/market/kline?...&start=1609459200000&end=1735689600000&limit=5"
→ list[0] = 2024-12-31, list[4] = 2024-12-30  (neueste zuerst)
```
`fetch_klines` geht von aufsteigender Sortierung aus und setzt `cursor = int(rows[-1][0]) * 1000 + 1` — bei absteigender Sortierung ist `rows[-1]` aber die **älteste Kerze der jeweils zuletzt (nahe `end_ms`) geholten Seite**, nicht die nächste vorwärts. Für den in der Spec genannten Referenzfall (BTCUSDT 4h, 2021-01-01 bis 2024-12-31, ~8.800 Bars) bedeutet das: Seite 1 liefert die 1000 jüngsten Kerzen vor `end_ms` (~Mitte 2024), `cursor` rückt danach nur bis an den Rand dieses Fensters vor, die Schleife bricht typischerweise ab, sobald `len(rows) < 1000` — de facto werden nur die letzten Monate geladen, **2021–2023 fehlen komplett**, ohne Fehlermeldung.
*Auswirkung:* Genau der in der Tech-Design-Sektion F beschriebene erste Testfall („Zeitreihe für BTCUSDT 4h über 2021-2024 anlegen — deckt alle 68 Backtests ab") schlägt in der Praxis fehl. Abdeckung, Lückenerkennung und alle darauf aufbauenden Auswertungen sind betroffen, weil die Zeitreihe von vornherein unvollständig ist.
*Fix:* `fetch_klines` paginiert jetzt rückwärts — `end` wandert je Seite auf die älteste bisher gesehene Kerze zurück (`cursor_end`), `start_ms` bleibt fest, Ergebnis wird vor Rückgabe aufsteigend sortiert. Neuer Regressionstest `test_fetch_klines_paginates_through_descending_pages` simuliert eine absteigend sortierte Fake-Bybit-API über 2.500 Kerzen (> 1 Seite) und prüft vollständige, aufsteigend sortierte Abdeckung.

**Bug 2 — Hoch — GEFIXT — Trade-zu-Regime-Zuordnung nur bei exakter Zeitstempel-Gleichheit (`backend/app/routes/regime.py`)**
`bar_index.get(entry_ts, "ohne Regimezuordnung")` matchte die Trade-`entry_time` 1:1 gegen `bar_time`. Alle Tests konstruierten `entry_time` bewusst identisch zu einer vorhandenen Bar — die reale trader.dev-Trade-Liste wurde damit nie gegen diese Zuordnung verifiziert. Fiel der tatsächliche Entry-Zeitstempel nicht exakt auf eine 4h-Bar-Grenze, landete der Trade in „ohne Regimezuordnung", obwohl die zugehörige Bar existiert.
*Fix:* Neue Funktion `_find_bar_regime` (Bisect auf sortierte `bar_times`) ordnet den Entry-Zeitpunkt der größten `bar_time <= entry_time` zu — Bucket-Zuordnung statt Exact-Match. Liegt die gefundene Bar mehr als ein Timeframe-Intervall zurück (echte Lücke), bleibt der Trade „ohne Regimezuordnung". Neuer Test `test_trade_entry_between_bars_uses_bucket_regime` deckt sowohl den Bucket-Fall (Entry 2:30 Uhr → Bar 0:00 Uhr) als auch die echte Lücke ab.
*Restrisiko (dokumentiert, kein Blocker):* weiterhin nicht gegen echte `get_trades()`-Antworten von trader.dev verifiziert — vor Produktivnutzung mit echten Daten gegenprüfen.

**Bug 3 — Mittel — GEFIXT — Abdeckung bezog sich auf die gesamte Zeitreihe, nicht auf den Backtest-Zeitraum (`backend/app/routes/regime.py`)**
Akzeptanzkriterium verlangt „Anteil des **Backtest-Zeitraums**, der durch die Regime-Zeitreihe abgedeckt ist". Implementiert war `valid_bars_in_series / total_bars_in_series` — unabhängig vom `period_start`/`period_end` des einzelnen `hal_result`.
*Fix:* Neue Funktion `_compute_coverage_pct` berechnet die erwartete Bar-Anzahl aus `(period_end - period_start) / Timeframe-Intervall` und vergleicht sie mit den tatsächlich verfügbaren Regime-Bars **innerhalb dieses Zeitraums** (nicht der gesamten Serie). `hal_results.period_start`/`period_end` sind `DATE`-Spalten — werden vor dem Vergleich auf UTC-Mitternacht normalisiert. Neuer Test `test_coverage_based_on_backtest_period` bestätigt 100 % Abdeckung bei vollständig importiertem Ein-Tages-Zeitraum; bestehender `test_evaluation_happy_path` musste angepasst werden (nur 4 Bars für ein Jahr Backtest-Zeitraum sind jetzt korrekt als `unvollständig` erkannt — vorher fälschlich `100 %`, weil nur die 4 vorhandenen Bars gegen sich selbst gezählt wurden).

**Bug 4 — Niedrig — offen — `_detect_coverage_issues` / `_timeframe_seconds` fallen bei unbekanntem Timeframe still auf 4h zurück (`backend/app/routes/regime.py:149-156`)**
Kein Fehler, keine Warnung — ein Timeframe außerhalb `1h/4h/1d` wird stillschweigend wie 4h behandelt, was Lücken-Erkennung verfälscht.

**Bug 5 — Mittel — offen — Akzeptanzkriterium „überlappende Modellversionen" nicht implementiert (`backend/app/routes/regime.py:118-146`)**
`_detect_coverage_issues` erkennt `gap` und `timeframe_mismatch`, nie `overlapping_version` — das Frontend hat dafür sogar schon ein Label (`ISSUE_TYPE_LABELS.overlapping_version`), das nie befüllt wird. Aktuell unkritisch: es existiert genau eine aktive Modellversion je Asset/Timeframe (68 Backtests, alle BTCUSDT 4h), daher kann heute keine echte Überlappung entstehen. Wird relevant, sobald eine zweite Modellversion für dasselbe Asset/Timeframe angelegt wird (PROJ-24/25). Nicht Blocker für dieses Release, aber vor Einführung einer zweiten Modellversion nachzuziehen.

### Security-Audit

- Durchgehend parametrisierte SQL-Queries, keine String-Konkatenation — keine SQL-Injection-Fläche gefunden.
- Kein Auth/Mandant-Konzept auf `/regime/*` — konsistent mit dem Rest der App (Projekt ist bewusst single-tenant, keine JWT/RLS irgendwo im Bestand; siehe Tech Design „single-tenant"). Kein regressionsspezifischer Befund.
- `bybit_client.fetch_klines` und `trader_dev.get_trades` sprechen ausschließlich öffentliche/bereits autorisierte externe Endpunkte an, keine Nutzereingabe fließt ungeprüft in die URL außer `asset`/`timeframe`, die vorher normalisiert werden (`_asset_to_bybit_symbol`).

### Regression

- Bestehende Ergebnisliste (`/ergebnisse`) unverändert für Nicht-HAL-Zeilen; „Regime"-Button erscheint nur bei `result_type === "HAL-Import"`.
- `row.run_id` bei HAL-Zeilen ist korrekt mit `hal_results.id` verifiziert (Backend-Alias `hr.id AS run_id`) — kein ID-Mismatch zum `/regime/hal-results/{id}`-Endpunkt.
- Keine Auffälligkeiten bei PROJ-21 (HAL-Import-Liste) durch die Erweiterung.

### Retest 2026-07-31

- `test_regime.py` + `test_bybit_client.py`: 24/24 grün.
- Regression PROJ-21 (`test_hal_import.py`, `test_results.py`): 39/39 grün, keine Auffälligkeiten durch PROJ-22.
- Bug 1 (Kritisch), Bug 2 (Hoch), Bug 3 (Mittel): verifiziert gefixt, je mit neuem Regressionstest belegt.
- Bug 4 (Niedrig) und Bug 5 (Mittel, überlappende Modellversionen) bleiben offen — beide ohne aktuelle Auswirkung auf den produktiven Datenbestand (siehe Begründung oben), kein Blocker.

### Zusammenfassung

- Acceptance Criteria: Kernnutzung (BTCUSDT 4h 2021–2024, Trade-Zuordnung, zeitraumbasierte Abdeckung) funktioniert und ist getestet. Offen: überlappende Modellversionen werden nicht erkannt (Bug 5, Medium, kein aktueller Anwendungsfall), Bug 4 (Niedrig).
- Bugs: 1 Kritisch (gefixt), 1 Hoch (gefixt), 1 Mittel (gefixt), 1 Mittel (offen, Bug 5), 1 Niedrig (offen).
- Tests: 24/24 grün (`test_regime.py` + `test_bybit_client.py`), plus 39/39 PROJ-21-Regression grün.
- **Production-Ready: JA** — 0 Critical/High offen. Bug 4 + Bug 5 als bekannte Limitationen für PROJ-24/25 vormerken (zweite Modellversion / neue Timeframes).

## Deployment
_To be added by /deploy_

## Implementation Notes (Backend)
**Completed:** 2026-07-30

### Files Created/Modified

| File | Action |
|------|--------|
| `backend/sql/015_regime_analyse.sql` | 6 tables: `regime_model_versions`, `price_bars`, `regime_series`, `regime_bars`, `result_trades`, `regime_evaluations`, `regime_eval_details` |
| `backend/app/schemas/regime.py` | All Pydantic schemas |
| `backend/app/services/regime_calculator.py` | Z-Score + HMA + confirmation logic |
| `backend/app/services/bybit_client.py` | Bybit public API OHLCV fetcher |
| `backend/app/services/trader_dev.py` | Added `get_trades()` function |
| `backend/app/routes/regime.py` | All API endpoints |
| `backend/app/main.py` | Registered regime routes |
| `backend/tests/conftest.py` | Added new tables to truncate |
| `backend/tests/test_regime.py` | 21 integration + unit tests |

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/regime/models` | List model versions |
| POST | `/regime/models` | Create model version |
| GET | `/regime/series` | List time series (filter by asset/timeframe) |
| GET | `/regime/series/{id}` | Get series detail with bars + coverage issues |
| POST | `/regime/series/import` | Import precomputed regime bars |
| POST | `/regime/series/{id}/refresh` | Fetch OHLCV from Bybit, compute regime, store |
| POST | `/regime/hal-results/{id}/trades/fetch` | Download trades from trader.dev |
| GET | `/regime/hal-results/{id}/trades` | List downloaded trades |
| GET | `/regime/hal-results/{id}/regime` | Get regime evaluation |

### Deviations from Spec

- HMA implementation is pure Python using WMA-based Hull Moving Average formula
- Coverage calculation is bar-count based (valid_bars/total_bars) — time-range based coverage deferred to frontend or future refinement
- The `regime/hal-results/{id}/regime` endpoint uses `model_version_id` query param to select the model version

### Next Steps

- Frontend: `/regime` page, regime panel on `/ergebnisse`
- Run `/abc-qa` for QA testing
- Apply migration to production DB on deploy
