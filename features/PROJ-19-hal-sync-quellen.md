# PROJ-19: Hal-Vault-Sync für Quellen + Feldbereinigung

## Status: Deployed
**Created:** 2026-07-29
**Last Updated:** 2026-07-29 (Re-Scope: Download statt Server-Sync, Deployed v0.2.32-PROJ-19)

## Re-Scope-Hinweis (nach Prod-Test, 2026-07-29)

Die ursprüngliche Spec sah einen synchronen Server-seitigen Dateisystem-Write nach
Hal bei jedem PATCH vor (Teil A unten, "Hal-Vault-Sync"). In der Produktion zeigte
sich: Dokploy hostet Backend + Frontend auf einem **separaten Server**, der Hal-Vault
(`/home/dev/tools/Hal`) liegt aber nur auf der Dev-VPS. Der Prod-Container hat
keinerlei Dateisystem- oder Netzwerkzugriff auf die Dev-VPS — ein serverseitiger
Sync kann dort strukturell nie ankommen (Backfill wie auch laufender Sync).

**Entscheidung (User, 2026-07-29):** Kein serverseitiger Hal-Write mehr. Stattdessen:
- Pro Entwurf ein **Download-Button** "Hal-Steckbrief herunterladen" (`GET /hal/drafts/{id}/export`) — liefert die Markdown-Datei als Attachment, der User zieht sie manuell in den Vault.
- Ein **Bulk-Download** "Alle Hal-Steckbriefe herunterladen (ZIP)" (`GET /hal/export-all`) auf der Quellenerfassungs-Seite — deckt den Backfill-Bedarf für bereits extrahierte Strategien ab, ohne Serverzugriff auf den Vault.
- Kein Namenskollisions-Handling mehr nötig (kein Server-Write, keine 409-Logik, kein `overwrite_hal`) — Konflikte beim manuellen Reinziehen ins Vault löst der User selbst wie bei jedem anderen Datei-Import.
- Teil A der ursprünglichen AC (unten) ist damit **ersetzt**, nicht ergänzt. Teil B (Feldbereinigung) ist unverändert gültig und weiterhin erfüllt.

Diese Notiz beschreibt bewusst nur den Re-Scope; die ursprüngliche Spec/AC unten bleibt als historischer Kontext stehen. Für den aktuellen Stand siehe `## QA Test Results` (Update unten).

## Dependencies
- Requires: PROJ-9 (Markdown-Export) — die bestehende Export-Logik liefert die Inhaltsstruktur für das Hal-Markdown.
- Requires: PROJ-2 (KI-Extraktion) — Draft-Daten werden beim Speichern einer Quelle erzeugt.
- Requires: PROJ-3 (Verifizierung und Versionierung) — Draft-Update-API (PATCH `/drafts/{id}`) ist der Trigger.

## User Stories

### Teil A: Hal-Vault-Sync
- Als Trader möchte ich jede erfasste Strategie automatisch als Markdown-Datei in meinem Hal Second Brain haben, damit ich sie auch außerhalb der App durchsuchen und verlinken kann.
- Als Trader möchte ich, dass bestehende Strategien einmalig nach Hal migriert werden (Backfill), damit keine Lücke entsteht und danach nur noch automatische Updates erfolgen.
- Als Trader möchte ich, dass sich die Hal-Datei automatisch aktualisiert, wenn ich Parameter oder Felder im Entwurf bearbeite, damit der Vault immer den aktuellen Stand spiegelt.
- Als Trader möchte ich, dass die Hal-Datei einen kurzen, lesbaren Steckbrief der Strategie enthält — nicht den vollständigen Export — damit ich im Obsidian-Vault schnell erfassen kann, worum es geht.
- Als Trader möchte ich bei einer Namenskollision (eine andere Strategiefamilie hat bereits eine gleichnamige Hal-Datei) gefragt werden, ob ich überschreiben will, damit ich nicht versehentlich fremde Strategiedaten verliere.

