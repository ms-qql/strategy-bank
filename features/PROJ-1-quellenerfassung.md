# PROJ-1: Quellenerfassung

## Status: In Progress
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
_To be added by /qa_

## Deployment
_To be added by /deploy_
