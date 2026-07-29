# PROJ-20: PDF, EPUB und MOBI als Markdown importieren

## Status: In Review
**Created:** 2026-07-29
**Last Updated:** 2026-07-29

## Dependencies
- Requires: PROJ-1 (Quellenerfassung) — bestehende Speicherung, Hashbildung und Einzelquellen-Regeln.
- Requires: PROJ-2 (KI-Extraktion) — erzeugtes Markdown wird über den vorhandenen Extraktionsweg verarbeitet.
- Requires: PROJ-14 (Markdown-Drag-and-Drop) — bestehende Dateiauswahl und Dropzone werden erweitert.

## User Stories
- Als Trader möchte ich eine PDF-, EPUB- oder MOBI-Datei als Quelle auswählen, um Strategien aus Büchern und Dokumenten ohne manuelles Kopieren zu erfassen.
- Als Trader möchte ich, dass unterstützte Dokumente in Markdown umgewandelt werden, damit danach derselbe Extraktionsablauf wie bei einer Markdown-Datei gilt.
- Als Trader möchte ich erkennen, welches Originalformat und welcher Dateiname importiert wurden, um die Quelle später zuordnen zu können.
- Als Trader möchte ich eine verständliche Fehlermeldung erhalten, wenn ein Dokument nicht gelesen oder nicht sinnvoll in Text umgewandelt werden kann.
- Als Trader möchte ich, dass Scan-PDFs ohne Textschicht nicht stillschweigend als leere Quelle übernommen werden.

## Acceptance Criteria
- [ ] Die Quellenerfassung akzeptiert genau eine Datei mit der Endung `.md`, `.pdf`, `.epub` oder `.mobi`; Klartext und Mehrfach-Upload bleiben unverändert.
- [ ] Dateidialog und Drag-and-Drop unterstützen dieselben vier Dateiformate und zeigen vor dem Speichern Dateiname, Dateigröße und erkanntes Format.
- [ ] Beim Speichern einer PDF-, EPUB- oder MOBI-Datei wird deren lesbarer Text in Markdown umgewandelt.
- [ ] Das erzeugte Markdown erhält erkennbare Absätze und übernimmt vorhandene Überschriften, Listen und Codeblöcke, soweit das Ausgangsformat diese Struktur bereitstellt.
- [ ] Nach erfolgreicher Umwandlung wird das erzeugte Markdown als Quelleninhalt gespeichert und anschließend ohne Sonderweg über die bestehende Extraktion aus PROJ-2 verarbeitet.
- [ ] Der SHA-256-Quell-Hash wird über die unveränderten Bytes der hochgeladenen Originaldatei berechnet, nicht über das erzeugte Markdown.
- [ ] Originaldateiname und Originalformat bleiben an der Quelle sichtbar; ein erneuter Import derselben Datei bleibt wie in PROJ-1 erlaubt.
- [ ] Eine Quelle wird erst als erfolgreich erfasst angezeigt, wenn die Umwandlung vollständig abgeschlossen ist. Währenddessen zeigt die Oberfläche „Dokument wird umgewandelt …“.
- [ ] PDF-Dateien werden nur unterstützt, wenn sie eine auslesbare Textschicht enthalten. OCR und Bilderkennung werden nicht ausgeführt.
- [ ] Schlägt die Umwandlung fehl, wird kein unvollständiger Quelleninhalt gespeichert und die Oberfläche zeigt eine deutsche Fehlermeldung.
- [ ] Pro Datei gilt ein Größenlimit von 25 MB; größere Dateien werden vor der Umwandlung mit „Datei überschreitet das Größenlimit von 25 MB.“ abgelehnt.
- [ ] Die bestehende Markdown-Erfassung und nachgelagerte Extraktion bleiben funktional unverändert.

## Edge Cases
- Eine PDF ohne auslesbare Textschicht wird abgelehnt mit „Die PDF enthält keinen auslesbaren Text. Scan-PDFs werden nicht unterstützt.“.
- Eine beschädigte oder nicht dem angegebenen Format entsprechende Datei wird abgelehnt mit „Das Dokument konnte nicht gelesen werden.“.
- Eine DRM-geschützte oder verschlüsselte Datei wird abgelehnt mit „Geschützte Dokumente werden nicht unterstützt.“.
- Ein Dokument, dessen Umwandlung nur Whitespace oder keinen lesbaren Text ergibt, wird wie eine leere Quelle abgelehnt.
- Bilder, Umschlaggrafiken und eingebettete Medien ohne Textinhalt werden ignoriert; sie lösen keine OCR-Verarbeitung aus.
- Tabellen und komplexe Seitenlayouts werden bestmöglich als lesbarer Markdown-Text übernommen; eine pixelgetreue Layout-Reproduktion ist nicht erforderlich.
- Inhaltsverzeichnisse, Fußnoten oder wiederkehrende Kopf-/Fußzeilen dürfen im erzeugten Markdown enthalten bleiben; deren automatische Bereinigung ist nicht Teil dieses Features.
- Ein Abbruch oder interner Fehler während der Umwandlung erzeugt weder eine teilweise Quelle noch einen Extraktionslauf.
- Dateiendungen werden unabhängig von Groß-/Kleinschreibung erkannt.

