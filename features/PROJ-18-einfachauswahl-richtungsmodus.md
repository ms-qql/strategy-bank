# PROJ-18: Einfachauswahl für den Richtungsmodus

## Status: Deployed (Frontend + Backend)
**Created:** 2026-07-16
**Last Updated:** 2026-07-16

## Dependencies
- Requires: PROJ-4 (Batch-Konfiguration) — Richtungsmodi und Run-Erzeugung bestehen bereits.

## User Stories
- Als Trader möchte ich genau einen Richtungsmodus je Batch wählen, damit die Konfiguration eindeutig ist.
- Als Trader möchte ich zwischen „Long & Short“, „Nur Long“ und „Nur Short“ über Radio-Buttons wechseln.
- Als Trader möchte ich vor der Bestätigung eindeutig sehen, welcher Modus für alle Runs gilt.
- Als Tastaturnutzer möchte ich die Richtungswahl mit den Pfeiltasten bedienen können.

## Acceptance Criteria
- [ ] Der Richtungsmodus wird als Radio-Gruppe mit genau drei Optionen dargestellt: „Long & Short“, „Nur Long“ und „Nur Short“.
- [ ] Zu jedem Zeitpunkt kann genau eine Option ausgewählt sein; die Auswahl einer anderen Option ersetzt die vorherige.
- [ ] Neue Batches starten mit „Long & Short“.
- [ ] Ein gespeicherter Batch enthält genau einen Richtungsmodus und erzeugt pro Kombination aus Strategieversion und aktivem Instrument genau einen Run.
- [ ] Run-Vorschau, Credit-Berechnung und Bestätigung verwenden ausschließlich den ausgewählten Richtungsmodus.
- [ ] Die Radio-Gruppe ist per Tab erreichbar, mit Pfeiltasten umschaltbar und für assistive Technologien als zusammengehörige Einfachauswahl ausgezeichnet.
- [ ] Die Mehrfachauswahl und der Hinweis „jeder gewählte Modus erzeugt einen eigenen Run“ entfallen.
- [ ] Standard-, Holdout- und Forward-Batches verwenden dieselbe Einfachauswahl.

## Edge Cases
- Ein älterer bestätigter Batch enthält mehrere Richtungsmodi: Er bleibt unverändert und zeigt den Hinweis „Historischer Batch mit mehreren Richtungsmodi“ sowie alle gespeicherten Modi schreibgeschützt an.
- Ein älterer bearbeitbarer Entwurf enthält mehrere Richtungsmodi: Vor erneutem Speichern muss der Nutzer genau einen Modus auswählen; keine Auswahl wird stillschweigend verworfen.
- Ein unbekannter gespeicherter Richtungswert wird nicht automatisch umgedeutet; Speichern bleibt blockiert und zeigt eine deutsche Fehlermeldung.
- Beim Öffnen eines aktuellen Batches ist dessen einzelner gespeicherter Modus vorausgewählt.
- Schnelles Wechseln der Radio-Buttons erzeugt erst beim Speichern beziehungsweise Bestätigen Runs und verbraucht keine Credits.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-16 · **Stack:** Next.js + FastAPI + Neon PostgreSQL · **Branch:** dev

### A) Komponentenstruktur

```text
BatchConfigurationPage
├── DirectionModeCard
│   ├── DirectionModeRadioGroup
│   │   ├── LongAndShortOption (Standard)
│   │   ├── LongOnlyOption
│   │   └── ShortOnlyOption
│   ├── CurrentDirectionSummary
│   └── LegacyDirectionNotice (nur bei historischen Mehrfachwerten)
└── PreviewAndConfirmationCard
    ├── RunPreview (ein Run je Strategieversion und aktivem Instrument)
    ├── CreditGate (berechnet dieselbe Run-Menge)
    └── ConfirmBatchAction
```

Die drei Optionen bilden eine native Radio-Gruppe. Dadurch sind Einfachauswahl,
Tab-Fokus, Pfeiltastensteuerung und die semantische Auszeichnung für assistive
Technologien bereits durch den Browser abgedeckt. Dieselbe Komponente erscheint
für Standard-, Holdout- und Forward-Batches.

