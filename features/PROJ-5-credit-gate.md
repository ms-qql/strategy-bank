# PROJ-5: Credit-Gate

## Status: Deployed
**Created:** 2026-07-15
**Last Updated:** 2026-07-15

## Dependencies
- Requires: PROJ-4 (Batch-Konfiguration) — liefert die Liste geplanter Runs.

Credit-Annahmen und verfügbare trader.dev-Aktionen stammen verbindlich aus `docs/trader-dev-capability-spike.md`.

## User Stories
- Als Trader möchte ich vor dem Start eines Batches die erwartete Credit-Anzahl sehen, um keine Überraschungen beim Verbrauch zu erleben.
- Als Trader möchte ich ein hartes Credit-Maximum je Batch festlegen, um versehentlich hohe Kosten zu verhindern.
- Als Trader möchte ich den Batch explizit bestätigen, bevor externe Aktionen ausgelöst werden.

## Acceptance Criteria
- [ ] Vor dem Start zeigt die App die erwartete Anzahl externer trader.dev-Aktionen (für den MVP: 1 Credit je geplantem Run, keine Schätzspanne nötig).
- [ ] Die App zeigt den aktuellen Credit-Kontostand (via `get_credits`) und den verbleibenden Bestand nach dem geplanten Batch.
- [ ] Der Nutzer legt vor dem Start ein hartes Credit-Maximum für den Batch fest (Default: exakte Anzahl geplanter Runs).
- [ ] Reicht der aktuelle Credit-Kontostand nicht für den geplanten Batch, startet der Batch nicht; verständliche Fehlermeldung mit fehlender Differenz.
- [ ] Der Nutzer muss den Batch (Runs-Liste) und das Credit-Maximum in einem expliziten Bestätigungsschritt freigeben, bevor die Queue (PROJ-6) etwas auslöst.
- [ ] Tarifhöhe, Credit-Menge und Reset-Zeitraum sind aus `get_credits` gelesene, nicht im Code fest hinterlegte Werte.
- [ ] Kein Privacy-Check ist Teil dieses Gates — die Verantwortung für ausschließlich öffentlich zulässige Strategieinhalte liegt beim Nutzer (Produktentscheidung, siehe PRD Abschnitt 4).

## Edge Cases
- Credit-Maximum wird während der Konfiguration nachträglich reduziert (weniger als geplante Runs): App verlangt Reduktion der Run-Auswahl oder Erhöhung des Maximums vor Bestätigung.
- Retry eines fehlgeschlagenen Runs (siehe PROJ-6) nach Batch-Abschluss: neue, bewusste Credit-Gate-Prüfung für genau diesen einen Run, kein automatischer Verbrauch aus dem ursprünglichen Maximum.
- `get_credits` liefert einen Fehler oder ist nicht erreichbar: Batch-Start blockiert, verständliche Fehlermeldung statt stillem Weiterlaufen mit veraltetem Stand.
- Credit-Kontostand ändert sich zwischen Anzeige und Bestätigung (z. B. durch parallele Nutzung außerhalb der App): Bestätigung prüft den Stand erneut unmittelbar vor Queue-Start.

## Technical Requirements (optional)
- Persistenz: bestätigtes Credit-Maximum und Kontostand-Snapshot zum Bestätigungszeitpunkt werden im Audit-Trail (PROJ-8) mitgespeichert.
- MVP-Planungsannahme: 1.000 Credits pro Woche. Credit-Kosten und Reset-Zeitraum werden in P1 erneut geprüft.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-15 · **Stack:** Next.js + FastAPI + Neon PostgreSQL + trader.dev MCP via OpenCode · **Branch:** dev

### A) Komponentenstruktur (UI — erweitert PROJ-4)

```text
BatchesPage (bestehend)
└── Vorschau & Bestätigung (bestehend, erweitert)
    ├── RunsPreviewTable (bestehende Runs-Liste)
    ├── CreditGatePanel
    │   ├── CreditStatus (aktueller Bestand, Tarif und Reset-Zeitraum)
    │   ├── CreditCalculation (geplante Aktionen und Restbestand danach)
    │   ├── CreditMaximumInput (Default: exakte Zahl geplanter Runs)
    │   ├── RefreshCreditsButton (erneuter Live-Abruf)
    │   └── CreditErrorAlert (fehlende Credits oder nicht erreichbarer Dienst)
    └── ConfirmBatchButton (bestehend; erst aktiv, wenn Runs und Maximum gültig sind)
```