## Non-Goals
- OCR für Scan-PDFs oder Bilder.
- Rekonstruktion eines originalgetreuen Seitenlayouts.
- Extraktion eingebetteter Bilder, Diagramme oder handschriftlicher Anmerkungen.
- Web-Links und Mehrfach-Upload.
- Automatische inhaltliche Bereinigung oder Zusammenfassung vor PROJ-2.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-29 · **Stack:** Next.js 16 (App Router) + shadcn/ui / FastAPI + PostgreSQL · **Branch:** dev

### A) Komponentenstruktur

```text
QuellenView
├── QuelleErfassenCard
│   ├── QuellenTabs
│   │   ├── KlartextEingabe (unverändert)
│   │   └── DokumentUploadPanel
│   │       ├── DokumentDropzone (.md, .pdf, .epub, .mobi)
│   │       ├── Dateiauswahl (Name, Größe, erkanntes Format)
│   │       └── Gemeinsame Dateivalidierung
│   ├── Umwandlungsstatus („Dokument wird umgewandelt …“)
│   ├── FehlerHinweis
│   └── QuelleSpeichernButton
└── QuellenListe
    └── QuelleZeile (Originalformat und Originaldateiname)
```

Die bestehende Markdown-Dropzone wird zur Dokument-Dropzone erweitert. Auswahl
per Klick und Drag-and-Drop verwenden weiterhin denselben Zustand und dieselbe
Validierung. Das Ablegen startet weder Speicherung noch Extraktion automatisch.

Beim Speichern bleibt das Formular geöffnet und zeigt den Umwandlungsstatus, bis
das Backend entweder die fertige Quelle oder eine deutsche Fehlermeldung
zurückgibt. Ein separater Fortschrittsdialog oder Polling ist nicht nötig.

### B) Datenmodell

Das bestehende Quellenobjekt bleibt erhalten und wird nur um weitere erlaubte
Quelltypen ergänzt:

- `text` für eingefügten Klartext
- `markdown_file` für unveränderte Markdown-Dateien
- `pdf_file`, `epub_file` und `mobi_file` für umgewandelte Dokumente

Bei PDF, EPUB und MOBI enthält das bestehende Inhaltsfeld das fertig erzeugte
Markdown. Dateiname und Quelltyp halten die Herkunft sichtbar; der vorhandene
Quell-Hash wird über die Originaldatei berechnet.

Die binäre Originaldatei wird nach der erfolgreichen Umwandlung nicht dauerhaft
gespeichert. Damit sind weder eine neue Dateitabelle noch MinIO erforderlich.
Eine Datenbankmigration erweitert ausschließlich die erlaubten Werte des
bestehenden Quelltyps.

### C) API-Form

- `POST /sources` → nimmt weiterhin genau Klartext oder eine Datei entgegen;
  PDF, EPUB und MOBI werden vor dem Speichern in Markdown umgewandelt
- `GET /sources` → liefert die vorhandene Quellenliste mit den neuen Quelltypen
- `GET /sources/{id}` → liefert wie bisher den gespeicherten, weiterverarbeitbaren
  Inhalt; bei Dokumentimporten ist dies das erzeugte Markdown
- `POST /sources/{id}/extractions` → bleibt unverändert und erhält unabhängig vom
  Originalformat immer den gespeicherten Textinhalt

Die Umwandlung erfolgt innerhalb des bestehenden Speichervorgangs. Erst nach
vollständigem Erfolg wird die Quelle angelegt; dadurch können weder Teilinhalte
noch verwaiste Extraktionsläufe entstehen.

### D) Technische Entscheidungen

- **Ein Import-Endpunkt statt eigener Konvertierungs-API:** Die Umwandlung ist
  Teil der Quellenerfassung und hat keinen eigenständigen Produktlebenszyklus.