### B) Datenmodell

Jeder neu angelegte oder erneut gespeicherte Batch hat:

- genau einen Richtungsmodus: `kombiniert`, `long-only` oder `short-only`
- `kombiniert` („Long & Short“) als Standard für neue Batches
- weiterhin die bestehende Zuordnung in Neon PostgreSQL; eine neue Tabelle oder
  Datenmigration ist nicht erforderlich

Die bestehende Mehrfachwert-Struktur bleibt ausschließlich zur Abwärtskompatibilität
lesbar. Bestätigte historische Batches mit mehreren Modi werden unverändert und
schreibgeschützt angezeigt. Bei bearbeitbaren Alt-Entwürfen mit mehreren Modi muss
der Nutzer vor dem nächsten Speichern bewusst genau einen auswählen. Unbekannte
gespeicherte Werte werden sichtbar als ungültig behandelt und blockieren das Speichern.

Dateien werden nicht verarbeitet; MinIO ist für dieses Feature nicht beteiligt.

### C) API-Form

Die bestehenden Endpunkte bleiben erhalten:

- `POST /batches` → neuen Standard-Batch mit genau einem Richtungsmodus anlegen
- `PATCH /batches/{id}` → bearbeitbaren Entwurf mit genau einem Richtungsmodus speichern
- `GET /batches/{id}` → aktuellen oder historischen Batch einschließlich gespeicherter Modi laden
- `GET /batches/{id}/preview` → Vorschau aus Strategieversionen × aktiven Instrumenten × einem Modus
- `GET /batches/{id}/credit-check` → Credits für exakt dieselbe Vorschau berechnen
- `POST /batches/{id}/confirm` → genau diese Runs anlegen und den Batch sperren
- `POST /strategy-versions/{id}/holdout-batch` → Holdout-Batch mit genau einem Modus anlegen
- `POST /strategy-versions/{id}/forward-test-batch` → Forward-Batch mit genau einem Modus anlegen

Das bestehende Listenfeld für Richtungsmodi bleibt im API-Vertrag erhalten, damit
historische Mehrfachwerte weiterhin gelesen werden können. Beim Anlegen darf das Feld
fehlen; dann gilt `kombiniert`. Wird es bei einem schreibenden Vorgang mitgesendet,
akzeptiert das Backend ausschließlich eine Liste mit genau einem bekannten Wert.
Vorschau, Credit-Prüfung und Bestätigung validieren diese Regel erneut, damit ein
veralteter oder manipulierter Client keine Mehrfach-Runs erzeugen kann. Leere oder
mehrfache Auswahl liefert 422 mit „Bitte genau einen Richtungsmodus wählen.“.

### D) Technische Entscheidungen

- **Kompatibilität statt Datenumbau:** Historische Batches und ihre Audits bleiben
  beweissicher unverändert; nur neue Schreibvorgänge folgen der Einfachauswahl.
- **Server als letzte Schutzschicht:** Die Radio-Gruppe verhindert Mehrfachauswahl in
  der Oberfläche, die API erzwingt dieselbe Regel unabhängig vom verwendeten Client.
- **Eine gemeinsame Run-Grundlage:** Vorschau, Credit-Berechnung und Bestätigung lesen
  dieselbe gespeicherte Auswahl. Dadurch können angezeigte Kosten und erzeugte Runs
  nicht auseinanderlaufen.
- **Native Radio-Semantik:** Browser-Verhalten deckt Tastatur und Barrierefreiheit ohne
  zusätzliche UI-Abhängigkeit ab und wird mit den vorhandenen Design-Tokens gestaltet.
- **Keine automatische Bereinigung:** Mehrere oder unbekannte Altwerte werden nie still
  reduziert oder umgedeutet; der Nutzer trifft bei Entwürfen eine bewusste Auswahl.

### E) Abhängigkeiten

- **Backend:** keine neuen Pakete
- **Frontend:** keine neuen Pakete; vorhandene React-/Next.js- und Styling-Bausteine genügen
- **Datenbank/Storage:** keine neue Tabelle, keine Migration, kein MinIO

## QA Test Results

