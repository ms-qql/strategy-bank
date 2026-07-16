# PROJ-13: LLM-basierte Pine-Script-Generierung (ersetzt Regex-Übersetzer)

## Status: In Review
**Created:** 2026-07-16
**Last Updated:** 2026-07-16
**Backend implemented:** 2026-07-16 (`pine_generator.py` Neubau + Tests, ungecommitted)
**QA:** 2026-07-16 — 2 Bugs offen (siehe QA Test Results), Approval ausstehend

## Dependencies
- Ersetzt einen Teil von PROJ-6 (Queue und trader.dev-Ausführung): der dort spezifizierte Pine-Übersetzer (`backend/app/services/pine_generator.py`) wird durch diesen Spec vollständig neu beschrieben und implementiert. PROJ-6s Queue-, Idempotency- und Worker-Logik bleibt unverändert.
- Requires: OpenCode-Runtime-Anbindung aus PROJ-2 (KI-Extraktion) — `opencode_extraction.run_opencode()` wird als bestehende, bereits authentifizierte LLM-Schnittstelle wiederverwendet (kein neuer Provider, kein neuer API-Key).

## Kontext / Root Cause

Der ursprüngliche PROJ-6-Pine-Generator war ein selbstgebauter Regex-Übersetzer
(~20 Patterns für RSI/SMA/EMA/MACD/Volume/etc.), der natürlichsprachige
Entry-/Exit-Regeln aus `strategy_versions.snapshot` in Pine-v5-Ausdrücke
übersetzte. Jede Formulierung außerhalb der vorgesehenen Patterns führte zu
`PineGenerationError`; der Worker markierte den Run als fehlgeschlagen
(`error_category = "pine_generation"`). In der Praxis (Nutzerbericht: 20-30
erfolglose Versuche) scheiterte die Übersetzung häufig, weil reale
Formulierungen nie vollständig durch Regex abbildbar sind.

Ein Vergleichstest in einer normalen Terminal-Session (Claude Code mit
trader.dev-MCP-Zugriff, ohne die App) zeigte den funktionierenden Ansatz:
das LLM schreibt das vollständige Pine-v5-Script selbst in einem Schritt und
übergibt es an `quick_backtest` — Ergebnis lag innerhalb weniger Sekunden vor
(Report: `https://mcp-api.trader.dev/backtest/01KXNB97NH73XTK0S2SG4TWRM9`,
Strategie „Mean-Reversion RSI“ auf BTCUSDT.P, 4h, 2021–2024).

Wichtige Klarstellung: Alle trader.dev-MCP-Tools (`quick_backtest`,
`create_strategy`, `run_backtest`) verlangen zwingend fertigen `pineSource` —
es gibt keinen MCP-Tool-Pfad, bei dem trader.dev selbst aus einer
Kurzbeschreibung Pine generiert. „Trader.dev mehr Arbeit machen lassen“
bedeutet technisch also nicht weniger Pine-Generierung, sondern: die
Pine-Generierung von einem starren Regex-Übersetzer auf einen einzelnen
LLM-Schreibschritt verlagern (wie im Terminaltest), und trader.dev den Rest
überlassen (Symbol-Resolve, Backtest-Ausführung, Versionierung,
Cascade-Exit-Erkennung).

**Nachträgliche Klärung (2026-07-16, nach Nutzerrückfrage):** Im Terminaltest
hat nicht trader.dev den Prompt-Text erhalten. Der Text war der Prompt **an
Claude** (die Terminal-Session); Claude hat daraus selbst das Pine-Script
geschrieben und dieses (nicht den Prompt-Text) als `pineSource`-Argument an
`quick_backtest` übergeben — das MCP-Tool-Schema erzwingt das (`required:
pineSource`), unabhängig davon, dass die Claude-Code-Oberfläche den Tool-Call
nur als kollabierten „Called trader-dev“-Einzeiler anzeigt und die vollen
Argumente nicht inline sichtbar macht. Das bestätigt exakt die BUG-2-Prämisse
unten: der Terminaltest bewies, dass **Claude** als Pine-Autor sehr schnell
und sauber funktioniert — er bewies nichts über das in der App tatsächlich
verdrahtete Modell (`opencode-go/deepseek-v4-flash`).