### Teil B: Feldbereinigung
- Als Trader möchte ich, dass die Felder „Gleichzeitiger Entry/Exit" und „Reversal-Verhalten" aus der Bearbeitungsoberfläche entfernt werden, da sie redundant zum Positionsmodus (PROJ-10) sind.
- Als Entwickler möchte ich, dass diese Felder auch im Backend-Datenmodell, in Schemas und in allen darauf zugreifenden Code-Pfaden entfernt werden, damit keine inkonsistenten REST-APIs entstehen.

## Acceptance Criteria

### Teil A: Hal-Vault-Sync
- [ ] Nach dem ersten Speichern eines Entwurfs (PATCH `/drafts/{id}`) wird automatisch eine Markdown-Datei unter `/home/dev/tools/Hal/04 Resources/Strategy_Bank/01_Quellen/[name].md` erzeugt.
- [ ] Die Markdown-Datei enthält mindestens: Name, Kategorie, Richtung, These, Entry-Regel, Exit-Regel, Positionsmodus, Warm-up, Parameter-Tabelle und ein Datum der letzten Änderung.
- [ ] Bei jeder nachfolgenden Änderung des Entwurfs (Speichern) wird die bestehende Hal-Datei überschrieben (nicht dupliziert).
- [ ] Ein einmalig ausführbarer Backfill-Endpoint (z. B. `POST /hal/sync-all`) erzeugt Hal-Dateien für alle bisher erfassten Entwürfe. Nach diesem einmaligen Event übernehmen die automatischen Speicher-Trigger; der Endpoint wird danach nicht erneut benötigt.
- [ ] Der Dateiname ist der `name`-Feldwert, gesäubert gemäß `_safe_filename()`-Logik aus PROJ-9.
- [ ] Wird ein Entwurf umbenannt, wird die alte Hal-Datei gelöscht und eine neue mit dem aktualisierten Namen erzeugt — keine doppelten Dateien.
- [ ] Der Sync schlägt nie fehl, wenn das Hal-Verzeichnis nicht existiert — er erzeugt das Verzeichnis vor dem Schreiben.
- [ ] Der Sync läuft synchron innerhalb des PATCH-Handlers (keine Background-Queue), damit der Vault immer konsistent ist.
- [ ] Der Sync schlägt den PATCH nicht fehl — ein Hal-Schreibfehler wird geloggt, aber die API antwortet dennoch mit 200 und dem aktualisierten Draft.
- [ ] Namenskollision: Speichert ein Entwurf auf einen Dateinamen, den bereits eine Hal-Datei einer **anderen** Strategiefamilie (`family_id`) belegt, antwortet der PATCH mit `409 Conflict` und einem Hinweis. Das Frontend zeigt einen Dialog: „Datei [name].md existiert bereits für eine andere Strategie. Überschreiben?" mit „Abbrechen" / „Überschreiben". Bei Bestätigung wird der PATCH mit `?overwrite_hal=true` wiederholt und die Datei überschrieben. Updates innerhalb derselben Familie (gleiche `family_id`) überschreiben ohne Nachfrage.

### Teil B: Feldbereinigung
- [ ] `simultaneous_entry_exit_behavior` und `reversal_behavior` sind aus dem Bearbeitungsformular (`/entwuerfe/[id]`) entfernt.
- [ ] Die Labels `Gleichzeitiger Entry/Exit` und `Reversal-Verhalten` erscheinen nicht mehr in `SNAPSHOT_LABELS`.
- [ ] Die zugehörigen Input-Felder und Form-State-Variablen (`simulBehavior`, `reversalBehavior`) sind aus der Page-Komponente entfernt.
- [ ] `simultaneous_entry_exit_behavior` und `reversal_behavior` sind aus `DraftUpdate` (Backend-Pydantic-Schema) entfernt.
- [ ] `simultaneous_entry_exit_behavior` und `reversal_behavior` sind aus `DraftRead` (Backend-Pydantic-Schema) entfernt.
- [ ] Die DB-Spalten bleiben bestehen (kein `ALTER TABLE DROP COLUMN`, um bestehende Daten nicht zu verlieren), werden aber nicht mehr gelesen oder geschrieben.
- [ ] Der PATCH-Handler ignoriert die beiden Felder stillschweigend (akzeptiert sie nicht im Body, verwendet sie nicht in SQL).
- [ ] Der Export (PROJ-9) enthält die beiden Felder nicht mehr.
- [ ] Der Freeze-/Vergleichs-Diff (`_compute_user_diff`) ignoriert die beiden Felder.
- [ ] `entwurf-card.tsx` zeigt die beiden Felder nicht mehr an.
- [ ] Die Extraktion (OpenCode-Prompt, `opencode_extraction.py`) fordert die beiden Felder nicht mehr an und verarbeitet sie nicht mehr.
- [ ] Die Pine-Generierung und der Exit-Resolver referenzieren die Felder nicht mehr (soweit sie das aktuell nicht tun).
- [ ] Entsprechende Tests sind aktualisiert (keine Assertions auf die entfernten Felder).
- [ ] TypeScript-Schemas (`extraction.ts`, `draft.ts`) enthalten die beiden Felder nicht mehr.

