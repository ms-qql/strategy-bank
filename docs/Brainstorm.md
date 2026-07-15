# Brainstorm: Strategy Bank Microapp

**Topic:** Jupiter-Microapp "Strategy Bank" — Trading-Strategien aus diversen Quellen (Bücher, Code, Screenshots, Links) per KI extrahieren, standardisiert backtesten (trader.dev MCP), filtern/priorisieren, Detail-Reports nach Hal Second Brain.
**Date:** 2026-07-15
**Status:** Divergenz abgeschlossen, bereit für `/abc-requirements`

---

## Session-Setup

- **Ziel der Session:** Grober Feature-Backlog + Schärfung der Idee (kein fertiges Requirements-Doc)
- **Approach:** Progressive Flow (breit divergieren über 10 Domains, dann konvergieren)
- **User-Profil:** Solo-Nutzer, alleiniger Trader/Entwickler, hat OpenCode- und Codex-Monatsabo
- **Constraints:**
  - Eigenständige Jupiter-Microapp (nicht Teil eines bestehenden Dashboards)
  - Single-User, kein Multi-Tenant nötig
  - Tech-Stack: **Next.js 16** (App Router) — nicht Flutter (Abweichung vom sonstigen Default)
  - Backend weiterhin FastAPI + raw SQL (Default-Stack)
  - trader.dev nur über MCP/Agent ansprechbar — **keine öffentliche REST-API gefunden** (recherchiert, bestätigt negativ)

## Initial Framing (Kern-Anforderungen aus der Ausgangsnachricht)

- Test-Assets: BTC, SPY, Gold — Timeframe 4h — Zeitraum 01.01.2021–31.12.2024 (alle in der App änderbar)
- Reine Entry/Exit-Signal-Strategie, **kein** Stop-Loss/Take-Profit/Exit-Optimierung in v1
- Default: Long **und** Short kombiniert testen (umschaltbar auf Long-only/Short-only)
- Beispielquelle: Kevin J. Davey Buch-Nugget (`/home/dev/tools/Hal/04 Resources/Buch_Nuggets/Kevin J. Davey-.../`)
- KI-Backend: OpenCode (eigener API-Key, Modellwahl) primär, Codex als Fallback

## Recherche-Ergebnis: trader.dev Pricing (per Screenshot korrigiert)

| Tier | Preis | Leistung |
|---|---|---|
| Free | $0/mo | 1.000 Credits (wöchentlicher Reset), Strategien **standardmäßig öffentlich** |
| Starter | $29.99/mo | 5× Free-Credits, mehr Backtests, alle MCP-Skills |
| Pro | $39.99/mo | 25× Free-Usage, Priority MCP, Early Access |

- 1 Credit = 1 Backtest. Long+Short kombiniert = **1 Backtest pro Strategie/Asset** → 3 Assets = 3 Credits/Strategie (nicht 9 — Long/Short-Split kommt aus dem Detail-Report, kein separater Run).
- **Risiko:** Free-Tier macht jede erstellte Strategie öffentlich sichtbar für die Community. "Make all PUBLIC"-Button nie nutzen.

---

## Divergenz — Ideen nach Domain