- **Synchroner Vorgang statt Queue:** Eine einzelne Datei bis 25 MB wird einmalig
  umgewandelt. Der bestehende Request mit sichtbarem Ladezustand genügt; Jobs,
  Polling und zusätzliche Statusfelder würden nur parallele Infrastruktur
  erzeugen.
- **Bestehendes Inhaltsfeld als gemeinsame Naht:** PROJ-2 und alle späteren
  Schritte lesen weiterhin ausschließlich Text. Sie benötigen keine Kenntnis
  von PDF, EPUB oder MOBI.
- **Original-Hash, erzeugter Inhalt:** Der Hash hält die Herkunft auf die exakte
  Upload-Datei zurückführbar, während das Markdown stabile Zeilenreferenzen für
  die bestehende Extraktion liefert.
- **Keine dauerhafte Binärablage:** Originaldateien sind weder zum Extrahieren
  noch zum Anzeigen erforderlich. Der Verzicht auf MinIO spart Storage,
  Berechtigungen, Bereinigung und Backup-Logik.
- **Formatprüfung im Backend:** Dateiendung, Dateigröße, tatsächliche
  Dokumentstruktur, Verschlüsselung/DRM und leerer Konvertierungsoutput werden an
  der Trust Boundary geprüft. Erst danach darf gespeichert werden.
- **Begrenzte Konvertierung:** Bilder werden ignoriert; verschachtelte Archive
  und ungewöhnlich stark aufgeblähte Inhalte werden abgebrochen. Temporäre
  Dateien werden nach jedem Versuch entfernt.
- **PDF bleibt Textimport:** Seiten werden in Reihenfolge als lesbarer
  Markdown-Text übernommen. Ohne Textschicht wird ausdrücklich abgelehnt; OCR,
  Layoutanalyse und automatische Kopf-/Fußzeilenbereinigung bleiben außen vor.

### E) Abhängigkeiten

- **Backend, neu:** `pypdf` für Text-PDFs, `EbookLib` für EPUB,
  `mobi` für unverschlüsselte MOBI-Dateien und `markdownify` für die gemeinsame
  HTML-zu-Markdown-Umwandlung der E-Book-Inhalte
- **Backend, vorhanden:** FastAPI-Dateiupload, SHA-256 aus der Python-Standardbibliothek
  und PostgreSQL-Persistenz
- **Frontend:** keine neuen Pakete; vorhandene Browser-Dateiauswahl,
  React-Zustände und shadcn/ui-Komponenten genügen
- **Storage:** kein MinIO und kein zusätzlicher externer Dienst

## QA Test Results
**Tested:** 2026-07-29
**Backend:** FastAPI/TestClient gegen lokale PostgreSQL-Testdatenbank; Browser-API auf `http://127.0.0.1:8200`
**Frontend:** Next.js Production Build auf `http://127.0.0.1:3120`
**Tester:** QA Engineer (AI)

### Acceptance Criteria Status

#### AC-1: Einzelquelle und erlaubte Dateiformate
- [x] Klartext oder genau eine `.md`-, `.pdf`-, `.epub`- oder `.mobi`-Datei wird angenommen.
- [x] Mehrfach-Drop, fehlende Datei und andere Endungen werden mit deutschen Meldungen abgelehnt.

#### AC-2: Gemeinsame Dateiauswahl
- [x] Dialog und Drag-and-Drop verwenden dieselbe Dropzone.
- [x] Name, Größe und erkanntes Format erscheinen vor dem Speichern.
- [x] Groß-/Kleinschreibung der Endung wird korrekt behandelt.

#### AC-3: PDF, EPUB und MOBI werden in Markdown umgewandelt
- [x] Text-PDF wird ausgelesen.
- [x] Echtes EPUB wird in Markdown umgewandelt und über `POST /sources` persistiert.
- [ ] **BUG-1:** Jeder MOBI-Import schlägt fehl, weil `mobi.extract()` ein Tupel aus
  Temporärverzeichnis und Ergebnisdatei liefert, der Konverter aber einen einzelnen
  Dateipfad erwartet.

#### AC-4: Dokumentstruktur bleibt bestmöglich erhalten
- [x] EPUB-Test erhält Überschrift, Absatz, Liste, Code und Tabelle als Markdown.
- [x] PDF-Seiten werden in Reihenfolge als lesbarer Text übernommen.
- [ ] MOBI kann wegen BUG-1 nicht geprüft oder verarbeitet werden.

#### AC-5: Gemeinsamer PROJ-2-Pfad
- [x] Erfolgreich konvertiertes EPUB liegt im bestehenden `sources.content`.
- [x] Die vorhandene Extraktionsroute liest weiterhin ausschließlich dieses Inhaltsfeld.

