# PROJ-20: PDF, EPUB und MOBI als Markdown importieren

## Status: Architected
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
_To be added by /abc-qa_

## Deployment
_To be added by /abc-deploy_
