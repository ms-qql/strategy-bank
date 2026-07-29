# Fix-Brief: Performance & Zuverlässigkeit der Pine-Generierung und Backtest-Ausführung

## TL;DR

Zwei unabhängige Problemkreise:

1. **Pine-Generierung bricht bei vielen Strategien** — weil die LLM-basierte Generierung (opencode subprocess) fehleranfällig ist und der Worker in einer Retry-Endlosschleife hängt.
2. **App 5-10x langsamer als Terminal** — weil eine 4-Stufen-Pipeline (Poll → Subprocess → MCP → Poll) statt eines direkten MCP-Calls läuft.

---

## Problem 1: Pine-Generierung schlägt fehl

### Root Causes

**A) Regex-Übersetzer (ursprünglich, historisch):**
- `backend/app/services/pine_generator.py` war ein Regex-Übersetzer (~20 Patterns) von Freitext → Pine v5
- Jede unerwartete Formulierung → `PineGenerationError` → Run `fehlgeschlagen`
- Worker pollt alle 30s und **regeneriert denselben kaputten Regex** → Endlosschleife (20-30+ Versuche)
- Fix vorhanden: LLM-basiert via `run_opencode()` ersetzt

**B) LLM-Generierung (aktuell, trotz Umstellung noch fehleranfällig):**

| Bug | Datei:Zeile | Beschreibung |
|-----|------------|--------------|
| `_extract_pine()` zu schwach | `pine_generator.py:111-120` | `_VERSION_TAG_RE.search()` prüft nur, ob `//@version=5` **irgendwo** im Text vorkommt, nicht ob er **damit beginnt**. Prosa wird als gültiges Pine akzeptiert → falsche Fehlerkategorie (`trader_dev_error` statt `pine_generation`) |
| Enum-Namen im Prompt | `pine_generator.py:51-53` | Interner Enum-Wert `signal_reversal` wird direkt in Prompt gesetzt → LLM erzeugt `strategy.signal_reversal()` (existiert nicht) |
| Halluzinierte ta.*-Funktionen | `pine_generator.py:29,116-117` | Pine v5 hat kein `ta.adx()` (→ `ta.dmi()`), kein `ta.kama()` → Blacklist-Regex ist Whack-a-Mole (jede neue Halluzination braucht neuen Fix) |
| Compiler-Feedback-Loop unvollständig | `compiler-feedback-loop` Wissen | Fix existiert ([compiler-feedback-loop-strategy-bank-0458af6d.md](vault://Agentic%20OS/Jupiter/Knowledge/compiler-feedback-loop-strategy-bank-0458af6d.md)) — prüfen ob `generate()` tatsächlich `previous_error` von der DB bekommt |
| Model-Mismatch | `config.py:16` | Tests mit Claude, Produktion mit `opencode-go/deepseek-v4-flash` — kleineres Modell generiert unzuverlässiger |
| `_load_strategy_details` JOIN-Fehler | `worker.py:324-332` | `LIMIT 1` ohne Filter auf aktuellen Run — kann falsche Batch-Daten (falsches Timeframe/Period) laden |

### Fix-Reihenfolge

1. **`_extract_pine()` fixen**: `_VERSION_TAG_RE` von `search()` auf `match()` umstellen — Code muss *mit* `//@version=5` *beginnen*, nicht nur enthalten.
2. **Enum-Namen aus Prompt entfernen**: `signal_reversal` durch beschreibenden Text ersetzen (bereits teilweise gefixt, prüfen ob alle Stellen sauber sind).
3. **Compiler-Feedback-Loop aktivieren**: `worker.py:_mark_failed()` speichert `last_provider_error` in `backtest_executions`; `_load_strategy_details()` übergibt ihn an `generate(previous_error=...)`; `build_prompt()` speist ihn ein → LLM korrigiert sich selbst. Prüfen ob dieser Loop durchgängig funktioniert.
4. **Blacklist-Regex entfernen**: Compiler-Feedback-Loop macht Blacklist überflüssig — `_INVALID_TA_BUILTIN_RE` kann dann ganz raus.
5. **Produktion mit Claude testen**: Falls möglich, `extraction_model` auf Claude umstellen für bessere Pine-Qualität.

---

## Problem 2: App 5-10x langsamer als Terminal

### Architektur-Vergleich

**Terminal (schnell):**
```
User: "MA Crossover BTC" → Claude generiert Pine inline (selber LLM-Context)
→ quick_backtest(pineSource=...) MCP → Ergebnis in 5-15s
```

**App (langsam):**
```
User speichert Strategie → FastAPI API → PostgreSQL
→ [WARTET] Worker pollt alle 30s neue Runs   // 0-30s
→ [PINEGEN] run_opencode() subprocess opencode run ... -m deepseek-v4-flash
  → lädt Modell, generiert Pine, parst Ausgabe, return       // 10-60s
→ [MCP] trader.dev quick_backtest via HTTP                    // 5-15s
→ [SAVE] Ergebnis in PostgreSQL persistieren
→ [POLL] Frontend pollt Status-Endpunkt
→ ≈ 30-120s total
```

### Konkrete Performance-Bremsen

| Stufe | App | Terminal | Hebel |
|-------|-----|----------|-------|
| **Polling-Latenz** | `POLL_INTERVAL_SECONDS = 30` (`worker.py:34`) | 0 (direkt) | Intervall auf 5s senken ODER Webhook/Notify-Mechanismus |
| **Pine-Generierung** | Subprocess `opencode run ...` mit deepseek-v4-flash (Timeout: **300s** in `config.py:18`) | Claude inline (kein Overhead) | Parallelisierung, Caching, oder async |
| **Pipeline-Tiefe** | 4 Stufen (DB→Poll→Subprocess→MCP→DB→Frontend-Poll) | 1 Stufe (MCP-Call) | Subprocess durch Inline-LLM ersetzen |
| **Worker-Modell** | Single-process blocking loop (`time.sleep(30)`) | N/A | Asyncio oder separater Thread für Pine-Gen |
| **Pine-Expiry** | Jeder Run regeneriert Pine frisch (`_load_strategy_details` → `generate_pine`) | Einmalig | Pine in `backtest_executions` cachen |

### Fix-Vorschläge

**Kurzfristig (einfach, hohe Wirkung):**

1. **POLL_INTERVAL auf 5s senken**: `worker.py:34` — reduziert maximale Wartezeit von 30s auf 5s. Minimales Risiko, da `FOR UPDATE SKIP LOCKED` Concurrency schützt.

2. **Pine-Generierung asynchron machen**: `run_opencode()` blockiert den kompletten Worker für 10-60s. Lösungen:
   a) Subprocess mit `asyncio.create_subprocess_exec` + Timeout (max 60s statt 300s)
   b) Pine-Generierung in separaten Thread auslagern (`concurrent.futures.ThreadPoolExecutor`)
   c) Timeout in `config.py` von 300s auf 60s senken

