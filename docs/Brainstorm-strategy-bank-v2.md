# Brainstorm V2: Strategy Bank Microapp

**Thema:** KI-gestützte Extraktion, Verifizierung und standardisierte Backtests von Trading-Strategien  
**Datum:** 2026-07-15  
**Status:** Konsolidiert und bereit als Input für `abc-requirements`  
**Vorgänger:** `docs/Brainstorm.md`  
**Review:** `docs/Brainstorm-strategy-bank-review.md`

---

## 1. Produktidee

Strategy Bank ist eine eigenständige Jupiter-Microapp für einen einzelnen Trader. Sie überführt Strategiebeschreibungen aus Textquellen in überprüfbare, deterministische Entry-/Exit-Regeln, führt standardisierte Backtests über trader.dev aus und macht die Ergebnisse reproduzierbar vergleichbar.

Die App soll nicht automatisch „gute Strategien erfinden“. Ihr Kernnutzen ist, den heute manuellen Weg von einer Strategiequelle bis zu einem nachvollziehbaren Vergleich zu verkürzen und dabei KI-Fehlinterpretationen, Credit-Verschwendung und nicht reproduzierbare Tests sichtbar zu verhindern.

## 2. Zielnutzer und Kontext

- Ein Solo-Nutzer, zugleich Trader und Entwickler
- Lokale beziehungsweise private Nutzung; kein Multi-Tenant-Betrieb
- Vorhandene Werkzeuge: Hal Second Brain, OpenCode, Codex und trader.dev MCP
- Geplanter Stack: Next.js 16 mit App Router, FastAPI und PostgreSQL/raw SQL
- Die konkrete technische Orchestrierung folgt erst nach einem trader.dev-Capability-Spike

## 3. Problem

Trading-Strategien liegen in uneinheitlichen Quellen vor. Regeln sind oft unvollständig, diskretionär oder nicht direkt ausführbar. Beim manuellen Übertragen entstehen Interpretationsfehler, Backtests verwenden unterschiedliche Annahmen und Ergebnisse lassen sich später nicht sicher auf die getestete Regelversion zurückführen.

Die App löst vier konkrete Probleme:

1. Regeln aus einer Quelle strukturiert erfassen.
2. Unklare KI-Auslegungen vor dem Backtest durch den Nutzer prüfen lassen.
3. Alle Strategien unter expliziten, vergleichbaren Annahmen testen.
4. Jede Kennzahl auf Strategieversion, Konfiguration und externen Report zurückführen.

## 4. MVP-Erfolgskriterium

Der MVP ist erfolgreich, wenn der Nutzer aus einer Text- oder Markdown-Quelle mindestens eine Strategie extrahieren, verifizieren und ohne manuelle Übertragung bei trader.dev auf drei konfigurierten Instrumenten testen kann und danach für jedes Ergebnis eindeutig sieht:

- welche Regelversion getestet wurde,
- mit welchen Markt-, Ausführungs- und Kapitalannahmen sie getestet wurde,
- welchen Status der Lauf hat,
- welche Kernmetriken zurückgegeben oder berechnet wurden,
- wo der zugehörige trader.dev-Report liegt.

## 5. Begriffe

- **Quelle:** Ein eingefügter Text oder eine Markdown-Datei, aus der Strategien extrahiert werden.
- **Strategie:** Die fachliche Idee mit Name, These, Kategorie und Herkunft.
- **Strategieversion:** Eine unveränderliche, vollständig definierte Fassung der Regeln und Parameter. Jede freigegebene Änderung erzeugt eine neue Version.
- **Entwurf:** Eine extrahierte, noch nicht für Backtests freigegebene Strategieversion.
- **Run:** Ein Backtest einer Strategieversion auf genau einem Instrument und in genau einem Richtungsmodus.
- **Batch:** Eine vom Nutzer bestätigte Gruppe mehrerer Runs.
- **Backtest-Profil:** Wiederverwendbare Markt-, Ausführungs- und Kapitalannahmen.
- **Nicht testbar:** Zustand für eine Strategie, deren Regeln nicht ohne Erfindung fehlender Logik deterministisch formuliert werden können.

## 6. Verbindliche MVP-Entscheidungen

### Quellen

- Ein Vorgang enthält genau eine Quelle.
- Unterstützt werden eingefügter Klartext und eine Markdown-Datei.
- Eine Quelle kann mehrere Strategien enthalten.
- PDF, OCR, Screenshots, Web-Links und Multi-Upload sind nicht Teil des MVP.

### KI und Agent-Runtime