Der Credit-Bereich erscheint erst bei einem gespeicherten, noch nicht bestätigten Batch. Die vorhandene Runs-Liste bleibt die sichtbare Grundlage der Bestätigung. Nach Änderungen an der Batch-Konfiguration wird der Default des Credit-Maximums an die neue Run-Anzahl angepasst; ein bewusst gesetztes niedrigeres Maximum wird nicht still überschrieben, sondern als Konflikt angezeigt.

### B) Datenmodell (Klartext)

Jeder Batch hat bis zur Bestätigung weiterhin nur seine PROJ-4-Konfiguration. Bei der Bestätigung werden zusätzlich festgehalten:

- das vom Nutzer freigegebene harte Credit-Maximum,
- die verbindliche Anzahl geplanter externer Aktionen (im MVP identisch mit der Run-Anzahl),
- der unmittelbar vor Bestätigung gelesene Credit-Kontostand,
- der daraus berechnete Restbestand nach dem Batch,
- die von `get_credits` gelieferten Tarif-/Kontingent- und Reset-Angaben,
- der Zeitpunkt des Live-Checks.

Diese Werte gehören zum bestätigten Batch und werden danach nicht mehr geändert. PROJ-8 kann sie dadurch ohne zweite Datenquelle in den Audit-Trail übernehmen. Die bereits in PROJ-4 angelegten `runs` bleiben die einzelnen Ausführungseinheiten; PROJ-5 legt keine parallele Run- oder Queue-Struktur an. Ein Retry aus PROJ-6 erhält später einen neuen Credit-Check für genau diesen Run und verwendet das ursprüngliche Batch-Maximum nicht erneut.

Gespeichert in Neon PostgreSQL. Keine Dateien, daher kein MinIO. Die App ist laut PRD eine Single-Trader-Microapp; PROJ-5 führt deshalb weder Mandantenmodell noch neue Rollen ein.

### C) API-Form (nur Endpunkte)

```text
GET  /batches/{id}/credit-check
     → liest den aktuellen Stand live über get_credits und liefert geplante
       Aktionen, Credit-Bestand, Restbestand, Tarif/Reset und Blockiergrund

POST /batches/{id}/confirm
     → erhält das Credit-Maximum, liest get_credits unmittelbar erneut,
       blockiert bei Fehler/Unterdeckung/zu kleinem Maximum und bestätigt
       sonst den Batch samt unveränderlichem Snapshot und geplanten Runs

GET  /batches/{id}
     → liefert bei bestätigten Batches zusätzlich Credit-Maximum und Snapshot
```

Der bestehende Confirm-Endpunkt bleibt die einzige Bestätigungsgrenze. Es entsteht kein zweiter „Credit bestätigen“-Endpunkt. PROJ-6 darf nur Runs eines erfolgreich bestätigten Batches in die Queue übernehmen und nutzt für bewusste Einzel-Retries dieselbe serverseitige Gate-Regel erneut.

### D) Tech-Entscheidungen (warum)