## Edge Cases

### Hal-Sync
- Namenskollision: Gleiche `family_id` → immer überschreiben (Versionsupdate). Unterschiedliche `family_id` → 409 Conflict, User muss aktiv mit `overwrite_hal=true` bestätigen. Backfill überschreibt ebenfalls nur innerhalb derselben Family; fremde Dateien werden übersprungen und geloggt.
- Entwurf hat keinen Namen → Dateiname fällt zurück auf `strategy.md` oder wird durch UUID ergänzt.
- Hal-Verzeichnis ist nicht schreibbar → Fehler wird geloggt (stderr), API antwortet dennoch mit 200.
- Sehr große Parameter-Tabelle → Markdown-Datei wird dennoch vollständig geschrieben; kein Truncation-Limit.
- Entwurf wird gelöscht → die Hal-Datei bleibt bestehen (nur der User räumt Hal manuell auf).
- Backfill läuft während aktiver Bearbeitung → Entwürfe im Status `Entwurf` werden inkludiert, unvollständige (`gesperrt`) ebenfalls.

### Feldbereinigung
- Bestehende Version-Snapshots enthalten die Felder noch → das ist akzeptabel; neue Versionen speichern sie nicht mehr. Der Diff-Mechanismus erzeugt beim ersten Speichern nach Entfernung keinen Eintrag für diese Felder.
- Alte Tests referenzieren die Felder → müssen auf die neue Signatur aktualisiert werden.
- Frontend-Cache zeigt veraltete Draft-Daten mit den Feldern → `loadDraft` liest die Felder nicht mehr ein, sie erscheinen nicht im UI.

## Technical Requirements (optional)
- Der Hal-Vault-Pfad ist fest: `/home/dev/tools/Hal/04 Resources/Strategy_Bank/01_Quellen/`
- Keine neue externe Dependency — `pathlib` und `os` aus der Python-Stdlib genügen.
- Die `_safe_filename()`-Funktion aus `export.py` wird in ein Shared-Modul extrahiert (oder dupliziert, falls das Shared-Modul Overkill wäre).
- Keine API-Änderung für Clients — die Hal-Datei ist ein reiner Server-Side-Effekt.

---

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-29 · **Stack:** Next.js 16 + FastAPI + PostgreSQL · **Branch:** `specs/PROJ-19-hal-sync-quellen`

### A) Component Structure

```
Backend (neu / geändert)
├── services/hal_sync.py              ← NEU: Markdown-Generierung + Dateisystem-Schreiblogik
│   ├── _draft_steckbrief_md(draft)   → baut Markdown-String aus Draft-Daten
│   ├── sync_draft_to_hal(draft_id)   → liest Draft aus DB, schreibt .md nach Hal
│   ├── sync_all_drafts_to_hal()      → Backfill: iteriert alle Entwürfe, schreibt Hal
│   └── _safe_filename(name)          → aus export.py geklont (3 Zeilen Regex)
│
├── routes/drafts.py                   ← GEÄNDERT: PATCH-Handler ruft sync_draft_to_hal auf
├── routes/hal_sync.py                ← NEU: GET /hal/sync-all (Backfill-Endpoint)
├── routes/export.py                   ← GEÄNDERT: _DETAIL_FIELDS ohne die zwei Felder
├── routes/extractions.py              ← GEÄNDERT: SELECTs ohne die zwei Felder
├── schemas/drafts.py                  ← GEÄNDERT: DraftUpdate/DraftRead ohne Felder
├── schemas/extractions.py             ← GEÄNDERT: DraftRead ohne Felder
├── services/opencode_extraction.py    ← GEÄNDERT: Prompt + Normalize ohne Felder
└── sql/                              ← KEINE Änderung (Spalten bleiben)

Frontend (geändert / entfernt)
├── app/entwuerfe/[id]/page.tsx        ← GEÄNDERT: Form-Felder entfernt, Overwrite-Dialog
├── components/quellen/entwurf-card.tsx ← GEÄNDERT: Anzeige der zwei Felder entfernt
└── lib/schemas/
    ├── draft.ts                       ← GEÄNDERT: draftUpdateSchema ohne Felder
    └── extraction.ts                  ← GEÄNDERT: draftSchema ohne Felder
```