- MVP verwendet genau einen konfigurierten OpenCode-Runtime-/Modell-Pfad.
- Es gibt keinen automatischen Provider-Fallback.
- Codex und weitere Provider sind spätere Erweiterungen.
- Ein Modellwechsel erzeugt neue Extraktionsmetadaten; bestehende Strategieversionen bleiben unverändert.

### Strategietyp

- MVP unterstützt deterministische Entry-/Exit-Signal-Strategien.
- Stop-Loss, Take-Profit, Trailing Stops, Portfolio-Optimierung und Parameter-Sweeps sind nicht Teil des MVP.
- Diskretionäre Aussagen werden nicht stillschweigend konkretisiert. Sie werden als offene Unklarheit markiert.
- Eine Strategie mit offenen Unklarheiten kann nicht freigegeben werden.

### Richtung

- Default ist ein kombinierter Long-/Short-Run.
- Pro Batch kann alternativ Long-only oder Short-only gewählt werden.
- Jeder Richtungsmodus ist ein eigener Run und wird separat in die Credit-Schätzung aufgenommen.
- Ein Long-/Short-Split aus einem Detailreport ersetzt keinen separat angeforderten Richtungsmodus.

### Standard-Testuniversum

Vorläufige fachliche Defaults:

| Fachliches Instrument | Zielprodukt | Provider-ID |
|---|---|---|
| Bitcoin | BTC/USDT Spot | im Capability-Spike zu bestätigen |
| S&P 500 | SPY ETF | im Capability-Spike zu bestätigen |
| Gold | XAU/USD Spot Gold | im Capability-Spike zu bestätigen |

- Default-Timeframe: 4 Stunden
- Research-/Backtest-Zeitraum: 2021-01-01 bis 2024-12-31
- Historischer Out-of-Sample-Holdout: ab 2025-01-01 bis zum Zeitpunkt, an dem eine Strategieversion eingefroren wird
- Echtes Forward-Testing: ausschließlich Bars nach dem Einfrieren der jeweiligen Strategieversion
- Instrumente, Timeframe und Zeitraum sind pro Batch änderbar, müssen aber als exakte Provider-Werte gespeichert werden.
- Falls trader.dev eines der Zielprodukte nicht unterstützt, wird vor Umsetzung ein fachlich gleichwertiger Ersatz festgelegt; keine stille Symbolersetzung.

Der Research-Zeitraum umfasst bewusst vier vollständige Kalenderjahre mit unterschiedlichen Bitcoin-Marktphasen und dem Halving 2024. Er wird als **vierjähriges Marktzyklus-Fenster** bezeichnet, nicht als exakter Halving-zu-Halving-Zyklus: Der vorherige Halving-Zyklus lief ungefähr von Mai 2020 bis April 2024.

Für die zeitliche Validierung gelten folgende Regeln:

- Daten ab 2025 dürfen während Extraktion, Regelklärung, Parameterauswahl und Ranking nicht angezeigt oder verwendet werden.
- Nach dem Einfrieren einer Strategieversion darf der Nutzer den historischen Holdout ab 2025 einmalig auswerten.
- Wurden Ergebnisse aus 2025 bereits zur Änderung der Strategie verwendet, ist 2025 für diese neue Version kein unangetasteter Holdout mehr.
- Der echte Forward-Test einer Version beginnt mit ihrem gespeicherten `frozen_at`-Zeitpunkt und wächst nur mit danach neu entstandenen Bars.
- Research-, historisches Holdout- und echtes Forward-Ergebnis werden getrennt gespeichert und angezeigt.

### Backtest-Profil

Alle Runs eines Vergleichs verwenden dasselbe Profil. Das Profil enthält mindestens:

- Datenquelle und Provider-Symbol
- Zeitzone und Handelssitzung
- Signalzeitpunkt und Fill-Zeitpunkt
- Ordertyp
- Gebühren, Spread und Slippage
- Startkapital und Quote-Währung
- Positionsgröße und Compounding-Regel
- Leverage
- Pyramiding und maximal gleichzeitig offene Positionen
- Umgang mit fehlenden Bars und Corporate Actions

Arbeitsdefault für Requirements: Signal auf Schlusskurs, Ausführung zum nächsten verfügbaren Bar-Open, eine Position je Run, kein Pyramiding und kein Leverage. Gebühren, Slippage, Startkapital und Positionsgröße müssen im trader.dev-Spike anhand der tatsächlich unterstützten Eingaben festgelegt werden.

### Datenschutz und Credits