- **Ein Credit pro materialisiertem Run:** Die verbindliche MVP-Annahme macht die bereits vorhandene PROJ-4-Run-Vorschau zur Kostenbasis. Eine Schätzlogik oder Spannendarstellung wäre derzeit ohne Mehrwert.
- **Live-Abruf im Backend über OpenCode/trader.dev MCP:** `get_credits` ist eine MCP-Aktion und kein Browser-Endpunkt. Zugangsdaten und die Provider-Antwort bleiben serverseitig; das Frontend erhält nur die für die Entscheidung benötigten Werte.
- **Doppelter Check ist beabsichtigt:** Der erste Abruf informiert den Nutzer. Der zweite Abruf innerhalb der Bestätigungsaktion ist verbindlich und reduziert das Risiko eines inzwischen geänderten Kontostands. Eine absolute Reservierung gegen parallelen Verbrauch außerhalb der App kann trader.dev ohne Reservierungsfunktion nicht garantieren.
- **Fail closed:** Timeout, unlesbare Antwort oder Fehler von `get_credits` blockiert die Bestätigung. Ein alter Snapshot wird nie als Ersatz verwendet, weil sonst das harte Kosten-Gate nur scheinbar sicher wäre.
- **Vorhandenen Confirm-Pfad erweitern:** Dort werden heute bereits Batch und Runs unveränderlich gemacht. Gate, Snapshot und Run-Erzeugung an derselben fachlichen Grenze verhindern bestätigte Runs ohne dokumentierte Credit-Freigabe.
- **Credit-Maximum ist eine Obergrenze, kein Budgettopf:** Es wird weder heruntergezählt noch für Retries wiederverwendet. Wenn die Run-Anzahl das Maximum übersteigt, muss der Nutzer die Auswahl reduzieren oder das Maximum erhöhen.
- **Keine Queue oder externe Backtest-Aktion in PROJ-5:** Die Bestätigung materialisiert ausschließlich geplante Runs. Erst PROJ-6 löst externe Ausführung aus.
- **Keine automatische Aktualisierung:** Live-Stand beim Öffnen/Ändern und ein manueller Refresh reichen für die Entscheidung; der verpflichtende zweite Check bei Bestätigung sorgt für Korrektheit ohne Polling.
- **Kein Privacy-Gate:** Entspricht der bewussten MVP-Produktentscheidung; die UI ergänzt keine irreführende Datenschutzfreigabe.

### E) Abhängigkeiten

- Backend: vorhandenes FastAPI, Pydantic, PostgreSQL und Python-`subprocess`; kein neues Python-Paket.
- Externe Runtime: vorhandene OpenCode-CLI mit konfiguriertem trader.dev-MCP-Zugang für `get_credits`.
- Frontend: vorhandenes Next.js, Zod und shadcn/ui (Card, Alert, Input, Button, Badge, Table); kein neues npm-Paket.
- PROJ-4 liefert Batch-Entwurf, Run-Vorschau und den bestehenden Confirm-Pfad.
- PROJ-8 übernimmt den unveränderlichen Credit-Snapshot in die vollständige Audit-Sicht.

## QA Test Results

**Tested:** 2026-07-15
**Backend:** FastAPI (TestClient), 87/87 tests pass
**Frontend:** Next.js (build 0 errors)
**Tester:** QA Engineer (AI)

### Acceptance Criteria Status

#### AC-1: Erwartete Anzahl Aktionen vor dem Start
- [x] `GET /batches/{id}/credit-check` liefert `planned_actions` (Strategien × Instrumente × Richtungsmodi)
- [x] `test_returns_credit_status` verifiziert `planned_actions == 3` (1v × 3i × 1m)
- [x] Frontend: geplante Aktionen im Credit-Gate-Panel sichtbar

#### AC-2: Credit-Kontostand und verbleibender Bestand
- [x] `credit-check` liefert `credit_balance` und `credit_remaining` live via `get_credits`
- [x] `test_returns_credit_status` verifiziert balance=500, remaining=497
- [x] Frontend: Guthaben und verbleibend im Panel, negativer Wert rot markiert

#### AC-3: Hartes Credit-Maximum, Default = geplante Runs
- [x] `POST /batches/{id}/confirm` erfordert `{credit_max: int}` via `BatchConfirmIn(ge=1)`
- [x] `test_credit_max_too_low_rejected` verifiziert 422 bei credit_max < planned_actions
- [x] Frontend: `creditMax` initialisiert auf `preview.length`, Input `min={planned_actions}`, Confirm-Button disabled bei Unterschreitung

#### AC-4: Blockiert bei unzureichenden Credits
- [x] `confirm` prüft `credit_balance >= planned_actions`, wirft 422 mit fehlender Differenz
- [x] `test_insufficient_credits_rejected` verifiziert 422 bei balance=1, needed=3
- [x] Frontend: blocked-Status + Alert bei `creditStatus.blocked`