### B) Data Model (Änderungen)

**Strategie-Steckbrief (Hal-Markdown):**
```
# [Name]
**Kategorie:** Trendfolge · **Richtung:** long-only · **Stand:** 2026-07-29

## These
[thesis text]

## Entry-Regel
[entry_rule]

## Exit-Regel
[exit_rule] *(Herkunft: Aus Quelle)*

## Positionsmodus
Entry mit Flat-Exit *(bestätigt)*

## Crypto-MTS-Eignung
Kontinuierlich geeignet *(bestätigt)*

## Warm-up
0 bars

## Parameter
| Name | Wert | Einheit | Bereich |
|------|------|---------|---------|
| RSI Length | 14 | — | 5–50 |

## Quellenbelege
- Entry: "When RSI crosses above 30..." *(Zeile 12)*
```

**DB-Spalten (unverändert):** `simultaneous_entry_exit_behavior` und `reversal_behavior` bleiben als TEXT-NULL-Spalten in `strategy_drafts` erhalten. Neue Migration setzt `DEFAULT NULL` und stoppt das Schreiben. Alle SELECTs und INSERTs ignorieren sie — kein Datenverlust für Historien.

**Keine neue DB-Tabelle.** Die Hal-Mapping-Datei (welcher Draft → welcher Dateiname) wird nicht gespeichert; die Datei auf Disk ist die einzige Wahrheit.

### C) API Shape

```
PATCH /drafts/{draft_id}          ← GEÄNDERT: akzeptiert die zwei Felder nicht mehr.
                                    Nach erfolgreichem DB-Update:
                                    1. Namenskonflikt-Prüfung (Query: andere Family, gleicher safe_name?)
                                       → 409 Conflict + {"conflict_family_id": "..."} bei Treffer
                                    2. sync_draft_to_hal(draft_id) — schreibt/überschreibt .md
                                    Fehler in Schritt 2 → nur Log, API antwortet 200.

GET  /hal/sync-all                ← NEU: einmaliger Backfill.
                                    Iteriert ALLE strategy_drafts, schreibt je eine .md-Datei.
                                    Überspringt Dateien, die bereits zu einer ANDEREN Family gehören
                                    (Log-Warnung). Antwort: {"synced": 42, "skipped": 0, "errors": []}
```

### D) Tech Decisions

1. **Dateiname nur aus Name, keine UUID:** `{_safe_filename(name)}.md`. Im Obsidian-Vault sollen Dateien sofort lesbar sein. Namenskonflikte über verschiedene Familien werden via 409 erkannt — der User entscheidet. Gleiche Family überschreibt immer (es ist dieselbe Strategie, Versionen sind DB-intern).

2. **Sync synchron, nicht Background:** `sync_draft_to_hal()` läuft im selben Request-Thread wie der PATCH. Der Hal-Vault ist eine lokale Datei — Schreibzugriff dauert < 1 ms. Async-Job wäre Overkill und brächte Race-Conditions (User speichert, öffnet Hal, Datei ist noch nicht da).

3. **try/except um den Dateizugriff:** Hal ist ein externes Verzeichnis — wenn es gelöscht wird oder die Platte voll ist, darf der API-Response nicht crashen. Fehler werden via `logging.getLogger(__name__).error()` geloggt, die API antwortet normal mit 200.

