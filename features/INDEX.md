# Feature Index — Strategy Bank

**Next Available ID:** PROJ-13

| ID | Feature | Status | Priorität | Dependencies |
|---|---|---|---|---|
| PROJ-1 | Quellenerfassung | Deployed | P0 | – |
| PROJ-2 | KI-Extraktion | Deployed | P0 | PROJ-1 |
| PROJ-3 | Verifizierung und Versionierung | Deployed | P0 | PROJ-2 |
| PROJ-4 | Batch-Konfiguration | Deployed | P0 | PROJ-3 |
| PROJ-5 | Credit-Gate | Deployed | P0 | PROJ-4 |
| PROJ-6 | Queue und trader.dev-Ausführung | Deployed | P0 | PROJ-5, PROJ-8 |
| PROJ-7 | Ergebnisvergleich | Approved | P0 | PROJ-6 |
| PROJ-8 | Audit-Trail | Deployed | P0 | PROJ-3, PROJ-4, PROJ-5 |
| PROJ-9 | Markdown-Export | Approved | P1 | PROJ-8 |
| PROJ-10 | Positions-, Exit- und Crypto-MTS-Kompatibilitätsmodell | Deployed | P0 | PROJ-2, PROJ-3 |
| PROJ-11 | Sidebar-Navigation | Approved | P0 | PROJ-1, PROJ-4, PROJ-7 |
| PROJ-12 | Automatische Backtest-Ausführung aus der App | Approved | P0 | PROJ-5, PROJ-6, PROJ-8 |

**Empfohlene nächste Umsetzung:** PROJ-11 → PROJ-12 → PROJ-7. PROJ-9 folgt als P1.

**Phase 2 / Phase 3 (nicht in INDEX, siehe `docs/Brainstorm-strategy-bank-v2.md` §17):** PDF/Screenshot-OCR, Hal-Sync, zweiter Agent-Provider, freie Web-Links, anpassbare Kategorien, Multi-Upload, Composite Score, Parameter-Sweeps, Regime-Analyse, Signal-Reverse-Engineering.