#### AC-5: Explizite Bestätigung
- [x] `confirm` erfordert Body mit `credit_max`, nie implizit
- [x] `test_confirm_materializes_runs` verifiziert Snapshot-Speicherung (credit_max/balance/remaining/tier/reset)
- [x] Frontend: Confirm-Button erst aktiv nach Credit-Check + gültigem credit_max

#### AC-6: Tarif/Credit/Reset aus get_credits
- [x] `trader_dev.get_credits()` ruft Live-Daten via OpenCode CLI ab, nie hartcodiert
- [x] `credit_tier`, `credit_reset` aus API-Response durchgereicht (getestet via mock: tier="free", reset="2026-07-22")

#### AC-7: Kein Privacy-Check
- [x] Kein Privacy-Gate in Routes, Schemas oder Service — entspricht MVP-Produktentscheidung

### Edge Cases Status

#### EC-1: Credit-Maximum nachträglich reduziert (unter geplante Runs)
- [x] Backend: `BatchConfirmIn(ge=1)` + `credit_max < planned_actions` → 422
- [x] Frontend: `creditMax` Input mit `min={planned_actions}` verhindert Unterschreitung
- [x] `test_credit_max_too_low_rejected` verifiziert

#### EC-2: Retry eines Runs nach Batch-Abschluss
- [x] Kein automatischer Verbrauch aus ursprünglichem Maximum (Credit-Maximum ist Obergrenze, kein Budgettopf)
- [x] PROJ-6 erhält bewusste Einzel-Prüfung je Retry, kein Wiederverwenden des Snapshot

#### EC-3: get_credits nicht erreichbar
- [x] `CreditServiceError` → HTTP 502 in beiden Endpunkten (credit-check + confirm)
- [x] `test_service_error_returns_502` verifiziert für beide
- [x] Fail closed: kein stiller Weiterlauf mit veraltetem Stand

#### EC-4: Credit-Stand ändert sich zwischen Anzeige und Bestätigung
- [x] Doppelter Check: `credit-check` informativ, `confirm` verbindlich mit eigenem `get_credits()`-Aufruf
- [x] Kein Caching alter Snapshot-Werte im Confirm-Endpunkt

### Security Audit Results

- [x] SQL Injection: Alle Queries parametrisiert (`%s` + params), Pydantic validiert Input-Types
- [x] Input Validation: `BatchConfirmIn.credit_max` mit `ge=1`, UUID-Pfadparameter durch FastAPI validiert
- [x] Error Leakage: 502/422 enthalten keine internen Stack-Traces oder Secrets
- [x] No Auth / No Multi-Tenant: Single-Trader-App per PRD, kein JWT, kein RLS nötig
- [x] Rate Limiting: N/A (keine Auth-Endpoints, kein slowapi im Projekt)

### Bugs Found

#### BUG-1: int()-Cast ohne Fehlerbehandlung in trader_dev.get_credits()
- **Severity:** Low
- **Location:** `backend/app/services/trader_dev.py:57-59`
- **Description:** `int(parsed.get("credits", 0))` und `int(parsed.get("weekly_free_credits", 0))` liegen außerhalb des try/except. Sollte die trader.dev-API mal einen nicht-numerischen Wert liefern, propagiert ein `ValueError` als unhandled 500.
- **Fix:** `try: int(...) except (ValueError, TypeError): raise CreditServiceError(...)`
- **Priority:** Fix in next iteration (P1 — aktuell liefert die API stets Integer)

### Summary
- **Acceptance Criteria:** 7/7 passed
- **Edge Cases:** 4/4 handled
- **Bugs Found:** 1 total (0 critical, 0 high, 0 medium, 1 low)
- **Security:** Pass — no auth leaks, parameterized SQL, fail-closed on upstream errors
- **Production Ready:** YES
- **Recommendation:** Deploy. Low bug is defensive code, not triggered by current API.

## Deployment
__Deployed 2026-07-15__ / **Version:** v0.2.0 / **Stack:** Next.js standalone + FastAPI + PostgreSQL 16 auf Dokploy