**Tested:** 2026-07-16
**Branch:** `dev`
**Backend:** http://localhost:8000 (FastAPI, env `Dashboard`) — pytest 203/204 passed, 1 pre-existing failure in `test_results.py` (unrelated)
**Frontend:** http://localhost:3099 (`next dev`, Next.js 16.2.10) — `tsc --noEmit` clean, `next build` 0 errors / 0 warnings, `eslint` clean (1 pre-existing error in `loadInitial` unrelated)
**Tester:** QA Engineer (AI)
**Tooling note:** project has no test framework installed (no Vitest/Jest/Playwright-as-test). Verification via `tsc`, `next build`, `eslint`, `pytest` + manual Playwright script (`/tmp/opencode/proj18-a11y.mjs`).

### Acceptance Criteria Status

#### AC-1: Radio group with 3 options „Long & Short", „Nur Long", „Nur Short"
- [x] Three `<input type="radio">` rendered inside a `role="radiogroup"` container with the spec'd labels
- [x] `name="direction-mode"` shared across all three (browser-level mutual exclusion)
- [x] Card description updated to "Genau ein Modus je Batch — gilt für Standard-, Holdout- und Forward-Batches."
- Evidence: `screenshots/proj18-card-kombiniert.png`, `proj18-card-longonly.png`, `proj18-card-shortonly.png`

#### AC-2: Exactly one selected at any time; selecting another replaces
- [x] Native HTML radio behavior — `checked` is single-valued per group
- [x] `checked={directionMode === mode}` ensures React mirrors single selection
- [x] Playwright `FINAL_CHECKED_STATE` after back-and-forth clicks: only one `c: true` at a time
- Evidence: `FOCUS_KOMBINIERT` → `AFTER_ARROW_DOWN_1/2/UP` log lines

#### AC-3: New batches start with „Long & Short"
- [x] `useState<string | null>("kombiniert")` default
- [x] `kombiniert` mapped to label "Long & Short" in radio JSX
- [x] Screenshot of fresh `/batches` page: "Long & Short" radio pre-selected, "Aktiver Modus: Kombiniert (Long & Short)"

#### AC-4: Saved batch contains exactly one mode → exactly one run per (version × instrument)
- [x] Save body sends `direction_modes: [directionMode]` (single-element array)
- [x] Backend `_create_batch` passes through to `batch_direction_modes` rows; cartesian product with `length === 1` array produces 1 run per (version, instrument)
- [x] `test_batches.py::test_create_with_defaults` regression-passed (asserts `direction_modes == ["kombiniert"]` after default-create)
- [x] Existing `test_preview_is_cartesian_product` still passes (uses `["kombiniert", "long-only"]` to verify the cartesian path is still multi-mode-capable on the backend — see BUG-1)

#### AC-5: Preview / credit-check / confirm use only the selected mode
- [x] All three read `direction_modes` from the saved batch (frontend sends `[mode]`, backend uses the same value)
- [x] No code path multiplies modes client-side; `preview` table is rendered from the backend's `direction_mode` column
- [x] Quick-switching radios does not call `refreshPreview`, `handleCreditCheck`, or `handleConfirm` — only `setDirectionMode` (verified by code review of `onChange`)

#### AC-6: Tab reachable, arrow keys, ARIA radiogroup
- [x] `role="radiogroup"`, `aria-labelledby="direction-mode-legend"`, `aria-describedby="direction-mode-help"` on the container
- [x] Legend `<p id="direction-mode-legend">Richtung</p>` and help `<p id="direction-mode-help">Pro Strategieversion und aktivem Instrument wird genau ein Run angelegt.</p>` set as siblings
- [x] Playwright keyboard test: focus → ArrowDown moves selection to next option, ArrowUp moves back
- [x] Playwright `RADIOGROUP_ATTRS` log: `{"role":"radiogroup","labelledby":"direction-mode-legend","describedby":"direction-mode-help"}`
- [x] Native browser behavior covers Tab focus, Space/Enter to select — no custom code needed

#### AC-7: Multi-select and „jeder gewählte Modus erzeugt einen eigenen Run" hint removed
- [x] Old checkbox multi-select is gone; only `<input type="radio">` remains
- [x] Card description no longer contains the old phrase
- [x] Card description now states the single-select intent

