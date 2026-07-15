# PROJ-2: KI-Extraktion

## Status: In Progress (Backend done, Frontend offen)
**Created:** 2026-07-15
**Last Updated:** 2026-07-15

## Dependencies
- Requires: PROJ-1 (Quellenerfassung) — liefert die zu verarbeitende Quelle inkl. Quell-Hash.

## User Stories
- Als Trader möchte ich, dass die KI alle in einer Quelle beschriebenen Strategien erkennt, um nichts manuell durchsuchen zu müssen.
- Als Trader möchte ich zu jeder extrahierten Regel den Textausschnitt sehen, aus dem sie stammt, um die KI-Auslegung prüfen zu können.
- Als Trader möchte ich, dass unklare oder diskretionäre Aussagen explizit als offene Unklarheit markiert werden, statt dass die KI sie stillschweigend konkretisiert.

## Acceptance Criteria
- [ ] Die Extraktion läuft über genau einen konfigurierten Agent-Runtime-/Modell-Pfad (OpenCode). Kein automatischer Fallback auf einen zweiten Provider.
- [ ] Erkennt die KI mehrere Strategien in einer Quelle, entsteht je Strategie ein eigener Entwurf mit eigenen Quellenbelegen.
- [ ] Jeder Entwurf enthält mindestens: Strategie-ID, Versionsnummer, Name, kurze These, Kategorie (aus der festen Liste, siehe Edge Cases), Richtung, Parameter (Name/Wert/Einheit/erlaubter Bereich), Entry-Regel als boolesche Bedingung, Exit-Regel als boolesche Bedingung, Warm-up-Anforderung, Verhalten bei gleichzeitigem Entry/Exit, Reversal-Verhalten, Quellenbeleg je Regel (Textausschnitt/Zeilenreferenz), Quell-Hash, offene Unklarheiten, Extraktionsmodell, Prompt-Version, Zeitstempel, Status.
- [ ] Fehlende Werte, die die KI vorschlägt, sind eindeutig als Vorschlag markiert (nicht als bestätigte Regel).
- [ ] Diskretionäre oder nicht deterministisch formulierbare Aussagen werden als offene Unklarheit mit Begründung erfasst, nicht stillschweigend konkretisiert.
- [ ] Enthält die Quelle keine erkennbare Strategie, erscheint ein verständlicher Hinweis und es werden keine Entwürfe erzeugt.
- [ ] Jeder Entwurf startet im Status „Entwurf".
- [ ] Ein Modellwechsel (Konfigurationsänderung) erzeugt bei künftigen Extraktionen neue Extraktionsmetadaten; bereits freigegebene Strategieversionen (PROJ-3) bleiben unverändert.

