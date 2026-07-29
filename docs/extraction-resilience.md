# Extraction Resilience

## Problem

FastAPI `BackgroundTasks` sind nicht durabel. Bei Server-Neustart während einer laufenden Extraktion geht der Task verloren — `sources.extraction_status` bleibt `'wird extrahiert'`, `extraction_runs.status` bleibt `'läuft'`.

Keine Recovery → Quelle für immer blockiert, kein Retry möglich.

## Fix: 2026-07-17

### Backend — Startup-Recovery (`main.py`)

Lifespan-Handler `_recover_stuck_extractions()` läuft beim API-Start. Findet alle Sources mit `extraction_status = 'wird extrahiert'` deren letzter Run `status = 'läuft'` und `started_at > 30min` zurückliegt. Setzt beide auf `'fehlgeschlagen'`.

30-Minuten-Schwelle verhindert, dass ein API-Neustart laufende Extraktionen fälschlich abbricht.

### Backend — Härtung (`opencode_extraction.py`)

- `_mark_failed()`: Interne DB-Fehler separat per `try/except` gefangen → nie re-raise. Ein DB-Fehler beim Fehler-Reporting blockiert nicht mehr die Status-Aktualisierung.
- `execute_extraction()`: Äußerer `try/except` als letztes Safety-Net. Fängt alle unerwarteten Exceptions und ruft `_mark_failed`.
- `keine Treffer`-Pfad: `run_command`-Aufrufe durch `try/except` geschützt.

### Frontend — Manueller Retry (`quellen-view.tsx`)

Retry-Button (`"Erneut extrahieren"`) jetzt auch für Quellen mit Status `"wird extrahiert"`. User kann hängengebliebene Extraktion manuell neu starten.
