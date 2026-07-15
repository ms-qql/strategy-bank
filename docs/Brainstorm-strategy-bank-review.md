# Review: Brainstorm „Strategy Bank Microapp“

**Datum:** 2026-07-15  
**Review-Ziel:** Eignung von `Brainstorm.md` als Input für `abc-requirements`  
**Urteil:** Gute Produktidee und brauchbare Kernschleife, aber noch nicht requirements-reif. Mehrere Aussagen widersprechen sich, einige Kennzahlen sind fachlich falsch oder nicht definiert, und der MVP enthält zu viele unbewiesene Integrationsannahmen.

## Was bereits trägt

- Klarer Solo-User und klarer Hauptnutzen: Strategien aus Quellen schneller vergleichbar machen.
- Sinnvolle Kernschleife: Quelle → Extraktion → menschliche Prüfung → Backtest → Vergleich.
- Das Freigabe-Gate vor kostenpflichtigen MCP-Aktionen ist richtig.
- Phase 2 trennt Regime-Analyse und Reverse Engineering grundsätzlich sinnvoll ab.
- Die Strategie-Note als langlebiges Objekt ist besser als eine Note pro Lauf.

## Fehler und Widersprüche

| Priorität | Stelle | Befund | Korrektur |
|---|---|---|---|
| Blocker | Long/Short | Initial ist der Modus zwischen kombiniert, Long-only und Short-only umschaltbar; später ist ausschließlich kombiniert vorgesehen. | Für MVP genau eine Regel festlegen. Vorschlag: kombiniert als Default, Modus pro Batch auswählbar; jeder gewählte Modus ist ein eigener Backtest und verbraucht entsprechend Credits. |
| Blocker | KI-Fallback | Initial ist Codex ein Fallback; später gibt es ausdrücklich keinen automatischen Fallback, sondern einen manuellen globalen Switch. | Vorschlag: v1 hat genau einen konfigurierten Agent-Runtime-Pfad. Ein zweiter Provider ist Phase 2. Falls beide bleiben: „manuelle Auswahl, kein automatischer Fallback“. |
| Blocker | trader.dev Privacy | Das Dokument nennt Starter als privaten Tarif. Die aktuelle Pricing-Seite nennt „Keep strategies private“ nur bei Pro. Dass Free-Strategien standardmäßig öffentlich sind, ist öffentlich nicht eindeutig dokumentiert. | Bis zum Capability-Spike keine privaten Strategien senden. Privacy je Tarif und je MCP-Aktion mit einem echten Konto verifizieren; Pro als derzeit einzige öffentlich belegte Privat-Option behandeln. |
| Hoch | trader.dev Credits | „1 Credit = 1 Backtest“ ist zu eng. trader.dev beschreibt 1 Credit pro MCP-Aktion, darunter Backtest, Optimierung oder Signalabfrage; außerdem werden typischerweise 10–30 Credits pro ausgearbeiteter Strategie genannt. | Kosten als Schätzung aus tatsächlich geplanten MCP-Aktionen berechnen. Vor Queue-Freigabe erwartete Maximalcredits anzeigen und ein Batch-Limit verlangen. |
| Hoch | Credit-Zeitraum | Tabelle behauptet 1.000 Credits mit wöchentlichem Reset; offene Punkte sagen zugleich, der Betrag sei unbekannt. Die öffentliche Seite nennt keinen exakten Betrag und verwendet widersprüchlich „monthly“ und „weekly“. | Betrag und Reset nicht als Fakt führen. Als extern zu verifizierende Tarifkonfiguration markieren. |
| Hoch | Calmar | `Net Profit / Max Drawdown` ist nicht die übliche Calmar-Formel. | `CAGR / abs(Max Drawdown)` verwenden; Zeitraum, Prozentbasis und Verhalten bei Drawdown 0 definieren. Morningstar definiert Calmar als compounded annual return geteilt durch maximum drawdown. |
| Hoch | Composite Score | Rohwerte von Calmar, Sharpe, Profit Factor und Trade Count werden addiert, obwohl Skalen und Ausreißer stark verschieden sind. | Im MVP keinen gewichteten Score. Zuerst harte Ausschlussregeln und sortierbare Einzelmetriken. Score erst nach Definition von Normalisierung, Caps, Missing Values und Vergleichsgruppe. |
| Hoch | „Signifikanz“ | `≥6 Trades/Jahr` wird als Signifikanz-Schwelle bezeichnet, ist aber nur eine Produktregel und keine statistisch begründete Signifikanz. | In „Mindestaktivität: Default 24 Trades im vierjährigen Test, vom Nutzer änderbar“ umbenennen; keine Signifikanzbehauptung. |
| Hoch | Screenshot-Scope | Screenshot ist MVP-Quelle; das nötige Reverse Engineering aus Signalen/Equity-Kurve liegt aber in Phase 2. | MVP-Screenshots nur für lesbaren Regeltext/OCR zulassen. Performance-Charts oder Signallisten ohne Regeln explizit ablehnen und auf Phase 2 verweisen. |
| Mittel | Kategorien | Kategorie aus der Backtest-Ergebnisverteilung abzuleiten vermischt Verhaltensklassifikation mit der fachlichen Strategielogik. | Kategorie aus den verifizierten Regeln ableiten oder vom Nutzer setzen; Ergebnisverhalten separat taggen. |
| Mittel | Architekturbehauptung | „Keine öffentliche REST-API gefunden“ wird als bestätigte Negativaussage behandelt und daraus direkt eine Agent-Architektur abgeleitet. | Als Annahme kennzeichnen. Erst einen kleinen Integrations-Spike durchführen: MCP-Tools, Input-/Output-Schema, Auth, Privacy, Limits und Headless-Aufruf belegen. |