## Edge Cases
- Quelle enthält keine Strategie: Hinweis „Keine Strategie in dieser Quelle erkannt.", keine Entwürfe, Quelle bleibt im Status „extrahiert, keine Treffer".
- Quelle enthält mehrere, teils überlappende Strategien: getrennte Entwürfe, auch wenn sie sich Parameter oder Textstellen teilen.
- KI-Ausgabe ist syntaktisch unvollständig (z. B. Entry-Regel fehlt ganz): Entwurf wird erzeugt, aber bleibt gesperrt (kein Freigabe-Gate möglich, siehe PROJ-3) mit Hinweis auf den fehlenden Teil.
- Regel bleibt trotz KI-Vorschlag diskretionär (z. B. „bei starkem Momentum einsteigen" ohne quantifizierbare Schwelle): Status „nicht testbar" mit Begründung, kein erfundener Schwellenwert.
- Feste Kategorienliste (Trendfolge, Mean Reversion, Breakout, Volatilität, Momentum, Saison/Zeit, Preis-/Candlestick-Muster, Hybrid, Sonstige) — passt keine Kategorie eindeutig, schlägt die KI „Sonstige" vor; der Nutzer kann korrigieren, die Liste selbst ist im MVP nicht erweiterbar.
- Extraktionslauf bricht durch Provider-Fehler/Timeout ab: Quelle bleibt im Status „Extraktion fehlgeschlagen", manueller Retry durch Nutzer nötig, kein stiller Wiederholungsversuch.

## Technical Requirements (optional)
- Kanonisches Zwischenformat wird als strukturierte, versionierbare Datenstruktur persistiert (Basis für PROJ-3 Versionierung).
- Jeder Entwurf referenziert die Quelle über den Quell-Hash aus PROJ-1.
- Security: API-Keys/Secrets des Agent-Runtime-Pfads nie im Frontend, in Prompts oder Logs.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-15 · **Stack:** Next.js 16 (App Router) + shadcn/ui / FastAPI + raw SQL / PostgreSQL · **Branch:** main (kein Git-Repo initialisiert)

### A) Komponentenstruktur (UI, Next.js — erweitert PROJ-1)
```
QuellenPage (app/quellen/page.tsx)
├── QuellenListe (aus PROJ-1)
│   └── QuelleZeile
│       ├── ExtrahierenButton         # sichtbar bei „noch nicht extrahiert" / Retry bei „fehlgeschlagen"
│       └── ExtraktionStatusBadge     # läuft · abgeschlossen · keine Treffer · fehlgeschlagen
└── EntwuerfeSection (bei Klick auf eine extrahierte Quelle)
    ├── KeineTrefferHinweis           # „Keine Strategie in dieser Quelle erkannt."
    └── EntwurfCard (je erkannter Strategie)
        ├── EntwurfKopf               # Name, These, Kategorie-Badge, Richtung, Status-Badge
        ├── RegelBlock (Entry/Exit)
        │   └── QuellenbelegPopover   # Textausschnitt/Zeilenreferenz je Regel
        ├── ParameterTabelle          # Name/Wert/Einheit/Bereich, „Vorschlag"-Badge
        └── OffeneUnklarheitenListe   # Begründung je Unklarheit, blockiert Freigabe (PROJ-3)
```
Kein Editieren hier — Entwürfe sind read-only Anzeige. Bearbeiten/Freigeben ist PROJ-3.

### B) Datenmodell (Klartext)
```
Extraktionslauf (extraction_runs) — einer pro Klick auf „Extrahieren":
- ID, Quelle-ID (FK sources)
- Status: „läuft" | „abgeschlossen" | „keine Treffer" | „fehlgeschlagen"
- Extraktionsmodell (konfigurierter OpenCode-Modellpfad)
- Prompt-Version (Bezeichner des verwendeten Prompt-Templates)
- Gestartet-/Beendet-Zeitpunkt, Fehlermeldung (nur bei „fehlgeschlagen")

Entwurf (strategy_drafts) — einer je erkannter Strategie:
- ID, Extraktionslauf-ID (FK), Quell-Hash (aus PROJ-1, direkt referenziert)
- Name, kurze These, Kategorie (feste Liste), Richtung
- Entry-Regel, Exit-Regel (je als Text/boolesche Bedingung)
- Warm-up-Anforderung, Verhalten bei gleichzeitigem Entry/Exit, Reversal-Verhalten
- Status: „Entwurf" | „nicht testbar" | „gesperrt (unvollständig)" + Begründung
- Zeitstempel

Parameter (draft_parameters, 1:n je Entwurf):
- Name, vorgeschlagener Wert, Einheit, erlaubter Bereich, ist_vorschlag=true (immer, bis PROJ-3 bestätigt)

Quellenbeleg (draft_source_citations, 1:n je Entwurf):
- Regel-Feld (z. B. „entry_rule"), Textausschnitt, Zeilenreferenz im Rohinhalt

Offene Unklarheit (draft_open_questions, 1:n je Entwurf):
- Beschreibung, Begründung (warum nicht quantifizierbar)

Speicherort: PostgreSQL, normalisiert in vier Tabellen (kein JSON-Blob) — damit PROJ-3
einzelne Felder gezielt bearbeiten/versionieren kann, ohne ein Gesamtdokument neu zu parsen.
```

### C) API-Form (nur Endpunkte)
```
- POST /sources/{id}/extractions   → startet einen Extraktionslauf (asynchron), liefert sofort Lauf-ID + Status „läuft"
- GET  /sources/{id}/extractions   → alle Läufe dieser Quelle, neueste zuerst (Status, Modell, Prompt-Version, Zeitstempel)
- GET  /extractions/{id}           → Status/Fehlermeldung + erzeugte Entwürfe (Frontend pollt hierauf)
- GET  /drafts/{id}                → vollständiger Entwurf inkl. Parameter, Quellenbelege je Regel, offene Unklarheiten
- GET  /categories                 → feste Kategorienliste (zentral im Backend gepflegt)
```
Kein PATCH/Freigabe-Endpunkt hier — Bearbeiten und Freigabe-Gate gehören zu PROJ-3.

### D) Tech-Entscheidungen (warum)
- **OpenCode headless per Server-Prozessaufruf, nicht REST:** trader.dev-MCP-Tools laufen nur innerhalb einer Agent-Session (bestätigt in `docs/Brainstorm.md`), nicht als klassische API. Für die reine Text-Extraktion ist aber gar kein MCP-Zugriff nötig — nur ein Prompt-Completion-Aufruf an das konfigurierte Modell. Das Backend startet dafür pro Lauf einen headless OpenCode-Prozess (Prompt-Template + Rohinhalt der Quelle als Input) und parst dessen strukturierte JSON-Ausgabe in die vier Tabellen aus Abschnitt B.
- **Asynchron statt blockierender Request:** eine LLM-Extraktion kann Sekunden bis Minuten dauern. Der POST-Endpunkt liefert sofort eine Lauf-ID zurück; das Frontend pollt den Status. Damit keine HTTP-Timeouts und der Lauf bleibt nach einem Prozessneustart anhand des persistierten Status fortsetzbar (NFR aus dem Brainstorm-Dokument).
- **Normalisierte Kindtabellen statt ein großes JSON-Dokument:** macht Filterung/Anzeige einfach und ist die Grundlage, auf der PROJ-3 einzelne Felder gezielt editieren und versionieren kann.
- **Prompt-Version + Modell pro Lauf, nicht global am Entwurf verankert:** ein Modell-/Prompt-Wechsel wirkt nur auf künftige Läufe; bereits erzeugte oder freigegebene Strategieversionen (PROJ-3) bleiben unverändert — genau wie in der Akzeptanzkriterien-Liste gefordert.
- **Kategorienliste zentral im Backend (ein Enum, per `GET /categories` exponiert), nicht im Frontend hartkodiert:** verhindert Drift zwischen Client-Anzeige und Server-Validierung. Liste bleibt im MVP fest, nicht erweiterbar.
- **Kein Auto-Retry bei Provider-Fehler/Timeout:** „Extraktion fehlgeschlagen" ist ein Endzustand; ein erneuter Lauf ist eine bewusste Nutzeraktion (`POST /sources/{id}/extractions` erneut aufrufen) — kein stiller Hintergrund-Retry.
- **Gesperrte Entwürfe werden gespeichert, nicht verworfen:** ein syntaktisch unvollständiger Entwurf (z. B. fehlende Exit-Regel) bekommt Status „gesperrt (unvollständig)" mit Begründung — bleibt sichtbar, kann aber das Freigabe-Gate (PROJ-3) nicht passieren.
- **Abgrenzung zum Capability-Spike:** Spike-Punkt 2 („Ob OpenCode den MCP-Server zuverlässig headless ansprechen kann") betrifft die trader.dev-Anbindung für Backtests (PROJ-6), nicht die reine Text-Extraktion hier — blockiert dieses Design also nicht. Offen bleibt als Umsetzungs-Voraussetzung für `/abc-backend`: OpenCode-CLI muss auf dem Zielhost installiert und authentifiziert sein.

### E) Abhängigkeiten
- Backend (Python): FastAPI, `BackgroundTasks` (FastAPI-eigen, für den asynchronen Lauf), stdlib `subprocess` für den OpenCode-Prozessaufruf, Pydantic v2 zum Parsen/Validieren der KI-Ausgabe. Kein neues Drittanbieter-Package für den Kern.
- Frontend (Next.js): `shadcn/ui` (Card, Badge, Table, Popover, Alert), bestehende `api-client.ts` erweitert um Extraction-/Draft-Endpunkte.
- Security: OpenCode-API-Key ausschließlich als Server-Umgebungsvariable; nie im Frontend, im Prompt-Log oder in Fehlermeldungen sichtbar.

## Backend-Implementierung (abc-backend, 2026-07-15)

FastAPI-Backend in `backend/`, untracked im Working Tree (committed in `master` per Spec-Default, Spec-Branch-Feld sagt `main` — Inkonsistenz aus PROJ-1 übernommen, kein Branch-Switch nötig).

**Neue/geänderte Dateien:**
- `backend/sql/002_extraction.sql` — 5 Tabellen: `extraction_runs`, `strategy_drafts`, `draft_parameters`, `draft_source_citations`, `draft_open_questions` (jeweils FK-CASCADE, Indizes auf FK-Spalten, CHECK-Constraints für Status-Enums).
- `backend/app/constants.py` — `CATEGORIES` (feste Liste), `FALLBACK_CATEGORY="Sonstige"`, `DIRECTIONS`.
- `backend/app/config.py` — `opencode_binary`, `extraction_model`, `extraction_prompt_version`, `extraction_timeout_seconds` (300s, pydantic-settings).
- `backend/app/schemas/extractions.py` — `ExtractionRunListItem`, `ExtractionRunDetail` (extends mit `drafts`), `DraftRead` (mit `parameters`/`citations`/`open_questions`), `ParameterRead`, `CitationRead`, `OpenQuestionRead`, `CategoryList`.
- `backend/app/services/opencode_extraction.py` — `build_prompt` (de-DE Anweisungstext, erzwingt `{"strategies": []}` wenn nichts erkennbar), `run_opencode` (subprocess-Aufruf mit Timeout, parst OpenCode-Stream-Events, wirft `RuntimeError` bei Fehler/kein Text), `parse_model_output` (Codefence-Extraktion + Fallback auf größtes `{...}`-Fragment), `_normalize_strategy` (server-seitig: unbekannte Kategorie → `Sonstige`, fehlende entry/exit-rule → `gesperrt (unvollständig)`, `is_proposal=true` immer), `execute_extraction` (Background-Task: bei Parser-/Provider-Fehler Endstatus `fehlgeschlagen` ohne Retry).
- `backend/app/routes/extractions.py` — `POST /sources/{id}/extractions` (201, Background-Task, setzt source auf `wird extrahiert`), `GET /sources/{id}/extractions`, `GET /extractions/{id}` (inkl. drafts), `GET /drafts/{id}`, `GET /categories`.
- `backend/app/main.py` — Router-Registrierung, Exception-Handler für `InvalidTextRepresentation`→404, `ForeignKeyViolation`→422 (aus PROJ-1 übernommen, deckt auch UUID-Pfade in PROJ-2 ab).
- `backend/tests/test_extractions.py` + `test_opencode_extraction.py` — 11 Tests: Happy-Path, fehlende Source, leere Läufe, Kategorie-Fallback, Gesperrt-Erkennung, Parameter-als-Vorschlag, keine-Treffer, Provider-Fehler.

**Verifiziert:** 27/27 pytest grün (PROJ-1 + PROJ-2). Server bootet clean (`/health`, `/categories` korrekt). DB-Migrationen angewendet (6 Tabellen in `public`).

**Offen (Frontend):** `ExtrahierenButton`, `ExtraktionStatusBadge`, `EntwuerfeSection` mit `EntwurfCard`/`RegelBlock`/`QuellenbelegPopover`/`ParameterTabelle`/`OffeneUnklarheitenListe` in `nextjs_app/components/quellen/` — gehört zu nächstem Schritt `/abc-frontend`.

**Security:** OpenCode-Authentifizierung erfolgt über dessen globales Credential-Management (`~/.config/opencode`); die App übergibt nie einen API-Key und loggt nie den Prompt-Inhalt. Timeout verhindert hängende Background-Tasks. Kein Auto-Retry bei Provider-Fehler.

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