- Private oder proprietäre Strategien dürfen erst an trader.dev gesendet werden, wenn der verwendete Tarif und die konkrete Aktion nachweislich private Verarbeitung erlauben.
- Bis dahin sind ausschließlich bewusst öffentliche Teststrategien zulässig.
- Vor dem Start zeigt die App die erwartete Anzahl externer MCP-Aktionen und ein hartes Credit-Maximum für den Batch.
- Der Nutzer muss den Batch und das Credit-Maximum explizit bestätigen.
- Tarifhöhe, Credit-Menge und Reset-Zeitraum sind externe, veränderliche Konfiguration; keine Werte werden im Produkt fest codiert.

## 7. Kanonisches Strategie-Zwischenformat

Jeder Entwurf enthält:

- Strategie-ID und Versionsnummer
- Name und kurze These
- feste Kategorie
- Richtung: kombiniert, Long-only oder Short-only
- Parameter mit Name, Wert, Einheit und erlaubtem Bereich
- Entry-Regel als eindeutige boolesche Bedingung
- Exit-Regel als eindeutige boolesche Bedingung
- Warm-up-Anforderung
- Verhalten bei gleichzeitigem Entry und Exit
- Reversal-Verhalten
- Quellenbeleg je Regel: Textausschnitt beziehungsweise Zeilenreferenz
- Quell-Hash
- offene Unklarheiten
- Extraktionsmodell, Prompt-Version und Zeitstempel
- Status: Entwurf, nicht testbar oder freigegeben

Die KI darf fehlende Werte vorschlagen, muss sie aber als Vorschlag markieren. Erst eine ausdrückliche Nutzerbestätigung macht daraus eine freigegebene Regel.

## 8. Feste MVP-Kategorien

- Trendfolge
- Mean Reversion
- Breakout
- Volatilität
- Momentum
- Saison/Zeit
- Preis-/Candlestick-Muster
- Hybrid
- Sonstige

Die KI schlägt eine Kategorie aus den verifizierten Regeln vor. Der Nutzer kann sie korrigieren. Kategorien werden im MVP nicht aus Backtest-Ergebnissen abgeleitet und die Liste ist noch nicht erweiterbar.

## 9. Happy Path

1. Nutzer fügt Text ein oder lädt eine Markdown-Datei hoch.
2. App speichert Quelle und Quell-Hash.
3. KI erkennt eine oder mehrere Strategien und erzeugt Entwürfe mit Quellenbelegen.
4. Nutzer prüft Regeln, löst Unklarheiten und gibt eine unveränderliche Version frei.
5. Nutzer wählt Instrumente, Zeitraum, Timeframe, Richtung und Backtest-Profil.
6. App zeigt geplante Runs, erwartete MCP-Aktionen und Credit-Maximum.
7. Nutzer bestätigt den Batch.
8. Queue führt jeden Run idempotent über den einen konfigurierten Agent-Runtime-Pfad aus.
9. App speichert strukturierte Ergebnisse, Report-Link und Reproduktionsmetadaten.
10. Nutzer filtert und sortiert die Ergebnisse.

## 10. Job-Lebenszyklus

Ein Run hat genau einen dieser Zustände:

`geplant → bestätigt → in_queue → läuft → erfolgreich | fehlgeschlagen | abgebrochen`

Zusätzliche Regeln:

- Derselbe Idempotency-Key darf keinen zweiten externen Run auslösen.
- Ein Fehler in einem Run stoppt nicht automatisch den gesamten Batch.
- Fehlgeschlagene Runs zeigen einen verständlichen Fehlergrund.
- Ein Retry ist eine bewusste Nutzeraktion und darf erneut Credits verbrauchen.
- Ein noch nicht gestarteter Run kann abgebrochen werden.
- Ein Batch zeigt Fortschritt und Teilergebnisse.

## 11. Ergebnisse und Vergleich

Pflichtfelder je erfolgreichem Run:

- Net Return in Prozent
- CAGR in Prozent
- Trade Count
- Max Drawdown in Prozent
- Sharpe Ratio
- Profit Factor
- Calmar Ratio
- trader.dev-Report-Link

Calmar wird als `CAGR / abs(Max Drawdown)` berechnet. Ist Max Drawdown null oder fehlt ein Eingangswert, wird Calmar als nicht verfügbar angezeigt und nicht künstlich ersetzt.

Die Ergebnistabelle unterstützt:

- Filter nach Strategie, Version, Instrument, Kategorie, Richtung und Status
- Sortierung nach jeder einzelnen Metrik
- Kennzeichnung niedriger Aktivität; Default ist weniger als 24 Trades im vierjährigen Gesamtzeitraum
- sichtbare Unterscheidung von Research-, historischem Holdout- und echtem Forward-Ergebnis