#### AC-6: Hash der Originalbytes
- [x] API-Test bestätigt SHA-256 über den Upload statt über das konvertierte Markdown.

#### AC-7: Herkunft sichtbar und erneuter Import erlaubt
- [x] Originalformat wird in der Quellenliste angezeigt.
- [x] Derselbe Inhalt darf weiterhin mehrfach importiert werden.
- [ ] **BUG-2:** Der Originaldateiname wird von der API geliefert, aber in der
  Quellenliste nicht dargestellt.

#### AC-8: Atomarer Speichervorgang und Ladezustand
- [x] „Dokument wird umgewandelt …“ ist während des Requests sichtbar.
- [x] Der Datensatz wird erst nach erfolgreicher Konvertierung angelegt.

#### AC-9: Keine OCR
- [x] Leere Text-PDF wird mit „Die PDF enthält keinen auslesbaren Text.
  Scan-PDFs werden nicht unterstützt.“ abgelehnt.

#### AC-10: Fehler erzeugen keine Teilquelle
- [x] Beschädigte PDF-/EPUB-Dateien und leerer Konvertierungsoutput liefern 400.
- [x] Vor dem erfolgreichen Insert wird kein Extraktionslauf gestartet.

#### AC-11: 25-MB-Limit
- [x] Client und Backend verwenden 25 MB und dieselbe deutsche Fehlermeldung.
- [ ] **BUG-3:** Für entpackten EPUB-/MOBI-Inhalt und erzeugtes Markdown existiert
  kein Ausgabelimit. Ein 7-KB-EPUB erzeugte im Test 5,24 MB Markdown
  (Faktor 743,8); ein Zip-Bomb-Upload kann Speicher und Datenbank erschöpfen.

#### AC-12: Regression Markdown und Extraktion
- [x] Alle 20 Source-API-Tests sowie die neuen realen Konvertertests laufen.
- [x] Next.js Production Build und ESLint der drei geänderten Frontend-Dateien sind grün.

### Edge Cases Status

- [x] Scan-PDF ohne Textschicht: korrekte Ablehnung.
- [x] Beschädigtes Dokument: korrekte Ablehnung.
- [ ] **BUG-4:** Ein EPUB mit `META-INF/encryption.xml` wurde nicht als geschützt
  erkannt und als inhaltsarmes Markdown gespeichert.
- [x] Leerer Konvertierungsoutput: keine Persistenz.
- [x] Bilder und eingebettete Medien werden nicht extrahiert.
- [x] EPUB-Überschrift, Liste, Codeblock und Tabelle werden lesbar übernommen.
- [x] Kopf-/Fußzeilen werden nicht automatisch bereinigt.
- [ ] **BUG-5:** Ein fehlerhafter MOBI-Versuch hinterlässt jeweils ein
  `mobiex*`-Temporärverzeichnis.
- [x] Endungen werden case-insensitiv erkannt.

### Browser- und Responsive-Test

- [x] 15/15 Browser-Smokes bestanden: Dropzone, vier Formate, falsche Endung,
  Mehrfach-Drop, Enter-Taste, Ladezustand, Format in Liste sowie 375/768/1440 px.
- [x] Tastaturbedienung und sichtbarer Fokus der bestehenden Dropzone bleiben erhalten.
- [ ] **BUG-6:** Der Seitenuntertitel lautet weiterhin
  „Strategiebeschreibungen als Text oder Markdown-Datei erfassen.“
- Screenshot: `screenshots/test/proj20-source-row-no-filename.png`

### Security Audit Results

- [x] SQL-Parameter bleiben gebunden; Dateiname und Inhalt werden nicht in SQL interpoliert.
- [x] Dateiendung, Dateigröße und tatsächliche Dokumentstruktur werden serverseitig geprüft.
- [x] Dateiname wird nicht als Serverpfad verwendet; React rendert Nutzwerte als Text.
- [x] Kein MinIO und keine neuen Secrets beteiligt.
- [ ] **BUG-3:** Unbegrenzte Dekompression/Markdown-Ausgabe ermöglicht
  Ressourcenerschöpfung. Das ist besonders relevant, weil `/sources` im
  bestehenden Single-User-System keine eigene Authentisierung oder Rate-Limitierung hat.
- [ ] **BUG-4:** EPUB-Schutzmetadaten werden nicht erkannt.
- [ ] **BUG-5:** MOBI-Temporärverzeichnisse werden bei Fehlern nicht bereinigt.

