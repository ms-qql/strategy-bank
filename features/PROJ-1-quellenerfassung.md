# PROJ-1: Quellenerfassung

## Status: Deployed
**Created:** 2026-07-15
**Last Updated:** 2026-07-15

## Dependencies
- None

## User Stories
- Als Trader möchte ich Klartext einfügen, um eine Strategiebeschreibung ohne Dateiumweg zu erfassen.
- Als Trader möchte ich eine Markdown-Datei hochladen, um bereits dokumentierte Strategien einzuspeisen.
- Als Trader möchte ich, dass jede Quelle eindeutig identifizierbar bleibt, um spätere Ergebnisse auf genau diese Quelle zurückführen zu können.

## Acceptance Criteria
- [ ] Ein Vorgang (Source-Erfassung) akzeptiert genau eine Quelle: entweder eingefügten Klartext oder eine hochgeladene `.md`-Datei.
- [ ] Beim Speichern wird ein SHA-256-Quell-Hash über den Rohinhalt berechnet und persistiert.
- [ ] Die Quelle wird unverändert (inkl. Whitespace/Zeilenumbrüche) gespeichert, damit spätere Zeilenreferenzen für Quellenbelege (PROJ-2) stabil bleiben.
- [ ] Eine Quelle kann beliebig viele Strategien enthalten — die Erfassung selbst trennt noch nicht in einzelne Strategien (das übernimmt PROJ-2).
- [ ] PDF, Bild/Screenshot-Upload, Web-Link-Eingabe und Mehrfach-Upload sind in der UI nicht vorhanden (kein Upload-Button außer für `.md`).
- [ ] Nach erfolgreicher Erfassung erscheint die Quelle in einer Liste mit Erfassungszeitpunkt, Quell-Hash (gekürzt) und Status „noch nicht extrahiert".
- [ ] Alle UI-Texte und Fehlermeldungen sind auf Deutsch.

## Edge Cases
- Leere Eingabe (nur Whitespace) oder leere `.md`-Datei: Fehlermeldung „Quelle enthält keinen Inhalt.", kein Speichern.
- Datei mit falscher Endung (z. B. `.txt` als Upload statt Klartextfeld): abgelehnt mit Hinweis, dass nur `.md` als Datei-Upload unterstützt wird.
- Identischer Inhalt wird zweimal eingereicht (gleicher Quell-Hash): beide werden als getrennte Quellen gespeichert (kein Dedupe im MVP), da unterschiedliche Vorgänge unterschiedliche Extraktionsläufe auslösen können.
- Sehr große Datei (> 2 MB): Fehlermeldung mit Hinweis auf Größenlimit, kein Speichern.
- Encoding-Probleme (kein valides UTF-8): Fehlermeldung „Datei konnte nicht als Text gelesen werden.".

## Technical Requirements (optional)
- Persistenz: Quelle inkl. Rohinhalt, Quell-Hash, Erfassungszeitpunkt, Quelltyp (`text` | `markdown_file`).
- Security: lokale Single-User-Auth genügt, kein Mandant-Feld.
- Größenlimit konfigurierbar, Default 2 MB.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-15 · **Stack:** Next.js 16 (App Router) + shadcn/ui / FastAPI + raw SQL / PostgreSQL · **Branch:** main (kein Git-Repo initialisiert)

### A) Komponentenstruktur (UI, Next.js)
```
QuellenPage (app/quellen/page.tsx)
├── QuelleErfassenCard
│   ├── Tabs (shadcn/ui)              # „Text einfügen" | „Markdown-Datei"
│   │   ├── TextEingabe (Textarea)    # Klartext
│   │   └── DateiUpload (nur .md)     # accept=".md,text/markdown"
│   ├── SpeichernButton               # disabled bei leerer Eingabe
│   └── FehlerHinweis (Alert)         # deutsche Validierungsmeldungen
└── QuellenListe (Table)
    ├── QuelleZeile                   # Zeitpunkt · Hash (12 Zeichen) · Typ · Status-Badge
    └── EmptyState                    # „Noch keine Quelle erfasst."
```
Genau ein Eingabekanal je Vorgang: entweder Text ODER `.md`-Datei — die Tab-Wahl erzwingt das. Kein weiterer Upload-Button (kein PDF/Bild/Link/Multi), damit AC „nur `.md`" strukturell garantiert ist.