Nicht im MVP:

- Composite Score
- automatische Gewinner-Empfehlung
- statistische Signifikanzbehauptung aus einer bloßen Mindestanzahl von Trades
- Vergleich von Runs mit unterschiedlichen Backtest-Profilen als wären sie gleichwertig

## 12. Reproduzierbarkeit und Audit-Trail

Jeder Run referenziert dauerhaft:

- unveränderliche Strategieversion
- vollständiges Backtest-Profil
- Instrument-ID, Timeframe und Zeitraum
- Richtungsmodus
- Agent-Runtime und Modell
- Prompt-/Executor-Version
- verwendete trader.dev-MCP-Aktion
- verfügbare Engine- und Datenstand-Angaben
- Start-, End- und Erstellungszeitpunkt
- externen Report und rohe strukturierte Antwort, sofern verfügbar

Änderungen überschreiben keine historischen Runs.

## 13. Fehler- und Grenzfälle

- Quelle enthält keine Strategie: verständlicher Hinweis, keine Entwürfe.
- Quelle enthält mehrere Strategien: getrennte Entwürfe mit eigenen Belegen.
- Regel bleibt diskretionär: Status „nicht testbar“ mit Begründung.
- KI-Ausgabe ist syntaktisch oder fachlich unvollständig: Entwurf bleibt gesperrt.
- Keine Trades: erfolgreicher Run mit Trade Count 0; ratios werden als nicht verfügbar behandelt.
- trader.dev unterstützt Instrument, Timeframe oder Zeitraum nicht: Run wird vor externer Ausführung blockiert.
- Credit-Maximum reicht nicht: Batch startet nicht.
- Privacy ist für den Inhalt nicht bestätigt: Batch startet nicht.
- Externer Timeout oder Teilfehler: Status fehlgeschlagen, kein stiller Retry.
- Report-Link fehlt trotz erfolgreicher Metriken: Ergebnis bleibt sichtbar und wird als unvollständig markiert.

## 14. Nichtfunktionale Anforderungen

- API-Keys und Secrets werden nie im Frontend, in Prompts, Logs oder Hal-Dateien gespeichert.
- Lokale Single-User-Authentisierung genügt; Multi-Tenant-Rollen sind ausgeschlossen.
- Externe Aktionen benötigen ein explizites Nutzer-Gate.
- Historische Strategieversionen und Runs sind unveränderlich.
- Verarbeitung muss nach Prozessneustart anhand persistierter Zustände fortsetzbar sein.
- Die App darf keine Renditeversprechen oder Live-Trading-Freigaben aus Backtests ableiten.

## 15. Capability-Spike vor Implementierung der Backtest-Ausführung

Der Spike ist ein Umsetzungsgate, keine offene Produktentscheidung. Er muss mit einem echten trader.dev-Konto nachweisen:

1. Welche MCP-Tools und Input-/Output-Schemas verfügbar sind.
2. Ob OpenCode den MCP-Server zuverlässig headless ansprechen kann.
3. Welche exakten Provider-IDs, Timeframes und Historien für die drei Zielinstrumente unterstützt werden.
4. Ob Richtung, Fees, Slippage, Kapitalmodell und Fill-Regeln konfigurierbar sind.
5. Welche Metriken und Rohdaten strukturiert zurückgegeben werden.
6. Wie viele Credits ein Run und notwendige Hilfsaktionen tatsächlich verbrauchen.
7. Welcher Tarif private Strategien für die konkrete Aktion nachweislich privat hält.
8. Ob Report-Links dauerhaft, privat und maschinenlesbar referenzierbar sind.

Scheitert ein Punkt, werden die Requirements an die belegte Capability angepasst, bevor die Backend-Architektur festgelegt wird.

## 16. MVP-Backlog für `abc-requirements`

1. **Quellenerfassung** – Text und Markdown, Quell-Hash, genau eine Quelle pro Vorgang
2. **KI-Extraktion** – mehrere Strategien erkennen, kanonische Entwürfe mit Quellenbelegen und Unklarheiten erzeugen
3. **Verifizierung und Versionierung** – Regeln bearbeiten, Freigabe-Gate, unveränderliche Versionen, Status „nicht testbar“
4. **Batch-Konfiguration** – Instrumente, Timeframe, Zeitraum, Richtung und Backtest-Profil auswählen
5. **Credit- und Privacy-Gate** – geplante Aktionen, hartes Credit-Maximum und bestätigte Privatheitsstufe prüfen
6. **Queue und trader.dev-Ausführung** – idempotente Runs, Status, Abbruch, bewusster Retry und Teilfehler
7. **Ergebnisvergleich** – Kernmetriken, Filter, Einzelsortierung, Trennung von Research, historischem Holdout und echtem Forward-Test sowie Report-Link
8. **Audit-Trail** – Strategieversion, Konfiguration, Runtime und externe Metadaten reproduzierbar speichern
9. **Markdown-Export** – eine Strategie samt Versionen und Runs als lokale Markdown-Datei exportieren