## User Stories
- Als Trader möchte ich, dass ein bestätigter Strategie-Entwurf zuverlässig in ein lauffähiges Pine-Script übersetzt wird, unabhängig von der genauen Formulierung der Entry-/Exit-Regel.
- Als Trader möchte ich nicht mehr wiederholt fehlschlagende Runs wegen „nicht übersetzbarer“ Regeln sehen, wenn die Regel inhaltlich eindeutig ist.
- Als Trader möchte ich, dass alle im Entwurf bestätigten Angaben (These, Kategorie, Richtung, Parameter, Positions-Modus) in die Pine-Generierung einfließen, nicht nur Entry-/Exit-Text isoliert.

## Acceptance Criteria
- [x] Öffentliches API von `pine_generator.py` (`generate()`, `PineGenerationError`) bleibt unverändert — `worker.py` erfordert keine Anpassung.
- [x] `generate()` baut aus dem Snapshot (These, Kategorie, Richtung, Entry-/Exit-Regel, Positions-Modus, Parameter, Warmup-Anforderung) sowie Timeframe/Capital/Commission/Slippage/Pyramiding einen vollständigen Prompt.
- [x] Der Prompt fordert ein einzelnes, mit `//@version=5` beginnendes Pine-v5-Script in genau einem ```pine-Codeblock ohne Zusatztext.
- [x] Der Prompt verlangt explizit edge-getriggerte Entry-/Exit-Logik (kein `strategy.close()` bei jeder Bar mit wahrer Bedingung) sowie Parameter als `input.*`-Deklarationen.
- [x] Fehlt die Entry-Regel im Snapshot, wird `PineGenerationError` sofort geworfen — kein LLM-Aufruf ohne Mindestinhalt.
- [x] Scheitert der LLM-Aufruf (Timeout, Provider-Fehler) oder enthält die Antwort kein gültiges Pine-Script (kein `//@version=5`), wird `PineGenerationError` mit verständlichem Grund geworfen statt eines stillen Fehlschlags.
- [x] Bestehende Regex-Übersetzungslogik (~20 Patterns, `_translate_rule` etc.) ist vollständig entfernt.
- [ ] End-to-End-Verifikation: ein realer Draft aus der laufenden Dev-DB (z. B. „Mean-Reversion RSI“) durchläuft den Worker vollständig bis zu einem erfolgreichen `backtest_executions`-Eintrag.
- [ ] Änderung ist committed und über die reguläre Test-Suite (`pytest`) grün im CI-Lauf bestätigt.

## Edge Cases
- Snapshot ohne Parameter (`parameters: []`): Prompt weist das LLM an, selbst sinnvolle Standardwerte zu wählen und als `input.*` zu deklarieren, statt zu scheitern.
- Snapshot ohne Exit-Regel: Prompt verlangt einen sinnvollen Systemdefault (Bar-Count-Exit) statt einer endlos offenen Position.
- LLM liefert Erklärtext statt Code oder eine unvollständige/offene Code-Fence: `_extract_pine()` nimmt das letzte ```pine-Fence-Match; ohne erkennbaren `//@version=5`-Tag gilt die Antwort als ungültig → `PineGenerationError`.
- LLM-Aufruf (OpenCode-Subprocess) hängt oder überschreitet Timeout: bestehender `extraction_timeout_seconds`-Wert aus `opencode_extraction.py` greift, Fehler wird als `PineGenerationError` durchgereicht.
- Cascade-Exit-Pattern trotz expliziter Prompt-Anweisung: bleibt Aufgabe des bestehenden PROJ-6-Korrekturpfads (trader.dev-Warning-Auswertung im Worker), nicht Teil dieses Fixes.

## Non-Goals
- Keine Änderung an Queue-, Idempotency- oder Retry-Logik aus PROJ-6.
- Keine Änderung an `trader_dev.py` (MCP-Aufruf bleibt `quick_backtest` mit fertigem `pineSource`).
- Kein neuer LLM-Provider oder zusätzlicher API-Key — Wiederverwendung der bestehenden OpenCode-Runtime.
- Keine Behebung des separat entdeckten Bugs in `worker.py:_load_strategy_details` (Batch/Timeframe-Auswahl über `JOIN runs ... LIMIT 1` ohne Filter auf den aktuellen Run) — eigenes Ticket, falls bestätigt.

