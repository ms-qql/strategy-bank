# Feature Index — Strategy Bank

**Next Available ID:** PROJ-10

| ID | Feature | Status | Priorität | Dependencies |
|---|---|---|---|---|
| PROJ-1 | Quellenerfassung | Approved | P0 | – |
| PROJ-2 | KI-Extraktion | Approved | P0 | PROJ-1 |
| PROJ-3 | Verifizierung und Versionierung | Approved | P0 | PROJ-2 |
| PROJ-4 | Batch-Konfiguration | In Progress | P0 | PROJ-3 |
| PROJ-5 | Credit-Gate | Planned | P0 | PROJ-4 |
| PROJ-6 | Queue und trader.dev-Ausführung | Planned | P0 | PROJ-5, PROJ-8 |
| PROJ-7 | Ergebnisvergleich | Planned | P0 | PROJ-6 |
| PROJ-8 | Audit-Trail | Planned | P0 | PROJ-3, PROJ-4, PROJ-5 |
| PROJ-9 | Markdown-Export | Planned | P1 | PROJ-8 |

**Empfohlene Build-Reihenfolge:** PROJ-1 → PROJ-2 → PROJ-3 → PROJ-4 → PROJ-5 → PROJ-8 → PROJ-6 → PROJ-7. PROJ-9 folgt als P1.

**Phase 2 / Phase 3 (nicht in INDEX, siehe `docs/Brainstorm-strategy-bank-v2.md` §17):** PDF/Screenshot-OCR, Hal-Sync, zweiter Agent-Provider, freie Web-Links, anpassbare Kategorien, Multi-Upload, Composite Score, Parameter-Sweeps, Regime-Analyse, Signal-Reverse-Engineering.