Quellen: [trader.dev Pricing](https://mcp-api.trader.dev/pricing), [trader.dev MCP-Einstieg](https://mcp-api.trader.dev/), [Morningstar Calmar-Definition](https://admainnew.morningstar.com/directhelp/Glossary/Custom_Statistics/Calmar_Ratio.htm).

## Fachliche Lücken im Backtest-Vertrag

Ohne diese Angaben sind Resultate weder reproduzierbar noch sinnvoll vergleichbar:

- **Instrumente:** „BTC“ und „Gold“ sind zu ungenau. Benötigt werden Provider-Symbol, Venue und Produkttyp, etwa `BTCUSDT` Spot auf einer bestimmten Börse sowie `XAUUSD`, `GC` oder `GLD`.
- **Marktdaten:** Datenquelle, Zeitzone, Handelssitzung, Umgang mit fehlenden Bars, Splits/Dividenden bei SPY und verfügbare Historie.
- **Ausführung:** Signalzeitpunkt versus Fill-Zeitpunkt, Market/Limit, Fees, Spread, Slippage und Verhalten bei Gaps.
- **Kapitalmodell:** Startkapital, Positionsgröße, Leverage, Pyramiding, gleichzeitig offene Positionen und Compounding.
- **Strategie-Semantik:** Reihenfolge bei gleichzeitigem Entry/Exit, Reversal, Warm-up-Periode, Look-ahead-Schutz und Behandlung unentscheidbarer Regeln.
- **Vergleichseinheit:** Kennzahlen als Prozent oder Betrag; Jahresannualisierung für 24/7-Krypto versus Börsensitzungen.
- **Validierung:** Ein einzelner Zeitraum 2021–2024 fördert Auswahl auf In-Sample-Ergebnisse. Mindestens ein unangetasteter Holdout oder ein klarer Research-/Validation-Split fehlt. Empirische Forschung zeigt, dass häufiges Backtesten die Lücke zur Out-of-Sample-Performance vergrößern kann ([Wiecki et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2745220)).

## Produkt- und Betriebs-Lücken

- **Strategie-Zwischenformat:** Es fehlt ein kanonisches, editierbares Schema für Name, These, Parameter, Entry, Exit, Richtung, Quellenbeleg und offene Unklarheiten.
- **Provenienz:** Jede extrahierte Regel sollte Seiten-/Textstelle und Quell-Hash behalten; sonst kann der Nutzer die KI-Auslegung kaum prüfen.
- **Versionierung:** Änderung einer Regel oder eines Parameters muss eine neue unveränderliche Strategieversion erzeugen. Ein Lauf referenziert exakt diese Version.
- **Job-Lebenszyklus:** Status, Timeout, Retry, Abbruch, Teilfehler, Duplikatschutz und Wiederaufnahme nach Prozessabbruch fehlen.
- **Kostenkontrolle:** Credit-Schätzung, hartes Batch-Budget und explizite Bestätigung vor Absenden fehlen.
- **Reproduzierbarkeit:** Pro Lauf gehören Agent/Modell, Prompt-Version, MCP-Tool, Engine-/Datenstand, Einstellungen und Zeitstempel gespeichert.
- **Externe Links:** Freie URL-Übernahme bringt SSRF-, Prompt-Injection- und urheberrechtliche Risiken. Für v1 besser streichen oder auf manuell eingefügten Text begrenzen.
- **Hal-Synchronisierung:** Dateipfad, Namenskollisionen, idempotente Updates, manuelle Änderungen im Vault und Fehlerverhalten sind offen.
- **Ergebnisqualität:** Neben technischen Fehlern braucht es den Status „nicht testbar“ mit konkreter Begründung, statt vage Regeln stillschweigend zu erfinden.

## Empfohlener Scope

### MVP: eine belastbare vertikale Schleife

1. **Quelle erfassen:** Markdown oder eingefügter Text; genau eine Quelle je Vorgang.
2. **Strategien extrahieren:** Eine oder mehrere Strategien in ein festes Zwischenformat, jeweils mit Quellenbelegen und markierten Unklarheiten.
3. **Strategie verifizieren:** Regeln und Parameter editieren; nur vollständig deterministische Versionen freigeben.
4. **Batch konfigurieren:** Fest definierte Instrument-IDs, Zeitraum, Timeframe, Richtung und Ausführungsannahmen wählen; Kostenobergrenze bestätigen.
5. **Backtest ausführen:** Ein nachgewiesener Agent-Runtime-Pfad über trader.dev MCP; idempotente Queue mit Status und Fehlertext.
6. **Ergebnisse vergleichen:** CAGR/Net Return, Max Drawdown, Calmar, Sharpe, Profit Factor und Trade Count; filtern und nach einer Einzelmetrik sortieren.
7. **Lauf nachvollziehen:** Strategieversion, vollständige Testkonfiguration, Report-Link und technische Metadaten speichern.

### Erst nach dem MVP

- PDF/OCR und Screenshot-OCR
- Abruf freier URLs
- zweiter KI-/Agent-Provider und Fallback
- Composite Score
- automatische Hal-Synchronisierung
- veränderbare Taxonomie
- Long-/Short-Detailanalyse, falls trader.dev sie nicht strukturiert liefert
- Multi-Upload, Regime-Analyse und Signal-Reverse-Engineering

Der Schnitt reduziert vier unabhängige Risikofelder im ersten Release: Dokumentverarbeitung, Multi-Provider-Orchestrierung, Vault-Synchronisierung und noch undefiniertes Ranking. Der eigentliche Produktnutzen bleibt testbar.

## Empfohlene Struktur des verbesserten Brainstorms

1. **Problem und Zielnutzer** – welcher heutige Ablauf ist langsam oder fehleranfällig?
2. **MVP-Erfolgskriterium** – z. B. „Aus einer verifizierbaren Textquelle entsteht ohne manuelle Datenübertragung ein reproduzierbarer Drei-Asset-Backtest.“
3. **Begriffe und fachliche Definitionen** – Strategie, Version, Run, Batch, Quelle, Instrument, Metrik.
4. **MVP-In-Scope / Out-of-Scope** – harte Grenze statt vermischter Phasen.
5. **Happy Path** – sieben Schritte der vertikalen Schleife.
6. **Daten- und Backtest-Vertrag** – Strategie-Schema sowie Ausführungsannahmen.
7. **Fehler- und Grenzfälle** – untestbare Regel, Teilfehler, keine Trades, ungültige Metrik, Credit-Mangel, privater Inhalt.
8. **Externe Annahmen** – trader.dev-Fähigkeiten mit Verifikationsstatus und Datum.
9. **Nichtfunktionale Anforderungen** – Reproduzierbarkeit, Secret-Schutz, lokale Single-User-Nutzung, Audit-Trail.
10. **Spätere Features** – ohne Umsetzungsvorgaben für v1.
11. **Offene Produktentscheidungen** – nur Entscheidungen, die Requirements wirklich blockieren.

## Entscheidungen vor `abc-requirements`

Diese sieben Punkte sollten vor dem Requirements-Lauf feststehen:

1. Exakte drei Instrumente inklusive Symbol, Venue und Produkttyp.
2. Ausführungsmodell inklusive Fees, Slippage, Positionsgröße und Leverage.
3. Research-/Holdout-Zeiträume und Regel gegen nachträgliches Tuning auf Holdout-Daten.
4. MVP-Richtungsmodi: nur kombiniert oder zusätzlich Long-only/Short-only.
5. Ein konkreter Agent-Runtime-/Modell-Pfad für v1.
6. Ergebnis eines trader.dev-Spikes: Tool-Schemas, unterstützte Assets/Zeiträume, strukturierte Resultate, Credit-Kosten und Privacy.
7. Ob Hal-Sync wirklich MVP ist; Empfehlung: zunächst nur lokaler Export einer Markdown-Datei.

## Vorgeschlagener Status des Ausgangsdokuments

`Review abgeschlossen – noch nicht bereit für abc-requirements; sieben Blocker offen.`