## Technical Requirements (optional)
- Wiederverwendung: `from .opencode_extraction import run_opencode` (kein neuer Subprocess-/HTTP-Client).
- Security: kein API-Key im Prompt oder Log; unverändert gegenüber bestehender OpenCode-Anbindung (Provider-Credentials liegen bei `~/.config/opencode`, nie im App-Code).

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-16 · **Stack:** FastAPI / Python-Service-Layer, kein Frontend-Anteil · **Branch:** main (working tree, ungecommitted)

### A) Betroffene Module

```text
backend/app/services/pine_generator.py   (komplett neu geschrieben)
  - build_prompt(snapshot, params, timeframe, direction, initial_capital,
                 commission_pct, slippage_ticks, pyramiding) -> str
  - _extract_pine(raw_text) -> str        (Fence-Parsing + @version=5-Check)
  - generate(snapshot, params=None, *, timeframe, direction, ...) -> str
  - PineGenerationError                    (unverändertes Exception-API)

backend/app/services/worker.py            (UNVERÄNDERT)
  - _load_strategy_details() ruft weiterhin generate_pine(snapshot, ...) —
    Import- und Aufrufsignatur identisch zur alten Regex-Implementierung.

backend/app/services/trader_dev.py        (UNVERÄNDERT)
  - start_backtest() übergibt den von generate() erzeugten pine_source
    unverändert an quick_backtest.
```

### B) Datenfluss

```text
strategy_versions.snapshot (entry_rule, exit_rule, thesis, category,
direction, position_mode, parameters, warmup_requirement)
        │
        ▼
pine_generator.build_prompt()  — reiner Text-Prompt, keine Regex-Analyse
        │
        ▼
opencode_extraction.run_opencode()  — bestehende OpenCode-Runtime,
                                       gleicher Pfad wie PROJ-2-Extraktion
        │
        ▼
pine_generator._extract_pine()  — Codeblock/​@version=5-Validierung
        │
        ▼
worker._submit_backtest() → trader_dev.start_backtest() → quick_backtest
```

### C) Tech-Entscheidungen (warum)