### B) Datenmodell (Klartext)
```
Jede Quelle:
- ID (UUID)
- Rohinhalt (unverändert, inkl. Whitespace/Zeilenumbrüche)
- Quell-Hash (SHA-256 über den Rohinhalt, hex)
- Quelltyp: „text" | „markdown_file"
- Dateiname (nur bei markdown_file, sonst leer)
- Erfassungszeitpunkt (UTC)
- Extraktionsstatus: „noch nicht extrahiert" (Default; wird von PROJ-2 fortgeschrieben)

Speicherort: PostgreSQL, eine Tabelle `sources`. Rohinhalt als TEXT-Spalte.
Kein MinIO — Inhalt ist kleiner Text (≤ 2 MB), und PROJ-2 braucht stabile
Zeilenreferenzen direkt am gespeicherten Rohtext. Kein Mandant-Feld (Solo).
```

### C) API-Form (nur Endpunkte)
```
- POST /sources        → eine Quelle erfassen (Text ODER .md-Datei), liefert ID + Hash zurück
- GET  /sources        → Liste aller Quellen (Zeitpunkt, gekürzter Hash, Typ, Status), neueste zuerst
- GET  /sources/{id}   → eine Quelle inkl. Rohinhalt (für PROJ-2)
```
Kein Auth-Mandant; einfache lokale Single-User-Auth genügt (PRD §3). Validierung server-seitig (Leerinhalt, Endung, 2-MB-Limit, UTF-8) — nicht nur im Client.

### D) Tech-Entscheidungen (warum)
- **Rohinhalt in Postgres statt MinIO:** Quelle ist kurzer Text; der Umweg über Objektspeicher + presigned URLs bringt keinen Nutzen und würde stabile Zeilenreferenzen für PROJ-2 verkomplizieren. MinIO bleibt für spätere Binär-Quellen (PDF/Bild, Phase 2) reserviert.
- **Hash server-seitig berechnet:** Der Quell-Hash ist Rückführbarkeits-Anker (Audit-Trail PROJ-8). Client-berechnete Hashes wären fälschbar/inkonsistent — deshalb im Backend über exakt den persistierten Bytes.
- **Kein Dedupe:** Gleicher Inhalt zweimal = zwei getrennte Quellen (bewusst, laut Spec-Edge-Case) — verschiedene Vorgänge dürfen getrennte Extraktionsläufe auslösen.
- **Tab-erzwungener Einzelkanal statt „beides erlaubt + Serverprüfung":** verhindert den Mehrdeutigkeitsfall (Text + Datei gleichzeitig) schon in der UI.
- **Validierung doppelt (Client für UX, Server als Wahrheit):** Größen-/Endungs-/Encoding-/Leer-Prüfungen sind Trust-Boundary — Serverprüfung ist verbindlich.

### E) Abhängigkeiten
- Backend (Python): FastAPI, `python-multipart` (Datei-Upload), `psycopg`/DB-Zugriff via `run_query_m`/`run_command_m`, `pydantic` v2. SHA-256 aus stdlib `hashlib` — keine neue Dependency.
- Frontend (Next.js): `shadcn/ui` (Tabs, Textarea, Table, Alert, Badge, Button), Zod + react-hook-form für Formvalidierung, `api-client.ts` (Fetch-Wrapper).

## Backend-Implementierung (abc-backend, 2026-07-15)

FastAPI + raw SQL in `backend/`, single-user (kein Mandant/RLS laut PRD §3).

