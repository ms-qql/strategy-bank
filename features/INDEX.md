# Feature Index — Strategy Bank

**Next Available ID:** PROJ-26

| ID | Feature | Status | Priorität | Dependencies |
|---|---|---|---|---|
| PROJ-1 | Quellenerfassung | Deployed | P0 | – |
| PROJ-2 | KI-Extraktion | Deployed | P0 | PROJ-1 |
| PROJ-3 | Verifizierung und Versionierung | Deployed | P0 | PROJ-2 |
| PROJ-4 | Batch-Konfiguration | Deployed | P0 | PROJ-3 |
| PROJ-5 | Credit-Gate | Deployed | P0 | PROJ-4 |
| PROJ-6 | Queue und trader.dev-Ausführung | Deployed | P0 | PROJ-5, PROJ-8 |
| PROJ-7 | Ergebnisvergleich | In Review | P0 | PROJ-6 |
| PROJ-8 | Audit-Trail | Deployed | P0 | PROJ-3, PROJ-4, PROJ-5 |
| PROJ-9 | Markdown-Export | Deployed | P1 | PROJ-8 |
| PROJ-10 | Positions-, Exit- und Crypto-MTS-Kompatibilitätsmodell | Deployed | P0 | PROJ-2, PROJ-3 |
| PROJ-11 | Sidebar-Navigation | Deployed | P0 | PROJ-1, PROJ-4, PROJ-7 |
| PROJ-12 | Automatische Backtest-Ausführung aus der App | Deployed | P0 | PROJ-5, PROJ-6, PROJ-8 |
| PROJ-13 | LLM-basierte Pine-Script-Generierung (ersetzt Regex-Übersetzer) | In Review | P0 | PROJ-6, PROJ-2 |
| PROJ-14 | Markdown-Drag-and-Drop in der Quellenerfassung | Deployed (2026-07-16, v0.2.24) | P1 | PROJ-1 |
| PROJ-15 | Einklappbare Liste vorhandener Batches | Planned | P1 | PROJ-4 |
| PROJ-16 | Scrollbare Strategieversionsauswahl im Backtest | Architected | P1 | PROJ-4 |
| PROJ-17 | Instrumente pro Batch aktivieren oder ausblenden | Deployed (Backend fix, 2026-07-16, v0.2.23) | P0 | PROJ-4, PROJ-5 |
| PROJ-18 | Einfachauswahl für den Richtungsmodus | Deployed (Frontend + Backend, 2026-07-16, v0.2.23) | P0 | PROJ-4 |
| PROJ-19 | Hal-Vault-Sync für Quellen + Feldbereinigung | Deployed (2026-07-29, v0.2.31) | P1 | PROJ-9, PROJ-2, PROJ-3 |
| PROJ-20 | PDF, EPUB und MOBI als Markdown importieren | Deployed (Mehrfach-Upload, 2026-07-29, v0.2.34) | P1 | PROJ-1, PROJ-2, PROJ-14 |
| PROJ-21 | HAL-Import und Ergebnis-Screening | Deployed (2026-07-30, v0.2.38) | P0 | PROJ-3, PROJ-7 |
| PROJ-22 | Regime-Analyse | Deployed (2026-07-31, v0.2.39) | P1 | PROJ-21 |
| PROJ-23 | Erfolgsfaktorenanalyse | Architected | P1 | PROJ-21 |
| PROJ-24 | Robustheitslabor | Planned | P2 | PROJ-3, PROJ-21 |
| PROJ-25 | Crypto-MTS-Forecast-Varianten | Planned | P3 | PROJ-10, PROJ-21, PROJ-24 |

**Empfohlene nächste Umsetzung:** PROJ-21 → PROJ-22 → PROJ-23 → PROJ-24 → PROJ-25. PROJ-15 und PROJ-16 bleiben unabhängige UI-Backlogpunkte; PROJ-13 verbleibt bis zur End-to-End-Verifikation in Review.

**Später (nicht in INDEX):** Scan-PDF-/Screenshot-OCR, zweiter Agent-Provider, freie Web-Links, anpassbare Kategorien, Composite Score und Signal-Reverse-Engineering.