### Bugs Found

#### BUG-1: MOBI-Import funktioniert nie
- **Severity:** High
- **Steps to Reproduce:**
  1. Eine gültige `.mobi`-Datei an `POST /sources` senden.
  2. `mobi.extract()` liefert `(tempdir, result_path)`.
  3. Erwartet: Ergebnisdatei wird als EPUB oder HTML in Markdown umgewandelt.
  4. Tatsächlich: Tupel wird als Dateipfad geprüft; Antwort ist 400
     „Das Dokument konnte nicht gelesen werden.“.
- **Zusatz:** Die Bibliothek kann neben EPUB auch HTML/PDF zurückgeben; der aktuelle
  Code behandelt jedes Ergebnis ausschließlich als EPUB.
- **Priority:** Fix before deployment.

#### BUG-2: Originaldateiname fehlt in der Quellenliste
- **Severity:** Medium
- **Steps to Reproduce:**
  1. `book.epub` erfolgreich importieren.
  2. Erwartet: Originalformat und `book.epub` bleiben sichtbar.
  3. Tatsächlich: Die Tabelle zeigt nur „EPUB-E-Book“.
- **Screenshot:** `screenshots/test/proj20-source-row-no-filename.png`
- **Priority:** Fix before deployment.

#### BUG-3: Keine Grenze für entpackten oder konvertierten Inhalt
- **Severity:** High
- **Steps to Reproduce:**
  1. Ein stark komprimiertes EPUB unter 25 MB hochladen.
  2. Erwartet: Ungewöhnlich stark aufgeblähter Inhalt wird abgebrochen.
  3. Tatsächlich: 7.049 Upload-Bytes wurden zu 5.242.971 Markdown-Bytes;
     es gibt weder Verhältnis-, Ausgabe- noch Speicherschranke.
- **Priority:** Fix before deployment.

#### BUG-4: DRM-/verschlüsseltes EPUB wird nicht erkannt
- **Severity:** Medium
- **Steps to Reproduce:**
  1. EPUB mit `META-INF/encryption.xml` und verschlüsseltem Inhaltsdokument importieren.
  2. Erwartet: 400 „Geschützte Dokumente werden nicht unterstützt.“.
  3. Tatsächlich: Import wird akzeptiert und Navigationsreste werden als Markdown gespeichert.
- **Priority:** Fix before deployment.

#### BUG-5: MOBI-Fehler hinterlassen temporäre Verzeichnisse
- **Severity:** Medium
- **Steps to Reproduce:**
  1. Anzahl `/tmp/mobiex*` erfassen.
  2. Eine beschädigte MOBI-Datei konvertieren.
  3. Erwartet: Alle temporären Artefakte werden entfernt.
  4. Tatsächlich: Pro Versuch bleibt ein neues `mobiex*`-Verzeichnis bestehen.
- **Priority:** Fix before deployment.

#### BUG-6: Seitenuntertitel nennt nur Markdown
- **Severity:** Low
- **Steps to Reproduce:**
  1. `/quellen` öffnen.
  2. Erwartet: PDF, EPUB und MOBI werden im Seitenkontext berücksichtigt.
  3. Tatsächlich: Untertitel nennt weiterhin ausschließlich Text und Markdown.
- **Priority:** Nice to have.

### Automated Test Summary

- **PROJ-20 gezielt:** 27 bestanden, 1 erwarteter Fehler für BUG-1.
- **Backend vollständig:** 252 bestanden, 1 erwarteter Fehler für BUG-1,
  1 bereits zuvor vorhandener fachlich veralteter PROJ-7-Testfehler
  (`test_multiple_result_types_are_separate_rows` erwartet drei Default-Instrumente,
  während die Anwendung bewusst nur BTC als Default führt).
- **Frontend:** Production Build grün; ESLint der geänderten Dateien grün.
- **Browser:** 15 bestanden, 1 dokumentierter erwarteter Befund (BUG-2).

### Summary

- **Acceptance Criteria:** 9/12 vollständig bestanden.
- **Bugs Found:** 6 total (0 Critical, 2 High, 3 Medium, 1 Low).
- **Security:** Nicht bestanden (unbegrenzte Dekompression/Ausgabe und Temp-Leak).
- **Production Ready:** **NO**.
- **Recommendation:** BUG-1 und BUG-3 zuerst beheben; danach BUG-2, BUG-4 und
  BUG-5 vor erneuter QA. BUG-6 kann separat kosmetisch korrigiert werden.

## Deployment
_To be added by /abc-deploy_
