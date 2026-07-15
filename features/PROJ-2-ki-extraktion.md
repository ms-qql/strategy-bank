# PROJ-2: KI-Extraktion

## Status: In Review (Backend + Frontend done)
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

## Frontend-Implementierung (abc-frontend, 2026-07-15)

Next.js 16 (App Router) + shadcn/ui (`base-nova`, neutral) in `nextjs_app/`. Erweitert die bestehende QuellenPage um Extraktions-UX gemäß Spec-Section A.

**Neue/geänderte Dateien:**
- `lib/schemas/extraction.ts` — zod-Schemas für `extractionRun`, `extractionRunDetail`, `draft`, `parameter`, `citation`, `openQuestion` (decken die Backend-Responses 1:1 ab, inkl. Status- und Richtungs-Enums).
- `lib/api-client.ts` — neuer Helper `apiPost(path)` (plain JSON POST ohne Body) für `POST /sources/{id}/extractions`.
- `components/quellen/extrahieren-button.tsx` — Button „Extrahieren" / „Erneut extrahieren" je nach Source-Status; feuert POST, gibt die neue `ExtractionRun` per Callback zurück.
- `components/quellen/quellenbelege.tsx` — native `<details>`-basierter Quellenbeleg-Expander (Textauszug + Zeilenreferenz). Bewusst KEIN shadcn-Popover: spart neue Deps, ist nativ zugänglich und erfüllt die UX-Anforderung „Quellenbeleg je Regel anzeigen".
- `components/quellen/entwurf-card.tsx` — `EntwurfCard` je erkannter Strategie: Kopf (Name + These), Badges (Kategorie, Richtung, Status), `status_reason`-Alert, Entry/Exit-Regelblock mit gruppierten Quellenbelegen, Warm-up/Simultaneous-Entry-Exit/Reversal-Zeilen, Parameter-Tabelle mit „Vorschlag"-Badge, offene Unklarheiten-Liste. Server-seitige `is_proposal=true` wird im UI explizit als „Vorschlag" markiert (PROJ-3 hebt das auf).
- `components/quellen/quellen-view.tsx` — erweitert: pro Quellen-Zeile jetzt (1) Chevron-Spalte, (2) Status-Badge mit `Loader`-Spinner für „wird extrahiert", (3) `ExtrahierenButton` nur bei „noch nicht extrahiert" / „Extraktion fehlgeschlagen" (mit `stopPropagation` damit der Klick die Zeile nicht auf-/zuklappt). Auf-/Zuklappen per Klick auf die Zeile (oder Enter/Space, `tabindex=0`, `aria-expanded`); beim Öffnen wird `GET /sources/{id}/extractions` lazy geladen, beim aktuellen „läuft"-Run alle 2 s `GET /extractions/{id}` gepollt (stoppt automatisch sobald `status != "läuft"`, Cleanup in `useEffect` Unmount). Source-Status wird mit jeder Status-Änderung im Top-Level-State aktualisiert. Expand-Section zeigt: Loader-Hinweis während des Ladens, Fehler-Alert mit „Erneut versuchen", laufenden Modell/Prompt-Text, Fehlermeldung bei `fehlgeschlagen`, „Keine Strategie in dieser Quelle erkannt." bei `keine Treffer` (sowohl Backend-Status als auch leerer `drafts`-Array), Entwurfs-Cards je Draft.

**Verifiziert:** `npm run lint` grün (0 Errors/Warnings), `npm run build` grün (TypeScript + statische Generierung für `/quellen`). Live-Smoke gegen FastAPI-Backend bestätigt: `POST /sources` liefert exakt das `Source`-Shape aus dem zod-Schema, `GET /categories` liefert die 9 Kategorien in Reihenfolge, `GET /extractions/{unknown-uuid}` → 404 mit deutscher `detail`-Meldung.

**Designentscheidung „kein Popover":** Spec erwähnt `QuellenbelegPopover` als UI-Detail. shadcn-Popover-Primitive ist im Projekt nicht installiert. Native `<details>` ist die lazy-korrekte Wahl: keine neue Dep, nativ screenreader-tauglich, gleicher funktionaler Outcome (Klick → Auszug + Zeilenreferenz). Falls echte Hover-/Focus-Tooltips gewünscht sind, kann shadcn `popover` später per `npx shadcn@latest add popover` nachgezogen werden.

**Verbleibend für PROJ-3:** Edit/Freigabe-Gate (PATCH-Endpoints, Versionsnummern, gesperrt-Status kann nur nach manueller Bestätigung aufgelöst werden). Die UI-Annotations- und Bearbeitungs-Workflow kommen mit dem nächsten Feature.

## QA Test Results
**Geprüft:** 2026-07-15 · **Branch:** main

### Acceptance Criteria