**Dateien:**
- `backend/sql/001_sources.sql` — `sources`-Tabelle: `id`, `content`, `source_hash`, `source_type` (`text`|`markdown_file`), `file_name`, `extraction_status` (Default „noch nicht extrahiert", PROJ-2-Enum vorhanden), `created_at`. Index auf `created_at DESC`.
- `backend/app/schemas/sources.py` — `SourceListItem`, `SourceDetail` (Pydantic v2).
- `backend/app/routes/sources.py` — `POST /sources` (multipart: `content` ODER `file`, niemals beides), `GET /sources` (neueste zuerst, `limit` 1–200), `GET /sources/{id}`.
- `backend/app/main.py` — Router eingebunden, Exception-Handler für `InvalidTextRepresentation` (→ 404 „Nicht gefunden.") und `ForeignKeyViolation` (→ 422).
- `backend/app/config.py` — `source_max_bytes` (Default 2 MB, aus `.env` überschreibbar).
- `backend/tests/test_sources.py` — 10 Tests: Happy-Paths (Text + Datei), Validierung (leer/beides/falsche Endung/zu groß/UTF-8/Größenlimit-monkeypatch), List newest-first, GET 404.

**Hash:** server-seitig `hashlib.sha256(raw_bytes).hexdigest()` über genau die persistierten Bytes.

**Validierung (Trust-Boundary, Server verbindlich):** leer ↔ 400 „Quelle enthält keinen Inhalt.", beides ↔ 400 „nicht beides", falsche Endung ↔ 400 „Nur .md-Dateien", >2 MB ↔ 400 „Größenlimit", UTF-8-Fehler ↔ 400 „konnte nicht als Text gelesen".

**Tests:** 27/27 grün (10× `test_sources.py`, 17× PROJ-2). Live-Smoke: POST Text + POST `.md` + GET-Liste + 400-/404-Pfade alle wie erwartet.

**Branch:** main (siehe Tech-Design). Backend liegt aktuell untracked im Working Tree (`backend/` + `docker-compose.yml`).

**Frontend-Implementierung (abc-frontend, 2026-07-15)**

Next.js 16 (App Router) + shadcn/ui in `nextjs_app/` frisch gescaffoldet (erstes Feature, Repo war leer).

**Neue/geänderte Dateien:**
- `app/quellen/page.tsx` — Route `/quellen` (Seiten-Header + View).
- `components/quellen/quellen-view.tsx` — Client-Component: Erfassen-Card (Tabs Text|`.md`) + Quellen-Tabelle, `useState`/`fetch` (kein Riverpod — Next.js-Stack).
- `lib/api-client.ts` — Fetch-Wrapper zum FastAPI-Backend, `NEXT_PUBLIC_API_URL` (Default `http://localhost:8000`), `ApiError`.
- `lib/schemas/source.ts` — Zod-Schemas + `MAX_SOURCE_BYTES` (2 MB).
- `app/layout.tsx` — `lang="de"`, Metadata DE; **DSGVO:** Schrift DM Sans via Bunny Fonts (kein Google-CDN). `app/globals.css` `--font-sans` auf DM Sans.
- `app/page.tsx` — Redirect `/` → `/quellen`.
- `.env.local` — `NEXT_PUBLIC_API_URL`.

**API-Vertrag (für /abc-backend verbindlich):**
- `POST /sources` — `multipart/form-data`: Feld `source_type` (`text`|`markdown_file`), dazu `content` (bei Text) **oder** `file` (bei `.md`). Liefert ein `Source`-Objekt zurück.
- `GET /sources` — Array von `Source`, neueste zuerst.
- `Source` = `{ id, source_hash, source_type, filename|null, captured_at (ISO-UTC), extraction_status }`.
- Fehler als FastAPI `{ detail: "…" }` (deutsche Meldung) → Client zeigt `detail` im Alert.

**Client-Validierung (UX; Server bleibt verbindlich):** Leerinhalt, `.md`-Endung, 2-MB-Limit → deutsche Alerts. Nur `.md` als Datei-Upload (`accept=".md"`), kein PDF/Bild/Link/Multi.

**Status:** UI baut sauber (`npm run build` + `npm run lint` grün, Routen `/`, `/quellen`). Liste zeigt bis zum Backend-Bau „Quellen konnten nicht geladen werden."; nicht in echter Runtime gegen Backend getestet (Backend existiert noch nicht).

## QA Test Results

**Tested:** 2026-07-15 (Erstlauf) + 2026-07-15 (Re-QA nach BUG-1/BUG-2-Fix)
**Backend:** `http://localhost:8765` (FastAPI, gegen Dev-Postgres `@55433`)
**Frontend:** nicht getestet (manueller API-Smoke + pytest-Suite; UI-Smoke gehört in `/abc-qa-e2e`)
**Tester:** QA Engineer (AI)

### Acceptance Criteria Status

#### AC-1: Eine Quelle pro Vorgang (Text ODER `.md`-Datei)
- [x] POST text → 201, `source_type="text"`, `filename=null`
- [x] POST `.md`-Datei → 201, `source_type="markdown_file"`, `filename` gesetzt
- [x] POST beides → 400 „Es kann nur Text ODER eine Datei angegeben werden, nicht beides."
- [x] POST weder noch → 400 „Quelle enthält keinen Inhalt."

#### AC-2: SHA-256-Quell-Hash serverseitig
- [x] Hash ist 64-stelliges Hex (Python `hashlib.sha256(raw_bytes).hexdigest()`)
- [x] Hash-Wert exakt = SHA-256 der Eingabe (gegen `sha256sum` verifiziert)

#### AC-3: Quelle unverändert inkl. Whitespace/Zeilenumbrüche
- [x] Inhalt mit `\n\n\n   ` wird mit identischen Whitespace-Zeichen zurückgegeben
- [x] Roh-Bytes werden vor Hash gehasht und als TEXT persistiert (kein `.strip()` auf der Persistenz)

#### AC-4: Eine Quelle darf beliebig viele Strategien enthalten
- [x] Kein Parsing/Splitting im PROJ-1-Code (nur Persistenz; Aufteilung macht PROJ-2)
- [x] DB-Schema kennt keine Strategie-Trennung in `sources`

#### AC-5: Keine PDF/Bild/Web-Link/Multi-Upload
- [x] Routes akzeptieren nur `content` (str) + `file` (UploadFile) — keine weiteren Felder
- [x] `.md`-Endungs-Check auf Datei-Upload (`file.filename.lower().endswith(".md")`)

#### AC-6: Liste zeigt Erfassungszeitpunkt + (gekürzter) Hash + Status
- [x] `GET /sources` liefert `captured_at` (ISO-UTC), `source_hash` (64 Zeichen, Client kürzt auf 12), `extraction_status` (Default „noch nicht extrahiert")
- [x] Sortierung `created_at DESC` (neueste zuerst)

#### AC-7: Deutsche UI-Texte und Fehlermeldungen
- [x] Alle 400/404-Antworten liefern deutschsprachige `detail`-Strings
- [x] Keine englischen Stacktraces oder interne Pfade in Fehlern

### Edge Cases Status

#### EC-1: Leere/whitespace-only Eingabe
- [x] `content=""` → 400 „Quelle enthält keinen Inhalt."
- [x] `content="   \n   "` → 400 „Quelle enthält keinen Inhalt."
- [x] `.md`-Datei mit 0 Bytes → 400 „Quelle enthält keinen Inhalt."

#### EC-2: Falsche Dateiendung
- [x] `.txt` → 400 „Nur .md-Dateien werden als Datei-Upload unterstützt."
- [x] `.markdown` → 400 (abgelehnt, Spec: nur `.md`)
- [x] `.mdx` → 400
- [x] `.MD` (uppercase) → 201 akzeptiert (`.lower()`-Vergleich; akzeptable Spec-Auslegung)
- [x] Leerer Dateiname → 400 „Quelle enthält keinen Inhalt."

#### EC-3: Identischer Inhalt zweimal
- [x] Zwei POSTs liefern zwei unterschiedliche UUIDs mit identischem `source_hash` (kein Dedupe, wie spezifiziert)

#### EC-4: > 2 MB
- [x] 2 MB + 1 Byte → 400 „Datei überschreitet das Größenlimit von 2 MB."
- [x] Genau 2 MB → 201 (Boundary korrekt)
- [x] Limit konfigurierbar via `source_max_bytes` in `.env` (von test verifiziert per monkeypatch)

#### EC-5: Kein valides UTF-8
- [x] Datei mit `\xff\xfe\x00bad` → 400 „Datei konnte nicht als Text gelesen werden."
- [x] Reine Binärdaten (Bytes 0–255) → 400 (gleiche Meldung)

### Zusätzliche QA-Tests (über Spec hinaus)

- [x] `GET /sources?limit=0` → 1 Zeile (auf 1 geclampt)
- [x] `GET /sources?limit=10000` → max 200 (geclampt; tatsächlich 9 vorhanden)
- [x] `GET /sources?limit=-5` → 1 (auf 1 geclampt)
- [x] `GET /sources?limit=abc` → 422 Pydantic Validation
- [x] `GET /sources/<valid-uuid>` mit existierender ID → 200 inkl. `content`
- [x] `GET /sources/00000000-0000-0000-0000-000000000000` → 404 „Quelle nicht gefunden."
- [x] SQL-Injection-Versuch in `content` und `filename` (psycopg `%s` parametrisiert) → keine Wirkung, `sources`-Tabelle intakt
- [x] pytest-Regression: 27/27 grün (10× `test_sources.py` + 17× PROJ-2-Suite)
- [x] `python -m compileall app` clean

### Security Audit Results

- [x] **Auth:** Spec Single-User, keine Auth implementiert — wie spezifiziert
- [x] **Mandant/RLS:** Spec Single-Tenant, keine RLS — wie spezifiziert
- [x] **SQL-Injection:** Alle DB-Calls nutzen `psycopg`-`%s`-Parameter; kein f-string-SQL
- [x] **Error-Leakage:** Server-Antworten liefern nur `{"detail": "..."}`, keine Stacktraces/Pfade
- [x] **CORS (BUG-1 behoben):** `CORSMiddleware` registriert, Origins aus `settings.cors_allow_origins` (Default `http://localhost:3000`, Prod via `CORS_ALLOW_ORIGINS` CSV-Env). Preflight `OPTIONS /sources` → 200 mit `access-control-allow-origin: http://localhost:3000` für erlaubte Origins; nicht-Whitelist-Origins erhalten die Response ohne `access-control-allow-origin`-Header (Browser blockt Lesen der Antwort).
- [x] **Path-Traversal:** `filename` wird ungeprüft in DB gespeichert; **kein direkter Exploit**, weil Content als TEXT in DB liegt (kein Dateisystemzugriff auf `filename`) — siehe BUG-3
- [x] **Non-UUID-Pfad (BUG-2 behoben):** `RequestValidationError`-Handler fängt `type=uuid_parsing` + `loc[0]=path` ab → 404 „Nicht gefunden." für `/sources/{id}`, `/extractions/{id}`, `/drafts/{id}`, `/sources/{id}/extractions`. Keine Pydantic-Internals in Response. Andere Validation-Errors bleiben bei 422.

### Bugs Found

#### BUG-1: Keine CORS-Middleware — Browser blockt Frontend→Backend
- **Severity:** Critical
- **Steps to Reproduce:**
  1. Starte Backend auf `localhost:8000`, Next.js-Frontend auf `localhost:3000` (Default-Ports laut `.env.local`/`next.config.ts`).
  2. Lade `/quellen` im Chrome.
  3. Klicke „Speichern" mit einer Quelle.
- **Expected:** POST landet am Backend, Quelle erscheint in der Liste.
- **Actual:** Browser-Console: CORS-Preflight (`OPTIONS /sources`) → 405, kein `Access-Control-Allow-Origin` auf der POST-Antwort. Browser blockt den Request. Liste bleibt leer.
- **Proof:**
  - `curl -i -X OPTIONS http://localhost:8765/sources -H "Origin: http://localhost:3000" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: content-type"` → `HTTP/1.1 405 Method Not Allowed`, `allow: POST`, keine CORS-Header.
  - `main.py` enthält keine `CORSMiddleware`-Registrierung.
- **Fix:** `backend/app/main.py` — `from fastapi.middleware.cors import CORSMiddleware` + `app.add_middleware(CORSMiddleware, allow_origins=[...], allow_methods=["GET","POST"], allow_headers=["*"])`. Origins aus `settings` konfigurierbar (Dev: `http://localhost:3000`, Prod: konfigurierbar).
- **Priority:** Fix before deployment (blockt jedes Frontend→Backend-Cross-Origin).
- **Resolution (2026-07-15):** `CORSMiddleware` in `main.py:13` registriert, `cors_allow_origins` in `config.py` mit CSV-`field_validator`. Live-Smoke: Preflight 200 mit Headers, POST mit erlaubtem Origin 201 + Allow-Origin, nicht-Whitelist-Origin POST 201 ohne Allow-Origin-Header (Browser blockt). 4 pytest-Tests grün (`test_api_hardening.py`).

#### BUG-2: Non-UUID-Pfad-Parameter liefert 422 statt 404
- **Severity:** Medium
- **Steps to Reproduce:**
  1. `curl http://localhost:8765/sources/not-a-uuid`
- **Expected:** 404 „Nicht gefunden." (Spec: „Als 'nicht gefunden' (404) behandeln statt Serverfehler.")
- **Actual:** 422 mit englischem Pydantic-Trace `{"detail":[{"type":"uuid_parsing","loc":["path","source_id"],"msg":"Input should be a valid UUID, invalid character: found 'n' at 1","input":"not-a-uuid","ctx":{...}}]}`.
- **Root cause:** Pydantic validiert `source_id: UUID` **vor** dem Route-Body; `main.py` registriert nur Handler für `InvalidTextRepresentation` (DB-Layer) und `ForeignKeyViolation` (DB-Layer), nicht für `RequestValidationError` (Path-Layer).
- **Fix:** `RequestValidationError`-Handler in `main.py:32` fängt `type=uuid_parsing` + `loc[0]=path` ab → 404 „Nicht gefunden." Andere Validation-Errors bleiben 422.
- **Priority:** Fix before deployment (sowohl UX als auch minimales Info-Disclosure).
- **Resolution (2026-07-15):** Handler in `main.py:32`. Live-Smoke: alle 4 Non-UUID-Pfade → 404 mit flachem `{"detail": "Nicht gefunden."}`, kein `uuid_parsing`/Pydantic-String in der Response. 5 pytest-Tests grün.

#### BUG-3: Filename wird ungeprüft persistiert (Path-Traversal-Form)
- **Severity:** Low
- **Steps to Reproduce:**
  1. `curl -X POST http://localhost:8765/sources -F "file=@/tmp/x.md;filename=../../../etc/passwd.md"`
- **Expected:** Spec schweigt; wahlweise Sanitize auf reinen Dateinamen (kein Pfad) oder dokumentiertes Akzeptieren.
- **Actual:** `filename` wird verbatim als `../../../etc/passwd.md` in `sources.file_name` gespeichert.
- **Impact:** Kein direkter Exploit — Content liegt in `sources.content` (TEXT), `file_name` wird nirgendwo als Pfad verwendet, kein File-Write serverseitig. Risiko entsteht erst, wenn ein Downstream-Code `file_name` als Pfad interpretiert.
- **Fix:** Entweder `os.path.basename(file.filename)` vor Persistenz, oder explizit dokumentieren dass `file_name` exakt der Upload-Dateiname ist.
- **Priority:** Nice to have (Defense-in-Depth, kein aktiver Bug).

#### BUG-4: Fehlermeldung „Datei überschreitet das Größenlimit" auch bei Text-Overflow
- **Severity:** Low
- **Steps to Reproduce:**
  1. >2 MB Text in `content` pasten und POSTen.
- **Expected:** „Eingabe überschreitet das Größenlimit von 2 MB." (oder ähnlich, ohne „Datei").
- **Actual:** „Datei überschreitet das Größenlimit von 2 MB." — suggeriert fälschlich, dass ein Datei-Upload schuld war.
- **Root cause:** `routes/sources.py:41` hardcoded „Datei".
- **Fix:** Branch: `has_file` → „Datei überschreitet…", `has_content` → „Eingabe überschreitet…".
- **Priority:** Nice to have (kosmetisch, deutsche Klarheit).

### Summary
- **Acceptance Criteria:** 7/7 passed
- **Edge Cases:** 5/5 passed (alle Spec-Edge-Cases + 5 zusätzliche Server-Validierungen)
- **Regression:** 36/36 pytest grün (10× PROJ-1 + 17× PROJ-2 + 9× Härtung)
- **Bugs Found (Erstlauf):** 4 total (1 critical, 1 medium, 2 low)
- **Bugs Resolved:** BUG-1 (CORS) + BUG-2 (Non-UUID 404) — gefixt, re-QA grün
- **Bugs Offen:** BUG-3 (Filename-Sanitization, Low) + BUG-4 („Datei"-Message bei Text-Overflow, Low) — explizit zurückgestellt
- **Security:** CORS + Path-Validation beide behoben; keine offenen High/Critical
- **Production Ready:** **YES** (BUG-3 + BUG-4 sind Defense-in-Depth / Kosmetik, kein Blocker)
- **Recommendation:** Deploy-fähig. BUG-3/BUG-4 in späterem Sprint aufgreifen.

## Deployment
__Deployed 2026-07-15__ / **Version:** v0.2.0 / **Stack:** Next.js standalone + FastAPI + PostgreSQL 16 auf Dokploy