## 17. Spätere Features

### Phase 2

- PDF- und Screenshot-OCR für lesbaren Regeltext
- automatische Hal-Synchronisierung auf Basis des MVP-Markdown-Exports
- zweiter Agent-/Modellprovider und manuelle Provider-Auswahl
- freie Web-Links mit SSRF-, Prompt-Injection- und Inhaltskontrollen
- anpassbare Kategorien
- Multi-Upload
- getrennte Long-/Short-Detailauswertung, sofern strukturierte Daten verfügbar sind

### Phase 3

- ADX-/ATR-basierte Regime-Analyse
- Signal-Reverse-Engineering aus Signalzeitpunkten oder Charts
- normalisierter Composite Score mit dokumentierter Vergleichsgruppe, Caps und Missing-Value-Regeln
- Parameter-Sweeps und Robustheitstests
- Walk-forward- oder weitergehende Out-of-Sample-Verfahren

## 18. Bewusst verworfene beziehungsweise verschobene Ideen

**[Ranking #1] Gewichteter Rohwert-Score**  
_Konzept:_ Calmar, Sharpe, Profit Factor und Trade Count direkt gewichten.  
_Entscheidung:_ Verschoben, weil unterschiedliche Skalen und Ausreißer ohne Normalisierung irreführend sind.

**[Integration #1] Automatische Hal-Pflege**  
_Konzept:_ Eine mitwachsende Hal-Notiz je Strategie.  
_Entscheidung:_ Verschoben. MVP erzeugt zunächst einen lokalen, deterministischen Markdown-Export; Hal-Sync baut später darauf auf.

**[Extraction #1] Beliebige Quellenformate**  
_Konzept:_ PDF, Screenshot, URL und Text im ersten Release.  
_Entscheidung:_ MVP bleibt bei Text/Markdown, damit zuerst die Kernschleife validiert wird.

**[KI #1] Automatischer Provider-Fallback**  
_Konzept:_ OpenCode primär, Codex automatisch als Ersatz.  
_Entscheidung:_ Verschoben, weil automatische Wiederholung Kosten, Reproduzierbarkeit und Fehlerdiagnose verschlechtert.

**[Research #1] Signal-Reverse-Engineering**  
_Konzept:_ Regeln aus Signalen, Equity-Kurven oder Performance-Screenshots ableiten.  
_Entscheidung:_ Phase 3; keine notwendige Funktion für den Kernnutzen des MVP.

## 19. Externe Fakten mit Verifikationsstatus

- trader.dev bietet einen MCP-Zugang und beschreibt Credits als Abrechnung pro MCP-Aktion.
- Die öffentliche Pricing-Seite nennt Free, Starter und Pro, veröffentlicht aber keinen verlässlichen exakten Free-Credit-Betrag.
- „Keep strategies private“ ist öffentlich beim Pro-Tarif genannt; Privacy anderer Tarife wird nicht vorausgesetzt.
- Eine öffentliche REST-API wurde nicht gefunden. Das ist eine Arbeitsannahme, kein Beweis, dass keine API existiert.
- Übliche Calmar-Definition: annualisierte zusammengesetzte Rendite geteilt durch absoluten maximalen Drawdown.

Quellen, geprüft am 2026-07-15:

- [trader.dev Pricing](https://mcp-api.trader.dev/pricing)
- [trader.dev MCP-Einstieg](https://mcp-api.trader.dev/)
- [Morningstar: Calmar Ratio](https://admainnew.morningstar.com/directhelp/Glossary/Custom_Statistics/Calmar_Ratio.htm)
- [Wiecki et al.: Backtest- und Out-of-Sample-Performance](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2745220)

## 20. Übergabe an `abc-requirements`

`abc-requirements` soll aus den neun MVP-Backlogpunkten konkrete User Stories, Akzeptanzkriterien und Edge Cases erstellen. Die technischen Details der trader.dev-Anbindung dürfen erst nach dem Capability-Spike als feste Architekturentscheidung behandelt werden. Phase-2-/Phase-3-Ideen dienen nur als Abgrenzung und erzeugen keine vorbereitenden MVP-Anforderungen.