**[Extraction #1] Discretionary-Regel-Problem**
_Concept:_ Buch-Strategien sind oft vage/ermessensbasiert ("wenn Markt stark aussieht"), nicht direkt in klare Entry/Exit-Bedingungen übersetzbar.
_Novelty:_ Zentrales Extraktionsrisiko, das die "grobe Idee → handelbare Strategie"-Umwandlung (Kernanforderung) am meisten erschwert.

**[Extraction #2] Signal-Reverse-Engineering**
_Concept:_ Bei proprietären/Blackbox-Strategien (nur Entry/Exit-Zeitpunkte + Equity-Kurve bekannt, keine Regeln): App korreliert ein Indikator-Featureset (MA-Crossovers, RSI, Vol, Momentum, Candle-Pattern) an den Signal-Bars und schlägt per Rule-Mining/Decision-Tree Kandidaten-Regelsets vor, gerankt nach Fit.
_Novelty:_ Macht auch "nur Performance-Screenshot ohne Code"-Quellen nutzbar — deckt einen Quellentyp ab, den reine Text-Extraktion nicht lösen kann.

**[Rollout #1] Tier-Phasing**
_Concept:_ Start mit Free-Tier + nur öffentlichen/generischen Strategien zum App-Testen; Umstieg auf Starter (privat) sobald eigene/spezielle Strategien reinkommen.
_Novelty:_ Löst das Privacy-Risiko organisatorisch statt technisch — kein Code nötig, nur Reihenfolge im Rollout.

**[Ergebnis-Tabelle #1] Kern-Metriken + Calmar-Fokus**
_Concept:_ Pflicht-Kennzahlen: Net Profit, Trade-Count (Signifikanz-Schwelle: ≥6 Trades/Jahr), Max Drawdown, Sharpe, Profit Factor. Winrate nachrangig. Zusätzliche berechnete Kennzahl: **Calmar-Ratio** (Net Profit / Max Drawdown) — Ziel ist Gleichmäßigkeit/geringe Drawdowns vor absoluter Rendite.
_Novelty:_ Calmar wird von trader.dev nicht direkt geliefert, muss von der App aus den Rohdaten berechnet werden.

**[Ergebnis-Tabelle #2] Composite-Score-Formel**
_Concept:_ Default-Ranking-Score: 30% Calmar + 30% Sharpe + 30% Profit Factor + 10% Trade-Count-Bonus. Gewichte in der App konfigurierbar (Slider/Settings).
_Novelty:_ Ein einzelner, nutzerdefinierter Sortier-Score statt manuellem Abwägen mehrerer Spalten — Kern für "sehr schnell Überblick bekommen".

**[KI-Backend #1] Einheitliches Modell, global umschaltbar**
_Concept:_ Ein gewähltes Modell (OpenCode-Modellwahl oder Codex) gilt für Extraktion UND Backtest-Steuerung (Agent-Prompts an trader.dev MCP). Umschaltung ist ein globaler manueller Setting-Switch, kein Auto-Fallback pro Job.
_Novelty:_ Vereinfacht Konfiguration erheblich — ein Schalter statt Modell-Matrix pro Aufgabentyp.

**[Architektur #1] Hintergrund-Agent-Session als Backtest-Executor**
_Concept:_ trader.dev-MCP-Tools laufen nur in einer Agent-Session, nicht als klassische REST-API (recherchiert, bestätigt). Next.js-App triggert pro Batch-Lauf eine Hintergrund-Agent-Session (Claude Code/OpenCode/Codex mit MCP-Zugriff), die die Strategie-Queue abarbeitet, Kurzstatistiken zurückschreibt und Report-Links an Hal weiterreicht. App selbst hält nur Queue + Ergebnis-DB.
_Novelty:_ Zentrale technische Weichenstellung — bestimmt die gesamte Backend-Architektur (Queue-Worker statt Direct-API-Call).

**[Upload-UX #1] Multi-Format-Single-Source-Default + Freigabe-Gate**
_Concept:_ Input: 1 Quelle pro Upload-Vorgang (PDF/MD/Screenshot/Link), Multi-Upload als späteres Feature. App erkennt automatisch mehrere Strategien pro Dokument, extrahiert einzeln, speichert als "Entwurf". Human-in-the-Loop-Pflicht: User verifiziert/gibt jede Strategie einzeln frei, bevor sie in die Backtest-Queue wandert.
_Novelty:_ Kein Auto-Run nach Extraktion — verhindert Credit-Verschwendung durch Fehlextraktionen.

**[Long/Short #1] Ein Backtest pro Strategie/Asset**
_Concept:_ Nur Long+Short kombiniert laufen lassen (kein separater Long-only/Short-only-Run). Long/Short-Split-Performance wird aus dem trader.dev-Detail-Report abgelesen, nicht separat berechnet.
_Novelty:_ Korrigiert die ursprüngliche Credit-Kalkulation (3 statt 9 Credits/Strategie) und vereinfacht die Queue.

**[Kategorisierung #1] Feste kuratierte Taxonomie + KI-Tagging bei Extraktion**
_Concept:_ Vordefinierte Standardkategorie-Liste (Trend-Following, Mean-Reversion, Volatility-Breakout, etc.), vom User vor dem ersten Lauf verifiziert/erweiterbar. KI ordnet beim Extrahieren direkt zu. Fallback bei unklarer Extraktion: Kategorie aus Backtest-Ergebnis-Verteilung ableiten.
_Novelty:_ Kuratierte Liste statt frei wachsendem Tag-Wildwuchs — bleibt filterbar/auswertbar.

**[Hal-Integration #1] Ein Note pro Strategie, mitwachsend**
_Concept:_ Note wird bei Erstverifizierung angelegt, bei jedem Re-Test/Parameter-Update ergänzt (Historie in einem Dokument statt verstreut). Inhalt: Link zum trader.dev-Detail-Report + KI-generierte Kurzzusammenfassung (Strategie-Logik, Kategorie, Kernergebnis), durchsuchbar im Vault, ähnlich Book-Nugget-Format.
_Novelty:_ Ein Note pro Strategie statt pro Lauf hält den Vault übersichtlich und macht Entwicklung über Zeit nachvollziehbar.

**[Regime-Analyse #1] ADX+ATR-basierte, asset-relative Zweifach-Klassifikation**
_Concept:_ Einheitliche Regime-Definition, einmal pro Asset berechnet, von allen Strategien wiederverwendet:
- **Trend (3 Klassen)** via ADX(14) + Directional Index auf Tagesbasis, auf 4h-Bars gemappt: Bull (ADX>20, +DI>-DI), Bear (ADX>20, -DI>+DI), Sideways (ADX≤20).
- **Volatilität (2 Klassen)** via ATR(14)/Close, klassifiziert relativ zum eigenen historischen Median des jeweiligen Assets (nicht absoluter Schwellwert — sonst wäre BTC immer "hoch", Gold immer "niedrig").
- Ergebnis: fixe Lookup-Tabelle (Datum → Regime-Label) pro Asset; Strategie-Performance wird nachträglich pro der 6 Regime-Kombinationen aggregiert.
_Novelty:_ Standard-Indikatoren (Wilder ADX/ATR), kein ML nötig, robust und einheitlich über alle Strategien — erfüllt explizit die Anforderung "gleiche Regimeeinschätzung für alle Strategien".

---

## Convergence — Themen-Cluster

### Kernschleife (Pipeline)
Upload-UX #1 → Extraction #1/#2 → Kategorisierung #1 → Freigabe-Gate → Architektur #1 (Agent-Session) → Ergebnis-Tabelle #1/#2 → Hal-Integration #1

### Konfiguration/Settings
KI-Backend #1, Rollout #1 (Tier-Phasing), Assets/Timeframe/Zeitraum (aus Initial Framing, alle änderbar), Composite-Score-Gewichte, Long/Short-Modus

### Later-Feature (explizit vom User terminiert)
Regime-Analyse #1

### Risiko/Constraint (kein Feature, aber Backlog-relevant)
trader.dev Free-Tier Public-Strategy-Risiko

---

## Vorgeschlagener Feature-Backlog (für `/abc-requirements`)

### Phase 1 — MVP
1. **Upload & Extraktion** — Single-Source-Upload (PDF/MD/Screenshot/Link), KI-Multi-Strategie-Erkennung pro Dokument, Umwandlung grober Ideen in handelbare Entry/Exit-Regeln (inkl. Discretionary-Regel-Behandlung), Speicherung als Entwurf
2. **Verifizierungs-UI** — Entwurfsliste, manuelle Freigabe pro Strategie vor Backtest-Queue, Kategorie-Korrektur möglich
3. **Kategorisierung** — Kuratierte Standard-Taxonomie (User-verifizierbar/erweiterbar), KI-Tagging bei Extraktion
4. **Backtest-Ausführung** — Hintergrund-Agent-Session-Executor gegen trader.dev MCP, Long+Short kombiniert, Assets/Timeframe/Zeitraum konfigurierbar (Default: BTC/SPY/Gold, 4h, 2021-2024)
5. **Ergebnis-Tabelle** — Net Profit, Trade Count, Max DD, Sharpe, Profit Factor, berechnete Calmar-Ratio, konfigurierbarer Composite-Score, Filter/Sortierung, Mindest-Trade-Schwelle
6. **Hal-Integration** — Ein Note pro Strategie (Link zum Detail-Report + KI-Summary), Rücklink in Ergebnis-Tabelle
7. **Settings** — KI-Modellwahl (OpenCode/Codex, global), trader.dev-Tier-Hinweis (Free-Tier-Start, Privacy-Warnung vor "Make all PUBLIC")

### Phase 2 — Später
8. **Regime-Analyse** — ADX+ATR-Klassifikation pro Asset, Performance-Breakdown pro Strategie über 6 Regime-Kombinationen
9. **Signal-Reverse-Engineering** — Rule-Mining für Blackbox-Strategien ohne Code/Text
10. **Multi-Upload** — mehrere Quellen gleichzeitig hochladen
11. **Starter/Pro-Tier-Umstieg** — sobald private/eigene Strategien getestet werden

---

## Offene Entscheidungspunkte (vor Requirements zu klären)

- Konkrete Liste der Standardkategorien (Trend-Following, Mean-Reversion, Volatility-Breakout, ... vollständige Liste)
- Technische Orchestrierung der Hintergrund-Agent-Session (Cron/Queue-Worker? Welcher Prozess startet z.B. headless Claude-Code-CLI oder Codex-CLI?)
- Speicherort/Schema für die Regime-Lookup-Tabelle (Phase 2)
- Genauer wöchentlicher Free-Credit-Betrag bei trader.dev (Login nötig zur Prüfung)
- Hal-Note-Template-Struktur (analog Book-Nugget-Format?)
- OpenCode-API-Key-Handling / Secrets-Storage in der App

## Empfohlene nächste Schritte

1. `/abc-requirements` mit diesem Backlog als Grundlage — Feature-Specs `PROJ-1` ff. für Phase-1-Punkte
2. Offene Entscheidungspunkte vor/während Requirements klären (insbesondere Standardkategorien-Liste und Agent-Session-Orchestrierung, da architekturrelevant)