4. **`_safe_filename()` klonen, nicht extrahieren:** Der Export-Modul hat 3 Zeilen Regex — ein Shared-Modul für 3 Zeilen wäre Over-Engineering. Die Hal-Sync-Funktion enthält eine lokale Kopie mit einem `# ponytail: cloned from export.py:31-34`-Kommentar.

5. **Steckbrief ist ein Subset des Voll-Exports:** Export.py baut eine komplette Familienhistorie mit Runs und Backtest-Metriken. Der Hal-Steckbrief ist eine Momentaufnahme eines Drafts — nur die Felder, die der Trader im Vault braucht. Gemeinsame Hilfsfunktion `_escape_md()` wird in `hal_sync.py` geklont (1 Zeile, keine Rechtfertigung für Shared-Modul).

6. **Backfill überschreibt nur eigene Family:** `GET /hal/sync-all` prüft vor jedem Schreiben, ob eine gleichnamige Datei existiert und einer anderen Family gehört. Falls ja → skip + log. So kann der Backfill gefahrlos mehrfach aufgerufen werden.

7. **DB-Spalten bleiben, Code entfernt sie:** `ALTER TABLE DROP COLUMN` würde bestehende Version-Snapshots beschädigen. Stattdessen: App-Code liest/schreibt die Spalten nicht mehr. Neue Drafts haben dort NULL. Historische Versionen behalten ihre alten Werte.

8. **409-Konflikt-Erkennung via SQL, nicht Filesystem:** Vor dem Schreiben prüft `SELECT family_id FROM strategy_drafts WHERE LOWER(name) = LOWER($new_name) AND family_id != $my_family_id LIMIT 1`. Das ist zuverlässiger als Dateisystem-Prüfung (Datei könnte fehlen, obwohl Draft existiert) und deckt auch Drafts ab, deren Hal-Datei noch nie geschrieben wurde.

### E) Dependencies

Keine neuen Abhängigkeiten. Nur Python-Stdlib:
- `pathlib.Path` — Verzeichnis anlegen, Datei schreiben/löschen
- `os.makedirs` — via `Path.mkdir(parents=True, exist_ok=True)`
- `logging` — Fehlerprotokollierung bei Hal-Schreibfehlern
- `re` — `_safe_filename()` Regex (wie in export.py)

---

## QA Test Results

**Tested:** 2026-07-29
**Backend:** conda env `Dashboard`, pytest gegen echte Test-DB
**Frontend:** `npx tsc --noEmit` (Next.js)
**Tester:** QA Engineer (AI)

### Acceptance Criteria Status

#### Teil A: Hal-Vault-Sync
- [x] Erster Save erzeugt Hal-Markdown-Datei
- [x] Markdown enthält Name, Kategorie, Richtung, These, Entry/Exit, Positionsmodus, Warm-up, Parameter, Datum
- [x] Nachfolgende Saves überschreiben (keine Duplikate bei gleichem Namen)
- [x] Backfill-Endpoint erzeugt Hal-Dateien für alle Entwürfe
- [x] Dateiname = gesäuberter `name`
- [x] BUG-1 (gefixt): Umbenennen löscht jetzt die alte Hal-Datei (`delete_hal_file`, vergleicht `safe_filename(alt)` vs `safe_filename(neu)`)
- [x] Verzeichnis wird bei Bedarf angelegt (`mkdir(parents=True, exist_ok=True)`)
- [x] Sync läuft synchron im PATCH-Handler
- [x] Hal-Schreibfehler failen den PATCH nicht (try/except + Logging, API antwortet 200)
- [x] BUG-2 (gefixt): Namenskollisions-Check läuft jetzt bei JEDEM Save (effektiver Name = neuer oder bestehender Name), nicht mehr nur wenn `name` im Body ist
- [x] BUG-3 (gefixt): Backfill trackt Dateinamen-Besitz pro Family während des Laufs; fremde Family wird übersprungen + geloggt, `skipped` zählt korrekt