- **Wiederverwendung von `run_opencode()` statt neuem LLM-Client:** Die App hat bereits eine authentifizierte, getestete OpenCode-Anbindung (PROJ-2). Ein zweiter LLM-Zugriffspfad würde Betrieb und Angriffsfläche ohne Mehrwert vergrößern.
- **Unverändertes öffentliches API (`generate`, `PineGenerationError`):** Der Worker (PROJ-6) bleibt komplett unangetastet — kleinstmöglicher Diff, kein Risiko für die bestehende Queue-/Idempotency-Logik.
- **Ein einziger LLM-Aufruf pro Generierung, kein Retry-Loop im Generator selbst:** Retries (inkl. Cascade-Exit-Korrektur) sind bereits Aufgabe des Workers/PROJ-6; eine zweite Retry-Ebene im Generator würde Verantwortlichkeiten vermischen.
- **Prompt verlangt genau einen ```pine-Codeblock:** Vereinfacht `_extract_pine()` auf ein einzelnes Regex-Fence-Match plus `@version=5`-Plausibilitätscheck, ohne eigene Pine-Syntaxvalidierung nachzubauen (die übernimmt trader.dev beim Backtest-Aufruf ohnehin).
- **Keine Fallback-Regex-Logik erhalten:** Halbe Lösungen (Regex bei einfachen Regeln, LLM bei Rest) hätten zwei Fehlerklassen und zwei Wartungspfade erzeugt, ohne dass der Terminaltest dafür einen Bedarf gezeigt hätte.

### D) Abhängigkeiten
- Backend: keine neuen Python-Pakete — `opencode_extraction.run_opencode` und `settings.opencode_binary` / `settings.extraction_model` / `settings.extraction_timeout_seconds` existieren bereits.
- trader.dev: keine neue Tool-Nutzung — weiterhin ausschließlich `quick_backtest` mit vollständigem `pineSource` (PROJ-6).

## QA Test Results

**Tested:** 2026-07-16
**Backend:** kein laufender FastAPI-Server nötig (reiner Service-Layer-Test), DB `strategy_bank_db` erreichbar
**Tester:** QA Engineer (AI)
**Branch:** main (Feld „Branch“ im Tech Design nennt explizit main; kein Feature-Branch angelegt)
**Tests:** volle Suite `pytest` — 196 passed, 1 pre-existing Fail (unabhängig von PROJ-13 bestätigt); zusätzlich 3 manuelle Live-Explorationen gegen die echte Dev-DB und den echten OpenCode-Binary (kein Mock)

Hinweis: Dieses Projekt hat kein JWT/Mandanten-Modell (Single-Tenant-Tool, per PROJ-6-QA bereits festgehalten) und keinen Flutter-/Web-Frontend-Anteil in diesem Ticket — Auth-/Tenant-Red-Team-Schritte aus der Standard-Checkliste entfallen entsprechend; stattdessen Fokus auf den neuen LLM-Pfad selbst.

### Acceptance Criteria Status
- [x] Öffentliches API unverändert — `worker.py` nicht editiert (Diff bestätigt: nur `pine_generator.py` + Test geändert)
- [x] Prompt enthält alle Snapshot-Felder (`TestBuildPrompt`)
- [x] Prompt fordert genau einen ```pine-Block mit `@version=5` (`test_includes_snapshot_fields`)
- [x] Edge-Trigger- und `input.*`-Anforderung im Prompt-Text enthalten
- [x] Fehlende Entry-Regel wirft sofort `PineGenerationError` ohne LLM-Aufruf (`test_missing_entry_raises`)
- [x] LLM-Fehler und ungültige LLM-Antwort werfen `PineGenerationError` mit verständlichem Text (`test_llm_call_failure_raises`, `test_invalid_llm_output_raises`) — **mit Einschränkung, siehe BUG-1**
- [x] Regex-Übersetzungslogik vollständig entfernt (Diff: alle `_RSI_RE`/`_SMA_RE`/etc.-Patterns weg)
- [ ] End-to-End über echten Worker/DB-Draft mit echter LLM-Antwort: **blockiert**, siehe BUG-2 (fehlendes Prod-Secret in dieser Umgebung)
- [ ] Commit + grüner CI-Lauf: weiterhin offen — Änderung liegt noch im Working Tree, siehe Production-Ready-Empfehlung

### Edge Cases Status
- [x] Snapshot ohne Parameter → Prompt verlangt sinnvolle Defaults (`test_includes_snapshot_fields` deckt Struktur ab; Formulierung manuell gegengelesen)
- [x] Snapshot ohne Exit-Regel → Prompt verlangt Systemdefault (`test_missing_exit_rule_asks_for_default`)
- [ ] „LLM liefert Erklärtext statt Code“ — im Spec als abgedeckt behauptet, **de facto nicht sicher abgedeckt**, siehe BUG-1
- [x] LLM-Aufruf hängt/überschreitet Timeout → reproduziert (siehe BUG-2-Exploration): `run_opencode` respektiert `extraction_timeout_seconds` (300s), `generate()` wandelt den `subprocess.TimeoutExpired`/`RuntimeError` korrekt in `PineGenerationError` um. Mechanik funktioniert, siehe BUG-2 für den inhaltlichen Befund dahinter.
- [ ] Cascade-Exit-Pattern trotz Prompt-Anweisung — nicht testbar ohne echte LLM-Antwort (blockiert durch BUG-2), bleibt laut Spec ohnehin PROJ-6-Aufgabe.

### Security-Hinweise (kein formaler Tenant-/Auth-Audit anwendbar)
- Kein API-Key-Leak in Fehlerpfaden: `PineGenerationError`-Texte enthalten nur `str(exc)` aus `run_opencode`/subprocess, kein Prompt-Dump, kein Secret (Code-Review von `pine_generator.py` + `opencode_extraction.py`, keine neuen `logger`-Aufrufe mit Prompt-Inhalt eingeführt).
- **Prompt Injection (Low-Medium, dokumentiert, nicht gefixt):** `thesis`/`entry_rule`/`exit_rule`/`warmup_requirement` sind freier Text, der ursprünglich aus beliebigen, vom Nutzer hochgeladenen Quellen extrahiert wurde (PROJ-1/2), und wird ungefiltert/ohne klare Trennzeichen in den Prompt eingebettet. Eine präparierte Quelle könnte Modell-Anweisungen im Feldinhalt verstecken. Blast Radius ist gering (Single-User-Tool, Pine läuft nur sandboxed bei trader.dev, kein Codeausführungspfad in dieser App) — dennoch als Finding festgehalten, da nicht Teil der Prompt-Härtung war.