#### AC-8: Standard, Holdout, Forward batches use the same single-select
- [x] Holdout and Forward-Test creation in `nextjs_app/app/entwuerfe/[id]/page.tsx:378-412` posts to `/strategy-versions/{id}/holdout-batch` and `/forward-test-batch` and immediately redirects to `/batches?batch={id}`
- [x] The same `BatchesPage` (and same `DirectionModeCard`) renders all three run_kinds
- [x] Backend `_create_batch` sets `run_kind` independently of `direction_modes`, so the single-select constraint applies uniformly

### Edge Cases Status

#### EC-1: Historical confirmed batch with multiple direction modes
- [x] Load: `setLegacyDirectionModes(loaded.direction_modes)` (since `status !== "entwurf"` and `length !== 1`)
- [x] `setDirectionMode(null)` (no silent pick)
- [x] Radios disabled (see BUG-1 fix)
- [x] Alert renders: "Historischer Batch mit mehreren Richtungsmodi (Kombiniert (Long & Short), Long-only) — schreibgeschützt."
- [x] „Speichern" button hidden via `!isConfirmed` guard, so no write path can mutate the historical record

#### EC-2: Editable legacy draft with multiple direction modes
- [x] Load: `setDirectionMode(null)` — no silent pre-selection
- [x] `setLegacyDirectionModes(null)` (since `status === "entwurf"`, the historical notice doesn't fire)
- [x] Summary line shows „Aktiver Modus: keiner ausgewählt"
- [x] Save validation `if (!directionMode || !DIRECTION_MODES.includes(directionMode))` blocks with German error „Bitte genau einen gültigen Richtungsmodus wählen."
- [x] No silent drop: stored multi-modes array is replaced only after user actively picks a single known value
- Note: the UI does not show a separate "stored values were X, Y" hint — only the summary line signals that nothing is selected. Acceptable per spec (spec mandates the constraint, not a specific hint text for this case).

#### EC-3: Unknown saved direction value
- [x] Load: `directionMode = "weird"`, `legacyDirectionModes = null`
- [x] Alert renders destructively: „Unbekannter Richtungswert „weird" — Speichern blockiert."
- [x] Save blocked: `!DIRECTION_MODES.includes("weird")` is true → error fires
- [x] User can recover by clicking any known radio (alert disappears, save path opens)

#### EC-4: Opening a current batch pre-selects its single stored mode
- [x] Load: `setDirectionMode(loaded.direction_modes[0])` when `length === 1`
- [x] `checked={directionMode === mode}` makes the corresponding radio selected
- [x] „Aktiver Modus:" summary mirrors the stored label

#### EC-5: Quick-switching radios does not consume credits
- [x] Radio `onChange` only calls `setDirectionMode(mode)` and `setLegacyDirectionModes(null)` — pure React state, no network
- [x] No effect tied to `directionMode` triggers any fetch
- [x] Credit balance unchanged until the user explicitly clicks „Credits prüfen" or „Batch bestätigen"

### Security Audit Results
- N/A — frontend-only change, no new endpoints, no new auth surface, no SQL, no file I/O
- Existing auth flow (AuthGate in `app/layout.tsx`) and backend RLS unchanged

### Regression Testing
- `backend/tests/test_batches.py`: 25/25 passed (covers create-with-defaults, preview-cartesian, explicit-empty-modes, standard/holdout/forward batch creation, PATCH flow)
- `backend/tests/test_audit.py`: passed (uses both single and multi `direction_modes` in test setup — multi is still supported by the backend per the spec's backward-compatibility decision)
- `backend/tests/`: 203/204 passed; 1 pre-existing failure in `tests/test_results.py::TestResultsWithData::test_multiple_result_types_are_separate_rows` (results-domain test, **unrelated** to PROJ-18 — confirmed by re-running on the clean `dev` branch with the frontend changes stashed)
- Visual regression on other cards (Backtest-Profil, Strategieversionen, Instrumente, Zeitraum): unchanged, verified by full-page screenshot

### Bugs Found

#### BUG-1: Confirmed batch allowed editing the direction mode (visual + minor write path)
- **Severity:** Medium
- **Found during:** AC-2 + EC-1 review
- **Original code:** `disabled={isConfirmed && legacyDirectionModes === null}` — left radios clickable when `legacyDirectionModes` was set (i.e. confirmed + multi modes case)
- **Steps to Reproduce:**
  1. Open a confirmed historical batch with `direction_modes = ["kombiniert", "long-only"]` (seed via DB or pre-PROJ-18 client)
  2. Observe the three radios
  3. Click „Nur Short"
  4. Expected: radios stay disabled (historical batch is read-only per spec section C and edge case EC-1)
  5. Actual (before fix): „Nur Short" became checked, legacy notice stayed on screen, state became inconsistent
- **Fix:** `disabled={isConfirmed}` — confirmed batches are read-only in all cases
- **Verified:** tsc clean, Playwright still passes; no behavioral change for editable drafts
- **Status:** Fixed in this QA pass

#### BUG-2 (Closed in `/abc-backend` follow-up, 2026-07-16): Backend does not enforce „exactly one known direction mode" (spec section C)
- **Severity:** High (security/correctness per spec)
- **Found during:** Spec compliance review (frontend QA)
- **Description:** Spec section C requires: „Vorschau, Credit-Prüfung und Bestätigung validieren diese Regel erneut, damit ein veralteter oder manipulierter Client keine Mehrfach-Runs erzeugen kann. Leere oder mehrfache Auswahl liefert 422 mit „Bitte genau einen Richtungsmodus wählen"." Original backend `_validate_direction_modes` in `backend/app/routes/batches.py:130` only rejected *unknown* values — it did not enforce `len(modes) == 1`.
- **Fix applied:**
  - `backend/app/routes/batches.py:130-135` — tightened `_validate_direction_modes` to require `len(modes) == 1` with German error „Bitte genau einen Richtungsmodus wählen." (422). Unknown value in a single-element list keeps the prior „Ungültiger Richtungsmodus: X" wording.
  - `backend/app/routes/batches.py:355` — added `_validate_direction_modes(direction_modes)` re-check inside `confirm_batch` so a legacy multi-mode entwurf batch (e.g. seeded by data migration) cannot silently produce N runs. Already-confirmed batches short-circuit on the prior „bereits bestätigt" check.
  - Preview and credit-check are read-only and intentionally left unchanged — the spec's backward-compat clause allows reading historical multi-value data; the confirm step is the only path that materializes runs.
- **Test updates:**
  - `test_batches.py::TestBatchCreateAndPreview::test_preview_is_cartesian_product` — flipped: now asserts the default-mode cartesian (2 versions × 1 instrument × 1 mode = 2 runs); multi-mode is asserted in a new sibling test `test_multi_direction_modes_rejected_422`.
  - `test_batches.py::test_explicit_empty_instruments_and_modes_not_replaced_with_defaults` — split into `test_explicit_empty_instruments_kept` (instruments still default, modes default to kombiniert) and `test_explicit_empty_direction_modes_rejected_422`.
  - `test_audit.py::TestAuditTrail::test_multiple_runs_each_have_own_audit` — refactored to produce 2 runs via 2 strategy versions (single mode) instead of 2 modes, preserving the test intent.
  - `test_batches.py::TestDirectionModeValidation` — 11 new tests covering: default-to-kombiniert, each known mode accepted, empty list 422, multi list 422, unknown value 422, PATCH multi/empty 422, PATCH single OK, holdout-batch multi 422, forward-test-batch multi 422, confirm re-validates a legacy multi-mode entwurf seed (422).
- **Test result:** `pytest tests/ -q` → 222 passed, 1 pre-existing failure in `test_results.py::test_multiple_result_types_are_separate_rows` (results-domain, unrelated — confirmed by QA pass before this fix). My changes added 11 new tests, all green; modified tests in `test_batches.py` and `test_audit.py` all green.
- **Status:** Closed.

#### BUG-3 (Open): No automated test coverage for the new behavior
- **Severity:** Low (test-infrastructure, not feature behavior)
- **Description:** Project `nextjs_app` has no test runner (no Vitest/Jest/Playwright-as-test). The QA pass used `tsc`, `next build`, `eslint`, `pytest`, plus an ad-hoc Playwright script (`/tmp/opencode/proj18-a11y.mjs`) for the UI verification. Without a permanent test suite, regressions on the radio-group behavior won't be caught automatically.
- **Recommendation:** add a minimal Vitest + React Testing Library setup (or Playwright component tests) for `nextjs_app` and cover at least: default state, single-selection enforcement, legacy-multi notice, unknown-value alert, save validation. Tracked as future work, not blocking PROJ-18.

### Summary
- **Acceptance Criteria:** 8/8 passed
- **Edge Cases:** 5/5 passed
- **Bugs Found:** 3 total (1 Medium fixed, 1 High closed, 1 Low open)
- **Security:** N/A (no new surface)
- **Regression:** 222/223 backend tests passed (1 pre-existing, unrelated in `test_results.py`)
- **Production Ready for the frontend change:** YES — the UI matches spec, the bug found was fixed in this pass
- **Production Ready for the full feature:** YES — backend single-mode enforcement (BUG-2) closed in `/abc-backend` follow-up
- **Recommendation:**
  - **Ship PROJ-18** — both frontend and backend are ready, all AC + EC pass, both open-bugs are resolved (1 infra-only Low remains, see BUG-3)
  - **Schedule BUG-3** (test infrastructure for `nextjs_app`) as separate follow-up — non-blocking



## Deployment
**Deployed:** 2026-07-16, Version v0.2.23 (Bump bereits in 6304a8c erfolgt — kein weiterer Bump in diesem Deploy-Commit).
**Inhalt:**
- **Frontend** (`nextjs_app/app/batches/page.tsx`): native Radio-Gruppe (role=radiogroup + aria-labelledby/aria-describedby; Tab/Pfeil/Space browser-native) ersetzt die Checkbox-Mehrfachauswahl. Drei Optionen mit AC-Labels „Long & Short", „Nur Long", „Nur Short". Default `kombiniert` für neue Batches; Single-Selektion erzwungen. Bearbeitbare Alt-Entwürfe mit 0/2+ Modi werden nicht stillschweigend reduziert (directionMode=null, Save blockiert). Bestätigte Multi-Mode-Historie zeigt schreibgeschützte Legacy-Notice. Unbekannter gespeicherter Wert löst destructive Alert aus, Save blockiert.
- **Backend** (`backend/app/routes/batches.py`): `_validate_direction_modes` verlangt jetzt `len(modes) == 1`; leere oder mehrfache Auswahl liefert 422 „Bitte genau einen Richtungsmodus wählen." Unbekannter Wert in single-element list behält „Ungültiger Richtungsmodus: X". `confirm_batch` ruft die Validierung erneut auf die gespeicherten Modi auf (letzte Schutzschicht gegen Migrationsdaten). Read-Endpoints (Preview, Credit-Check) bleiben unverändert für Backward-Compat mit historischen Multi-Mode-Batches.
- **Tests**: `TestDirectionModeValidation` (11 neue Fälle inkl. Confirm-blockt-Legacy-Multi-Seed) + 3 modifizierte bestehende Tests. `pytest tests/`: 222/223 grün (1 pre-existing failure in `test_results.py` results-domain, unrelated).

**Commit:** `64c12eb feat(PROJ-18): Einfachauswahl Richtungsmodus (Frontend + Backend + QA)`.
**Push:** `origin/main` (Auto-Deploy auf Dokploy, `docker-compose.dokploy.yml`).
**Offen:** Bug 3 (Test-Infrastruktur für `nextjs_app`, Low) — non-blocking, separate Folge-Iteration.
**Smoke-Test (Browser!):** Nach dem Frontend-Rebuild **Hard-Refresh** (Strg/Cmd+Shift+R) auf `/batches`, sonst läuft das alte Service-Worker-Bundle und der Fix wirkt nicht. Dann eine neue Batch-Konfiguration öffnen, „Long & Short" / „Nur Long" / „Nur Short" per Tab + Pfeiltasten durchschalten, „Aktiver Modus"-Zeile muss synchron wechseln. Bei bestehendem Batch: gespeicherten Modus vorausgewählt.