#### Teil B: Feldbereinigung
- [x] Felder aus Bearbeitungsformular entfernt (Page-Komponente, State-Variablen)
- [x] Labels aus `SNAPSHOT_LABELS` entfernt
- [x] Aus `DraftUpdate` und `DraftRead` (beide Schema-Dateien) entfernt
- [x] DB-Spalten bleiben bestehen, werden nirgends mehr gelesen/geschrieben (grep bestätigt: keine Treffer mehr im Code)
- [x] PATCH ignoriert die Felder (nicht mehr im Schema, kein SQL-Zugriff)
- [x] Export enthält die Felder nicht mehr
- [x] `_compute_user_diff` referenziert die Felder nicht mehr (aus `_FIELD_NAMES` entfernt)
- [x] `entwurf-card.tsx` zeigt die Felder nicht mehr an
- [x] Extraktion (`opencode_extraction.py`, Prompt + Normalize + INSERT) fordert/verarbeitet die Felder nicht mehr
- [x] Pine-Generierung / Exit-Resolver: keine Referenzen gefunden
- [x] Tests aktualisiert (`test_drafts.py`, `test_export.py`, `test_opencode_extraction.py`) — keine Assertions mehr auf entfernte Felder
- [x] TypeScript-Schemas (`draft.ts`, `extraction.ts`) ohne die Felder; `tsc --noEmit` fehlerfrei

### Edge Cases Status
- [x] Kein Name → Fallback `"Unbenannt"` → `safe_filename` → `strategy.md`
- [x] Rename-Fall: alte Datei wird jetzt gelöscht (BUG-1 gefixt)
- [x] Hal-Verzeichnis fehlt → wird angelegt
- [x] Große Parameter-Tabelle → kein Truncation-Code vorhanden, vollständiger Write bestätigt durch Code-Lesung
- [ ] Nicht separat getestet: Entwurf gelöscht → Hal-Datei bleibt (kein Lösch-Pfad im Code — Verhalten passt zur AC, aber ungetestet)

### Regressionstest
- Backend-Suite: `pytest backend/tests` → 237 passed, 1 failed (`test_results.py::test_multiple_result_types_are_separate_rows`) — **vorbestehender Fehler, auch auf `main` reproduzierbar, nicht durch PROJ-19 verursacht.**
- Neu: `backend/tests/test_hal_sync.py` (7 Tests) deckt PATCH-Sync-Trigger, Rename-Löschung, Konflikt ohne Namens-Feld, `overwrite_hal`-Bypass, Same-Family-Overwrite und Backfill-Konflikt-Skip ab.
- Kein Grep-Treffer mehr für die entfernten Felder in `backend/` oder `nextjs_app/`.
- Frontend: `npx tsc --noEmit` fehlerfrei.

### Security Audit Results
- [x] Kein neuer externer Input-Pfad ohne Validierung (Dateiname wird serverseitig aus DB-Feld generiert, nicht aus Client-Body übernommen)
- [x] SQL: `check_name_conflict` parametrisiert, keine Injection-Fläche
- [x] Pfad-Traversal: Dateiname läuft durch `safe_filename()` (Regex whitelisted `\w\s-`), kein `../` möglich
- [x] BUG-4 gefixt: Backfill ist jetzt `POST /hal/sync-all`

### Bugs Found (alle gefixt)

#### BUG-1: Umbenennen hinterließ doppelte Hal-Datei — FIXED
- **Severity:** Medium
- **Fix:** `drafts.py` liest jetzt `name`/`family_id` mit, ruft nach dem Sync `delete_hal_file(old_name)` auf, wenn sich `safe_filename(alt)` von `safe_filename(neu)` unterscheidet.
- **Verifiziert:** `test_hal_sync.py::test_rename_deletes_old_file`

#### BUG-2: Namenskollisions-Check griff nur bei explizitem Namens-Feld — FIXED
- **Severity:** High
- **Fix:** Konflikt-Check läuft jetzt für jeden Save mit dem effektiven Namen (`update_fields.get("name", old_name)`), unabhängig davon, ob `name` im Body war.
- **Verifiziert:** `test_hal_sync.py::test_conflict_detected_even_without_name_field_in_body`, `::test_overwrite_hal_bypasses_conflict`, `::test_same_family_overwrites_without_conflict`