### Bugs Found

#### BUG-1 (Medium): `_extract_pine()` akzeptiert Prosa als „gültiges“ Pine-Script
- **Reproduziert:** `pg._extract_pine("Ich kann leider keinen vollständigen Code liefern, aber //@version=5 ist die aktuelle Pine-Version. Bitte mehr Infos.")` liefert den kompletten Fließtext zurück statt `""`.
- **Ursache:** Ohne Codeblock-Fence prüft `_extract_pine` nur, ob `//@version=5` **irgendwo im Text** vorkommt (`_VERSION_TAG_RE.search`), nicht ob der Text **damit beginnt** (wie der Prompt es explizit vom Modell verlangt: „der mit `//@version=5` beginnt“).
- **Auswirkung:** Reine Prosa-Antworten des Modells (z. B. Rückfrage statt Code) werden als `pine_source` akzeptiert und an `trader_dev.start_backtest()` weitergereicht. Das schlägt dort mit einem Pine-Compile-Fehler fehl, wird aber als `trader_dev_error` statt `pine_generation` kategorisiert — irreführender Fehlergrund für den Nutzer, plus ein unnötiger externer API-Roundtrip.
- **Fix-Vorschlag (nicht umgesetzt):** Im No-Fence-Zweig zusätzlich prüfen, dass `candidate.strip()` mit `//@version=5`/`// @version=5` **beginnt**, nicht nur enthält.

#### BUG-2 (High): Live-LLM-Aufruf in dieser Umgebung nicht verifizierbar — Prod nutzt anderes Modell als der validierende Terminaltest
- **Exploration 1:** `pg.generate()` mit echten Draft-Feldern („Mean-Reversion RSI“: `RSI > 30` / `RSI < 70`, entry_exit) lief 300s (voller `extraction_timeout_seconds`-Wert) und endete in `PineGenerationError: ... timed out after 300.0 seconds`.
- **Exploration 2 (Root Cause):** Direkter CLI-Aufruf `opencode run "Say OK" -m opencode-go/deepseek-v4-flash` liefert sofort `401 Missing API key` — `~/.config/opencode/auth.json` existiert in dieser Shell nicht. `docker-compose.yml` zeigt: Produktion braucht `OPENCODE_GO_API_KEY` als Pflicht-Env-Var (`:?Set OPENCODE_GO_API_KEY in Dokploy`); in diesem Dev-Sandbox ist sie nicht gesetzt (`printenv` bestätigt leer). Dieselbe Präbedingung gilt bereits für die bestehende PROJ-2-Extraktion (identischer `run_opencode()`-Pfad) — **keine Regression durch PROJ-13**, aber ein echter Blocker für die in AC/Edge-Cases behauptete Live-Verifikation.
- **Wichtigerer Befund, unabhängig vom fehlenden Key:** Der validierende Terminaltest, der diesen ganzen Umbau motiviert hat (Screenshot: Backtest in Sekunden, sauberes Pine-Script), lief mit **Claude** (Sonnet-Klasse) als Autor des Pine-Scripts. Die tatsächlich verdrahtete Produktions-Konfiguration (`settings.extraction_model = "opencode-go/deepseek-v4-flash"`) nutzt ein anderes, kleineres Modell für exakt denselben Schreibschritt. Es gibt noch keinen Beleg, dass `deepseek-v4-flash` ebenso zuverlässig ein zero-shot korrektes, edge-getriggertes (kein Cascade-Exit) Pine-v5-Script liefert wie Claude im Terminaltest.
- **Auswirkung:** Die Kernannahme des gesamten PROJ-13-Ansatzes — „ein LLM-Schreibschritt reicht“ — ist mit dem in Produktion tatsächlich genutzten Modell noch nicht bestätigt.
- **Empfehlung:** Vor Approval einmal mit gesetztem `OPENCODE_GO_API_KEY` (Dev- oder Staging-Key) `pg.generate()` gegen 2-3 reale Drafts laufen lassen und das Ergebnis (kompiliert? cascade-exit-frei? inhaltlich korrekt?) mit dem Claude-Terminaltest vergleichen. Falls `deepseek-v4-flash` unzuverlässig ist: Modell für diesen Anwendungsfall in den Settings konfigurierbar/getrennt von `extraction_model` machen (separates Ticket).

