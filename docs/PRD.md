# PRD: Strategy Bank

**Status:** MVP-Spezifikation abgeschlossen
**Erstellt:** 2026-07-15
**Basis:** `docs/Brainstorm-strategy-bank-v2.md`, `docs/Brainstorm-strategy-bank-review.md`, `docs/trader-dev-capability-spike.md`

## 1. Vision

Strategy Bank ist eine eigenständige Microapp für einen einzelnen Trader. Sie überführt Strategiebeschreibungen aus Text-/Markdown-Quellen in überprüfbare, deterministische Entry-/Exit-Regeln, führt standardisierte Backtests über die trader.dev-MCP-Schnittstelle aus und macht die Ergebnisse reproduzierbar vergleichbar. Kein automatisches Erfinden „guter" Strategien — Kernnutzen ist der verkürzte, fehlerarme Weg von Quelle zu nachvollziehbarem Vergleich.

## 2. Zielnutzer

- Solo-Nutzer, zugleich Trader und Entwickler.
- Lokale/private Nutzung, kein Multi-Tenant-Betrieb, keine mandant_id/RLS.
- Vorhandene Werkzeuge: Hal Second Brain, OpenCode, trader.dev MCP (bereits authentifiziert, Free-Tier).

## 3. Tech-Stack (projektspezifisch, abweichend vom globalen Default)

- Frontend: Next.js 16 (App Router), Tailwind + shadcn/ui.
- Backend: FastAPI, raw SQL, PostgreSQL.
- Auth: einfache lokale Single-User-Authentisierung. **Kein** JWT-Mandant-Modell, kein RLS — bewusste Abweichung vom globalen Multi-Tenant-Default, da Solo-Nutzung.
- Externe Integration: trader.dev MCP (Pine Script v5 Backtests), OpenCode als einziger konfigurierter Agent-Runtime-Pfad im MVP.

## 4. Bestätigte externe Capability

Verbindliche Quelle für alle trader.dev-Capabilities und MVP-Annahmen ist `docs/trader-dev-capability-spike.md`.

- Backtest-Ausführung läuft ausschließlich über volle Pine-Script-v5-Quellen (`quick_backtest`/`run_backtest`), kein deklaratives Regel-JSON. Die App muss kanonische Entry-/Exit-Regeln in Pine Script übersetzen.
- Standard-Testuniversum (verbindlich, kein weiterer Spike nötig):
  | Fachliches Instrument | Provider-Symbol | Markt |
  |---|---|---|
  | Bitcoin | `BTCUSDT` (`BYBIT:BTCUSDT.P`) | Bybit USDT-linear Perpetual |
  | S&P 500 | `SPYUSDT` (`BYBIT:SPYUSDT.P`) | Bybit USDT-linear Perpetual — **synthetischer/tokenisierter Proxy, kein echtes ETF**, 24/7-Handel, keine Corporate Actions |
  | Gold | `XAUUSD` | Polygon Forex |
- Credits: exakt 1 Credit pro Backtest (`quick_backtest`/`run_backtest`). Free-Tier: 1000 Credits/Woche.
- Kein Privacy-Parameter in der API. Jede benannte oder aus dem Pine-`strategy()`-Titel abgeleitete Strategie wird öffentlich auf `/browse` gespeichert (`visibility: "public"`), unabhängig vom Tier. **Produktentscheidung:** kein Privacy-Gate im MVP — Nutzer bestätigt eigenverantwortlich, nur öffentliche/nicht-proprietäre Strategien einzureichen.
- Die API meldet naive Regel-zu-Pine-Übersetzungen mit „cascade exit pattern" (severity error), wenn Exit-Logik nicht edge-getriggert ist. Muss von der App erkannt und mit korrigierter Übersetzung wiederholt werden.

## 5. Kernproblem

Trading-Strategien liegen in uneinheitlichen Quellen vor, sind oft unvollständig oder diskretionär. Manuelles Übertragen erzeugt Interpretationsfehler, uneinheitliche Backtest-Annahmen und fehlende Rückführbarkeit von Kennzahl auf Regelversion.

## 6. MVP-Erfolgskriterium

Aus einer Text-/Markdown-Quelle mindestens eine Strategie extrahieren, verifizieren und ohne manuelle Übertragung auf den drei Standardinstrumenten testen — mit für jedes Ergebnis eindeutig sichtbarer Regelversion, Testannahmen, Status, Kernmetriken und trader.dev-Report-Link.

## 7. Core Features (Roadmap)

| ID | Feature | Priorität |
|---|---|---|
| PROJ-1 | Quellenerfassung (Text/Markdown) | P0 |
| PROJ-2 | KI-Extraktion in kanonisches Zwischenformat | P0 |
| PROJ-3 | Verifizierung und Versionierung | P0 |
| PROJ-4 | Batch-Konfiguration | P0 |
| PROJ-5 | Credit-Gate | P0 |
| PROJ-6 | Queue und trader.dev-Ausführung (Pine-Übersetzung) | P0 |
| PROJ-7 | Ergebnisvergleich | P0 |
| PROJ-8 | Audit-Trail | P0 |
| PROJ-9 | Markdown-Export | P1 |

Empfohlene Build-Reihenfolge: PROJ-1 → PROJ-2 → PROJ-3 → PROJ-4 → PROJ-5 → PROJ-8 → PROJ-6 → PROJ-7. PROJ-9 folgt als P1.

## 8. Erfolgsmetriken

- Mindestens eine Strategie durchläuft Quelle → Extraktion → Freigabe → 3-Instrumente-Batch → Ergebnisvergleich ohne manuelle Datenübertragung.
- Jedes Ergebnis ist auf Strategieversion, Backtest-Profil und trader.dev-Report zurückführbar (Audit-Trail vollständig, stichprobenartig geprüft).
- Keine cascade-exit-fehlerhaften Ergebnisse werden ungefiltert als gültig angezeigt.

## 9. Constraints

- Solo-Entwicklung, kein festes Zieldatum.
- trader.dev Free-Tier: 1000 Credits/Woche, keine Privacy-Option — Nutzer verantwortet Auswahl öffentlich zulässiger Strategien selbst.
- Nur ein konfigurierter Agent-Runtime-Pfad (OpenCode) im MVP, kein automatischer Provider-Fallback.

## 10. Non-Goals (MVP)

- PDF/OCR/Screenshot-Quellen, Web-Links, Multi-Upload.
- Stop-Loss/Take-Profit/Trailing-Stops, Portfolio-Optimierung, Parameter-Sweeps.
- Composite Score, automatische Gewinner-Empfehlung.
- Automatischer Provider-/Modell-Fallback, zweiter Agent-Provider.
- Automatische Hal-Synchronisierung (nur lokaler Markdown-Export im MVP).
- Privacy-Gate / private Strategien (bewusst verworfen, siehe Abschnitt 4).
- Multi-Tenant-Betrieb.

## 11. Begriffe

Siehe `docs/Brainstorm-strategy-bank-v2.md` Abschnitt 5 (Quelle, Strategie, Strategieversion, Entwurf, Run, Batch, Backtest-Profil, Nicht testbar) — unverändert übernommen.