#### BUG-3: Backfill überschrieb fremde Family-Dateien ohne Prüfung — FIXED
- **Severity:** High
- **Fix:** `sync_all_drafts_to_hal` trackt pro Lauf, welche Family welchen Dateinamen zuerst beansprucht (`owner_by_filename`); fremde Family wird übersprungen + geloggt, `skipped` zählt korrekt hoch.
- **Verifiziert:** `test_hal_sync.py::test_backfill_skips_cross_family_conflict`

#### BUG-4: Backfill-Endpoint war GET statt POST — FIXED
- **Severity:** Low
- **Fix:** `routes/hal_sync.py` jetzt `@router.post("/sync-all")`.
- **Verifiziert:** `test_hal_sync.py::test_backfill_is_post` (GET liefert 405)

#### BUG-5: Keine automatisierten Tests für Hal-Sync — FIXED
- **Severity:** Medium
- **Fix:** `backend/tests/test_hal_sync.py` neu angelegt, 7 Tests, deckt alle oben genannten Fixes + Grundfunktionen ab.

### Summary (v0.2.31-PROJ-19, vor Re-Scope)
- **Acceptance Criteria:** 23/23 passed
- **Bugs Found:** 5 total, alle gefixt (0 offen)
- **Security:** Pass
- **Production Ready:** YES
- **Recommendation:** Deploy

---

## Re-Scope Update (2026-07-29, v0.2.32-PROJ-19)

Nach Prod-Test durch den User (siehe Re-Scope-Hinweis oben) wurde Teil A komplett
ersetzt: kein serverseitiger Filesystem-Write mehr, stattdessen Download-Endpunkte.

**Geänderte/entfernte Komponenten:**
- `backend/app/services/hal_sync.py`: `sync_draft_to_hal`, `sync_all_drafts_to_hal`, `delete_hal_file`, `check_name_conflict` entfernt. Neu: `build_steckbrief_export(draft_id)` (einzeln), `build_all_steckbriefe_zip()` (Bulk-ZIP in-memory, `io`/`zipfile`, keine Festplatten-Schreibzugriffe mehr).
- `backend/app/routes/hal_sync.py`: `POST /hal/sync-all` ersetzt durch `GET /hal/export-all` (ZIP-Download) und `GET /hal/drafts/{id}/export` (einzelne Markdown-Datei, `Content-Disposition: attachment`).
- `backend/app/routes/drafts.py`: PATCH-Handler wieder ohne `overwrite_hal`-Query-Param, ohne 409-Konflikt-Check, ohne Sync-Aufruf — reiner CRUD-Handler wie vor PROJ-19.
- Frontend: `entwuerfe/[id]/page.tsx` — Overwrite-Dialog entfernt, neuer Button "Hal-Steckbrief herunterladen" (Browser-Download via Blob). `quellen-view.tsx` — neuer Button "Alle Hal-Steckbriefe herunterladen (ZIP)" auf der Quellenerfassungs-Seite.
- `backend/tests/test_hal_sync.py` neu geschrieben: testet die beiden Export-Endpunkte (Content-Disposition, 404, ZIP-Inhalt inkl. Dedupe bei Namenskollision über Familien hinweg) statt Dateisystem-Verhalten.

**Test-Ergebnis:** `pytest backend/tests` → 235 passed (vorbestehender, unabhängiger Fehler in `test_results.py` weiterhin vorhanden, siehe oben), `npx tsc --noEmit` fehlerfrei.

**Production Ready:** YES — löst das strukturelle Problem (kein Netzwerk-/Dateisystemzugriff Prod → Dev-VPS) endgültig, da der Server keine Annahme über den Hal-Vault-Standort mehr trifft.

## Deployment
**Deployed:** 2026-07-29 · **Version:** v0.2.32-PROJ-19 · **Host:** Dokploy Compose-App (`ms-qql/strategy-bank`, Branch `main`, `docker-compose.dokploy.yml`)

Follow-up deploy, keine Infra-Änderung nötig (keine neuen Env-Vars, keine neue Dependency, keine DB-Migration). Push nach `main` löst Auto-Deploy aus.