#### Vorbestehend, unabhängig von PROJ-13
- `test_results.py::TestResultsWithData::test_multiple_result_types_are_separate_rows` — per `git stash` bestätigt: Fail tritt auch ohne diese Änderung auf. Nicht Teil dieses Tickets, sollte aber nicht in Vergessenheit geraten.
- Separat notierter Verdacht (nicht verifiziert): `worker.py:_load_strategy_details` wählt Batch/Timeframe über `JOIN runs r ON r.strategy_version_id = sv.id ... LIMIT 1` ohne Filter auf den konkret verarbeiteten Run — könnte bei mehreren Runs derselben Strategieversion Batch-Daten eines anderen Runs ziehen. Eigenes Ticket nötig, falls bestätigt.
- Datenintegrität: Der einzige echte `strategy_versions`-Datensatz in der Dev-DB („Mean-Reversion RSI“) hat ein unvollständiges `snapshot` (nur `name`/`category`/`direction`, ohne `entry_rule`/`exit_rule`/`parameters`), obwohl der zugehörige `strategy_drafts`-Eintrag alle Felder vollständig hat. Wirkt wie Seed-/Testdaten, die nie den echten Freeze-Endpunkt (PROJ-3) durchlaufen haben — nicht PROJ-13, aber es bedeutet: **kein einziger im System vorhandener Run kann aktuell End-to-End getestet werden**, ohne zuerst einen Draft sauber über `/drafts/{id}/freeze` einzufrieren.

### Summary
- **Acceptance Criteria:** 7/9 passed, 2 blockiert/offen (Live-Verifikation, Commit)
- **Bugs Found:** 2 (1 Medium, 1 High) — beide im neuen PROJ-13-Code bzw. seiner unbewiesenen Modell-Annahme, 0 Regressionen in bestehendem Code
- **Security:** kein Tenant-/Auth-Modell anwendbar; 1 Low-Medium-Hinweis (Prompt Injection, dokumentiert, nicht blockierend für Single-User-Tool)
- **Production Ready:** NEIN
- **Recommendation:** Vor Approval (a) BUG-1 fixen (strengere `_extract_pine`-Prüfung), (b) BUG-2 auflösen — mit echtem `OPENCODE_GO_API_KEY` mindestens 2-3 reale Drafts durch `generate()` laufen lassen und das deepseek-v4-flash-Ergebnis bewerten, (c) einen Draft sauber über `/drafts/{id}/freeze` einfrieren, damit ein vollständiger Worker-E2E-Lauf überhaupt möglich ist, (d) danach committen und diesen QA-Durchlauf wiederholen.

## Deployment
**Entscheidung (2026-07-16, Nutzer):** Bewusster Test-Deploy auf main trotz offener BUG-1/BUG-2 — Ziel ist, BUG-2 (unbewiesene Modell-Qualität von `opencode-go/deepseek-v4-flash`) erst in der echten Umgebung zu klären, da dort `OPENCODE_GO_API_KEY` gesetzt ist (in der Dev-Sandbox fehlt er, siehe BUG-2-Exploration). Das ist kein QA-Approval — BUG-1 bleibt ungefixt im deployten Code, Status bleibt **In Review** bis reale `generate()`-Ergebnisse ausgewertet sind.

**Nächster Schritt nach diesem Deploy:** einen Draft sauber über `/drafts/{id}/freeze` einfrieren, Worker gegen ihn laufen lassen, generiertes Pine-Ergebnis + Backtest-Ausgang prüfen (kompiliert? cascade-exit-frei? inhaltlich korrekt vs. Claude-Terminaltest?). Danach BUG-1 fixen und regulären `/abc-qa`-Durchlauf wiederholen, bevor Status auf Approved geht.