3. **Pine-Ergebnis cachen**: Wenn sich `snapshot` + `params` + `previous_error` nicht geändert haben, `pine_source` wiederverwenden statt neu zu generieren. `backtest_executions.pine_source` wird bereits persistiert — beim Retry prüfen ob Pine schon existiert und gültig ist.

**Mittelfristig (Strukturänderung):**

4. **Blocking-Loop durch Event-Queue ersetzen**: Statt polling: PostgreSQL `NOTIFY`/`LISTEN` oder PgBoss/Celery. Worker wird sofort benachrichtigt wenn ein neuer Run ansteht.

5. **In-Memory Pine-Caching**: `lru_cache` auf `generate()` — identische Snapshots erzeugen identisches Pine.

6. **Frontend-Polling durch SSE/WebSocket**: Statt dass das Frontend alle X Sekunden den Status abfragt, pushed der Worker das Ergebnis via Server-Sent-Events.

---

## Dateien im Überblick

| Datei | Relevanz |
|-------|----------|
| `backend/app/services/pine_generator.py` | Kern: LLM-Prompt-Bau, `_extract_pine()`, `generate()` |
| `backend/app/services/worker.py` | Queue-Verarbeitung, Polling, Retry-Logik |
| `backend/app/services/opencode_extraction.py` | `run_opencode()` Subprocess-Aufruf |
| `backend/app/services/trader_dev.py` | MCP-Client (urllib-basiert) |
| `backend/app/config.py` | `POLL_INTERVAL`, `extraction_timeout`, Model |
| `backend/tests/` | Tests für Pine-Gen und Worker |

## Wissen aus Hal (Quellen)

- `Agentic OS/Jupiter/Knowledge/bug_geloest-strategy-bank-fe8142bb.md` — Regex→LLM-Umstellung
- `Agentic OS/Jupiter/Knowledge/gotcha-mcp-pinesource-strategy-bank-fe8142bb.md` — MCP erfordert pineSource
- `Agentic OS/Jupiter/Knowledge/gotcha-extractpine-falsepositive-strategy-bank-fe8142bb.md` — `_extract_pine()` zu schwach
- `Agentic OS/Jupiter/Knowledge/bug-geloest-sb-fehler.md` — signal_reversal leak
- `Agentic OS/Jupiter/Knowledge/bug-geloest-sb-fix.md` — ta.adx-Halluzination
- `Agentic OS/Jupiter/Knowledge/compiler-feedback-loop-strategy-bank-0458af6d.md` — Compiler-Feedback-Loop
- `Agentic OS/Jupiter/Knowledge/bug-geloest-strategy-bank-quick-backtest-sync-result.md` — Sync-Result-Bug
- `Agentic OS/Jupiter/Knowledge/adr-strategy-bank-ba957293.md` — Worker-Architektur (PostgreSQL-Queue)

---

## Umsetzung 2026-07-29

### Problem 1 — Pine-Zuverlässigkeit

- `_extract_pine()` verlangt den Versions-Header am Anfang der Quelle.
- Interne Positionsmodus-Werte bleiben aus dem Prompt entfernt.
- Der vorhandene Compiler-Feedback-Loop wurde durchgängig bestätigt.
- Die statische `ta.adx`/`ta.kama`-Blacklist wurde entfernt; Compilerfehler
  steuern stattdessen die nächste Generierung.
- Der OpenCode-Timeout wurde von 300 auf 60 Sekunden reduziert.

### Problem 2 — Ausführungslatenz

- Worker-Polling wurde von 30 auf 5 Sekunden reduziert.
- Batch-/Timeframe-Daten werden über den aktuellen Run geladen; der bisherige
  `LIMIT 1`-Mehrdeutigkeitsfehler ist behoben.
- Erfolgreich kompiliertes Pine wird bei gleicher Strategieversion, gleichem
  Timeframe und Richtungsmodus aus `backtest_executions` wiederverwendet.
  Compiler-Retries umgehen den Cache bewusst.

### Verifikation

- Neue Reproduktionstests: grün.
- Betroffene Backend-Module: grün.
- Gesamtsuite: 229 grün; ein vorbestehender, unabhängiger Fehler bleibt in
  `tests/test_results.py::TestResultsWithData::test_multiple_result_types_are_separate_rows`.
- Nicht umgesetzt: Event-Queue, Threads, SSE/WebSockets und In-Memory-Cache.
  Die vorhandene PostgreSQL-Queue und der persistierte Pine-Stand decken den
  aktuellen Umfang ohne neue Infrastruktur ab.