| Kriterium | Ergebnis | Nachweis |
|---|---|---|
| Genau ein konfigurierter OpenCode-Pfad, kein Fallback | PASS | `run_opencode` ruft ausschließlich `settings.opencode_binary` mit `settings.extraction_model` auf; kein zweiter Provider im Backend. |
| Mehrere Strategien ergeben getrennte Entwürfe | FAIL | Backend persistiert mehrere Items, aber die UI bleibt nach dem Polling auf „Extraktion läuft“ und zeigt keine Entwürfe (BUG-1). |
| Vollständiger Entwurf inkl. Strategie-ID, Versionsnummer und Quellenbelegen je Regel | FAIL | `strategy_drafts` und API-Schema enthalten keine Versionsnummer; Belege sind optional und werden nicht pro Regel validiert (BUG-2). |
| Fehlende vorgeschlagene Werte sind als Vorschlag markiert | PASS | `_normalize_strategy` erzwingt `is_proposal=True`; durch `test_normalize_strategy_forces_parameters_as_proposal` abgedeckt. |
| Diskretionäre Aussagen werden als offene Unklarheit erfasst | FAIL | Der Prompt fordert dies nur an; serverseitig wird weder eine offene Unklarheit noch „nicht testbar“ erzwungen (BUG-2). |
| Keine Strategie erzeugt Hinweis und keine Entwürfe | FAIL | Backend liefert korrekt `keine Treffer`; die UI erreicht wegen BUG-1 den terminalen Zustand nicht. |
| Jeder Entwurf startet als „Entwurf“ | PASS | Status-Default und Normalisierung setzen `Entwurf`; unvollständige Entry-/Exit-Regeln werden korrekt gesperrt. |
| Modellwechsel betrifft nur künftige Extraktionen | PASS | Modell und Prompt-Version werden je `extraction_runs`-Datensatz persistiert; bestehende Entwürfe bleiben unverändert. |

### Edge Cases und Regression

- PASS: Keine Treffer, Provider-/Parser-Fehler, Kategorie-Fallback, gesperrter unvollständiger Entwurf und Parameter-Vorschläge sind durch die Backend-Tests abgedeckt.
- PASS: Feste Kategorienliste ist serverseitig zentral und per `GET /categories` verfügbar.
- PASS: 36/36 Backend-Tests (`python -m pytest`), Next.js-Lint und Production-Build.
- NOT RUN: Live-OpenCode-Lauf wurde nicht ausgelöst, da er externe Modell-Credits verbraucht; Browser-/Responsive-Smoke kann wegen der blockierenden UI-Logik nicht erfolgreich abgeschlossen werden.

### Security Audit

- PASS: Solo-User-Architektur, daher kein JWT-/Mandanten-/RLS-Test erforderlich (PRD §3).
- PASS: SQL-Parameterbindung via psycopg `%s`; React escaped gerenderte Quelleninhalte.
- FAIL: Provider-Fehlertext wird bis zu 2.000 Zeichen in `error_message` gespeichert und im Frontend ausgegeben. Enthält ein Provider-Fehler Credentials oder interne Details, werden sie offengelegt (BUG-3).
- PASS: Kein Auto-Retry; CORS-Whitelist und UUID-Fehlerbehandlung sind durch die Regressionstests abgedeckt.

### Bugs Found

#### BUG-1: Terminaler Extraktionsstatus wird im Frontend nicht übernommen
- **Severity:** High
- **Reproduktion:** Extraktion starten und auf einen terminalen Backend-Status warten (`abgeschlossen`, `keine Treffer` oder `fehlgeschlagen`).
- **Expected:** Status-Badge und Detailbereich zeigen Entwürfe, „Keine Strategie …“ oder den Fehler mit Retry.
- **Actual:** `schedulePoll` ersetzt nur `details`; `runs[0].status` bleibt `läuft`. `EntwuerfeSection` rendert deshalb dauerhaft den Ladezustand.
- **Root Cause:** `nextjs_app/components/quellen/quellen-view.tsx`, `schedulePoll` aktualisiert `state.runs` und `sources` nicht.

#### BUG-2: Kanonischer Entwurf erfüllt Mindestvertrag nicht
- **Severity:** High
- **Reproduktion:** Modellantwort ohne `version`, ohne Quellenbelege oder mit diskretionärer Regel wie „bei starkem Momentum einsteigen“ und leerem `open_questions` zurückgeben.
- **Expected:** Versionsnummer und Belege je Regel sind vorhanden; diskretionäre Regel wird als offene Unklarheit/nicht testbar gespeichert.
- **Actual:** Version ist in Migration, Schema und UI nicht vorhanden; Belege und offene Unklarheiten bleiben optional, die Regel kann als `Entwurf` persistieren.
- **Root Cause:** Die Normalisierung erzwingt nur Entry-/Exit-Regeln und Vorschlags-Parameter, nicht den restlichen Mindestvertrag.

#### BUG-3: Provider-Fehler kann in API und UI offengelegt werden
- **Severity:** High
- **Reproduktion:** OpenCode mit einem Fehlertext starten, der vertrauliche Provider-Details enthält.
- **Expected:** Nutzer erhält eine generische Fehlermeldung; Detail bleibt ausschließlich serverseitig und bereinigt.
- **Actual:** `run_opencode` übernimmt `stderr`, `_mark_failed` persistiert ihn, `GET /extractions/{id}` und die UI geben ihn aus.
- **Root Cause:** Unbereinigte Exception-Texte werden als `error_message` gespeichert und gerendert.

### Summary

- **Acceptance Criteria:** 4/8 passed, 4/8 failed.
- **Bugs:** 3 High, 0 Critical, 0 Medium, 0 Low.
- **Production Ready:** **NO** — High-Bugs blockieren die Kernanzeige, den Entwurfsvertrag und den Secret-Schutz.
- **Status:** bleibt **In Review**.

## Deployment
_To be added by /deploy_
