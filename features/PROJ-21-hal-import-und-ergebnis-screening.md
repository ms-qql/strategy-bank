# PROJ-21: HAL-Import und Ergebnis-Screening

## Status: In Progress
**Created:** 2026-07-30
**Last Updated:** 2026-07-30

## Dependencies
- Requires: PROJ-3 (Verifizierung und Versionierung) — liefert bestehende Strategieversionen für die Zuordnung.
- Requires: PROJ-7 (Ergebnisvergleich) — liefert die vorhandene globale Ergebnisansicht und Vergleichsregeln.
- Related: PROJ-19 (Hal-Vault-Sync für Quellen) — bestätigt, dass die produktive App keinen direkten Zugriff auf den lokalen Hal-Vault besitzt.

## Ziel

Backtestergebnisse aus dem Hal-Ordner `02_Backtests` werden per Browser-Upload
in die Strategy Bank übernommen und in der bestehenden Ergebnisansicht
gleichwertig, aber mit klarer Import-Provenienz dargestellt. Der Nutzer kann
rund 300 Ergebnisse in höchstens fünf Minuten auf eine nachvollziehbare
Shortlist reduzieren.

## User Stories

- Als Trader möchte ich mehrere Hal-Markdown-Dateien oder ein ZIP mit diesen Dateien hochladen, damit die produktive App keinen direkten Vault-Zugriff benötigt.
- Als Trader möchte ich pro Datei sehen, ob sie importiert, unverändert, aktualisiert oder fehlerhaft ist, damit ein einzelner Fehler den restlichen Import nicht blockiert.
- Als Trader möchte ich importierte Ergebnisse vorhandenen Strategieversionen zuordnen, damit Backtest und verifizierte Regel zusammengehören.
- Als Trader möchte ich nach Calmar, Sortino, Return, Drawdown und Trades vergleichen, damit Downside-Qualität vor Bruttorendite steht.
- Als Trader möchte ich eine feste Erfolgsgruppe und Hinweise auf geringe Aktivität sehen, ohne Kandidaten automatisch auszublenden.
- Als Trader möchte ich Strategieversionen manuell auf eine Shortlist setzen und wieder entfernen, damit meine Auswahl von automatischen Schwellen getrennt bleibt.

## Acceptance Criteria

### Import und Provenienz

- [ ] Der Import akzeptiert mehrere `.md`-Dateien oder genau eine `.zip`-Datei mit Markdown-Dateien.
- [ ] Andere Dateitypen werden nicht verarbeitet und mit „Dateityp wird nicht unterstützt.“ pro Datei gemeldet.
- [ ] Jede Datei wird unabhängig verarbeitet; ein Parserfehler verhindert nicht den Import gültiger Geschwisterdateien.
- [ ] Pro Datei zeigt eine Zusammenfassung genau einen Status: `importiert`, `unverändert`, `aktualisiert` oder `fehlerhaft`.
- [ ] Jedes importierte Ergebnis speichert ursprünglichen Dateinamen beziehungsweise relativen ZIP-Pfad, Inhaltshash und Importzeitpunkt.
- [ ] Derselbe normalisierte Pfad mit demselben Inhaltshash erzeugt kein zweites Ergebnis und erhält den Status `unverändert`.
- [ ] Derselbe normalisierte Pfad mit geändertem Inhalt erzeugt eine neue Importversion; die vorherige Version bleibt im Audit-Trail erhalten, erscheint aber nicht doppelt in der aktuellen Analyse.
- [ ] ZIP-Pfade dürfen das Importarchiv nicht verlassen; betroffene Einträge werden mit „Unsicherer Dateipfad im Archiv.“ abgelehnt.

### Mindestvertrag und Datenqualität

- [ ] Ein auswertbares Ergebnis benötigt mindestens Strategiename, Asset beziehungsweise Provider-Symbol, Timeframe, Beginn und Ende des Testzeitraums, Net Return, Max Drawdown und Trade-Anzahl.
- [ ] Prozent-, Währungs- und Ganzzahlwerte aus dem ausführlichen Tabellenformat und dem vorhandenen kompakten KPI-Format werden unterstützt.
- [ ] Sortino Ratio, Report-Link, Parameter, Long-/Short-Breakdown und Pine-Code dürfen fehlen; das Ergebnis bleibt sichtbar und zeigt die jeweils fehlenden Angaben als `nicht verfügbar`.
- [ ] CAGR darf aus Net Return und exaktem Testzeitraum abgeleitet werden. Bei Net Return `≤ -100 %`, ungültigem Zeitraum oder fehlendem Eingangswert bleibt CAGR nicht verfügbar.
- [ ] Calmar folgt unverändert PROJ-7: `CAGR / abs(Max Drawdown)`; bei Drawdown `0` oder fehlendem Eingangswert ist Calmar nicht verfügbar.
- [ ] Ein Ergebnis gilt nur dann als direkt vergleichbar, wenn Asset/Provider, Timeframe, Zeitraum, Gebühren, Slippage und Sizing-Modell vollständig vorliegen und mit der aktiven Vergleichsgruppe übereinstimmen.
- [ ] Unvollständige oder abweichende Profile bleiben sichtbar, werden aber nicht still in Erfolgsquoten oder Kohorten eingerechnet.

### Strategiezuordnung

- [ ] Ein stabiler Strategieversions-Identifier aus der Datei hat Vorrang vor allen anderen Zuordnungsmerkmalen.
- [ ] Fehlt der Identifier, darf die App anhand des Quellenlinks beziehungsweise eines normalisierten exakten Strategienamens genau einen Vorschlag machen.
- [ ] Kein oder mehrere mögliche Treffer führen zum Status `unzugeordnet`; die App trifft keine stille Auswahl.
- [ ] Der Nutzer kann ein unzugeordnetes Ergebnis manuell einer bestehenden unveränderlichen Strategieversion zuweisen.
- [ ] Die manuelle Zuordnung ist sichtbar, änderbar und im Audit-Trail nachvollziehbar.

### Screening

- [ ] Importierte und intern erzeugte Ergebnisse erscheinen in derselben PROJ-7-Ergebnisansicht; der Ergebnistyp `HAL-Import` ist sichtbar und filterbar.
- [ ] Sortino Ratio wird als zusätzliche dominante Spalte neben Calmar, Net Return, Max Drawdown und Trades angezeigt.
- [ ] Die Standardsortierung ist Calmar absteigend; nicht verfügbare Werte stehen am Ende.
- [ ] `Trades pro Jahr` wird aus Trade-Anzahl und exakter Testdauer berechnet.
- [ ] Weniger als `6 Trades pro getestetem Jahr` erzeugen das Badge `Niedrige Aktivität`; die Zeile bleibt sichtbar.
- [ ] Der Filter `Erfolgsgruppe` enthält nur direkt vergleichbare Ergebnisse mit Calmar `≥ 0,8`, Sortino `≥ 0,5` und mindestens `6 Trades pro getestetem Jahr`.
- [ ] Schnellfilter existieren für Erfolgsgruppe, Shortlist, Kategorie, Richtung, Instrument, Timeframe, MTS-Eignung, Robustheitsstatus und Ergebnistyp.
- [ ] Calmar ist das stärkste visuelle Signal; es gibt keinen Composite Score und keine automatische Gewinnerempfehlung.

### Manuelle Shortlist

- [ ] Der Nutzer kann eine Strategieversion aus jeder Ergebniszeile mit einem Stern zur Shortlist hinzufügen oder entfernen.
- [ ] Die Shortlist ist an die Strategieversion gebunden; alle zugehörigen Runs zeigen denselben Shortlist-Zustand.
- [ ] Eine neue Version derselben Strategiefamilie übernimmt den Shortlist-Zustand nicht automatisch.
- [ ] Das Setzen oder Entfernen verändert keine Metrik, Erfolgsgruppenzugehörigkeit oder historischen Ergebnisdaten.

## Edge Cases

- Eine ZIP-Datei enthält gültige, fehlerhafte und fremde Dateien: gültige Dateien werden importiert, alle anderen einzeln gemeldet.
- Zwei Dateien haben denselben Strategienamen, aber unterschiedliche Quellen: beide bleiben unzugeordnet, bis der Nutzer entscheidet.
- Ein Ergebnis enthält `0` Trades: es bleibt sichtbar; Trades/Jahr ist `0`, Aktivität ist niedrig und nicht berechenbare Ratios bleiben leer.
- Ein kompaktes HAL-Dokument enthält mehrere KPIs in einer Tabellenzeile: bekannte Werte werden gelesen; nicht eindeutig zuordenbare Werte werden nicht geraten.
- Ein Ergebnis besitzt hohe Kennzahlen, aber kein vollständiges Vergleichsprofil: es erscheint nicht in der Erfolgsgruppe.
- Der Testzeitraum ist kürzer als ein Jahr: Trades/Jahr wird anhand der tatsächlichen Dauer annualisiert und als abgeleitete Anzeige gekennzeichnet.
- Eine bereits shortlisted Strategieversion wird gelöscht oder ist nicht mehr verfügbar: der Import bleibt erhalten und zeigt `Strategieversion nicht verfügbar`.

## Non-Goals

- Kein direkter Dateisystemzugriff der produktiven App auf `/home/dev/tools/Hal`.
- Keine Ausführung oder Wiederholung externer Backtests.
- Keine KI-Reparatur fehlerhafter Ergebnisdateien.
- Keine kausalen Aussagen aus Screening oder Erfolgsgruppe.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-30 · **Stack:** Next.js 16 (App Router, shadcn/ui) + FastAPI + PostgreSQL (Dokploy, single-tenant, kein MinIO) · **Branch:** dev

### Ausgangslage im Bestand

Die heutige Ergebnisansicht (PROJ-7) liest ausschließlich intern erzeugte Läufe:
`runs` verbunden mit `batches`, `backtest_profiles` und `backtest_executions`.
Jede Ergebniszeile setzt also einen Batch, ein Backtest-Profil und eine
Strategieversion voraus. Ein HAL-Import hat nichts davon — er ist ein fertiges,
extern erzeugtes Ergebnis, das anfangs sogar ohne Strategiezuordnung existieren
darf. Das ist die zentrale Designspannung dieses Features.

Ebenfalls bereits vorhanden und wiederverwendet:
- Der Datei-Upload der Quellenerfassung (Multipart-Upload, PROJ-14/PROJ-20) als Muster für Datei-Entgegennahme.
- Die ZIP-Verarbeitung des Dokumentkonverters (PROJ-20) als Muster für Archiv-Handhabung.
- Die Metrikberechnung der Ergebnisansicht (CAGR-Ableitung, Calmar) — sie wird gemeinsam genutzt, nicht dupliziert.
- Der Audit-Trail (PROJ-8) als Ablage für nachvollziehbare Nutzerentscheidungen.

### A) Komponentenstruktur

Neue Seite `/hal-import` (eigener Sidebar-Eintrag, Entscheidung des Nutzers):

```
HalImportSeite
├── ImportDropzone (Mehrfachauswahl .md oder genau eine .zip)
├── ImportBericht (erscheint nach jedem Upload)
│   └── DateiZeile  → Status-Badge: importiert / unverändert / aktualisiert / fehlerhaft
│                     plus Klartextgrund bei Fehler
├── ZuordnungsQueue (nur unzugeordnete Importe)
│   └── ZuordnungsZeile → Strategieversion suchen und zuweisen, Zuordnung ändern
└── ImportHistorie (frühere Importläufe, chronologisch, mit Dateiherkunft)
```

Erweiterung der bestehenden Ergebnisansicht `/ergebnisse` (keine neue Seite):

```
ErgebnisseSeite (bestehend)
├── SchnellfilterLeiste (erweitert)
│   └── neu: Erfolgsgruppe · Shortlist · MTS-Eignung · Robustheitsstatus
│       bestehend: Kategorie · Richtung · Instrument · Timeframe · Ergebnistyp (neu: „HAL-Import")
├── ErgebnisTabelle (erweitert)
│   ├── neue Spalte: Sortino Ratio
│   ├── neue Spalte: Trades pro Jahr
│   ├── neue Spalte: Stern (Shortlist an/aus)
│   ├── Calmar bleibt das visuell stärkste Signal, Standardsortierung Calmar absteigend
│   └── ZeilenBadges: „HAL-Import" · „Niedrige Aktivität" · „Nicht vergleichbar" · „Strategieversion nicht verfügbar"
└── HerkunftsPopover (nur HAL-Zeilen: Dateiname bzw. ZIP-Pfad, Importzeitpunkt, Importversion)
```

Bewusst nicht gebaut: keine Gewinnerempfehlung, kein Composite Score, keine
automatische Ausblendung von Kandidaten. Alles bleibt sichtbar, Schwellen
kennzeichnen nur.

### B) Datenmodell (Klartext)

**Importlauf** — ein Upload-Vorgang:
- Zeitpunkt, Anzahl Dateien, Zusammenfassung der vier Statuswerte
- dient der Historie und dem Audit-Trail

**Importierte Ergebnisdatei** — eine Zeile je Datei je Importversion:
- normalisierter Herkunftspfad (Dateiname oder relativer ZIP-Pfad)
- Inhaltshash, Importzeitpunkt, Importversionsnummer
- Verweis auf den Importlauf
- Verarbeitungsstatus und, bei Fehlern, der Klartextgrund
- Kennzeichen, ob diese Importversion die aktuell gültige ist; ältere Versionen bleiben
  als Audit-Trail erhalten, erscheinen aber nicht in der Analyse
- Regel: gleicher Pfad + gleicher Hash ⇒ `unverändert`, keine neue Zeile.
  Gleicher Pfad + anderer Hash ⇒ neue Importversion, alte wird abgelöst.

**Importiertes Ergebnis** — die ausgewerteten Inhalte einer gültigen Datei:
- Pflichtangaben: Strategiename, Asset bzw. Provider-Symbol, Timeframe, Beginn und Ende
  des Testzeitraums, Net Return, Max Drawdown, Trade-Anzahl. Fehlt eine davon,
  ist die Datei `fehlerhaft` und wird nicht als Ergebnis geführt.
- Optionale Angaben: Sortino Ratio, Report-Link, Parameter, Long-/Short-Aufteilung,
  Pine-Code, Richtung. Fehlende Angaben werden als „nicht verfügbar" angezeigt, nie geraten.
- Vergleichsprofil: Gebühren, Slippage, Sizing-Modell. Nur wenn diese zusammen mit
  Asset, Timeframe und Zeitraum vollständig vorliegen und zur aktiven Vergleichsgruppe
  passen, gilt das Ergebnis als direkt vergleichbar.
- Zuordnung: optionaler Verweis auf eine unveränderliche Strategieversion, dazu die
  Herkunft der Zuordnung (aus Datei-Identifier, aus Vorschlag bestätigt, manuell gesetzt).
  Ohne Verweis lautet der Zustand `unzugeordnet`.

**Shortlist-Eintrag** — Verweis auf genau eine Strategieversion plus Zeitpunkt.
An die Version gebunden, nicht an die Strategiefamilie und nicht an einen einzelnen Lauf:
alle Läufe derselben Version zeigen denselben Stern, eine neue Version startet ohne Stern.

Gespeichert wird alles in PostgreSQL. Kein MinIO: hochgeladene Dateien werden
im Arbeitsspeicher verarbeitet, gespeichert werden nur Herkunftspfad, Hash und die
ausgewerteten Werte — die Originaldatei bleibt im Hal-Vault des Nutzers.

### C) API-Zuschnitt

```
POST /hal-results/import      → Dateien entgegennehmen (mehrere .md oder genau eine .zip),
                                pro Datei einen Status zurückgeben
GET  /hal-results/imports     → Importhistorie
GET  /hal-results/unassigned  → unzugeordnete Ergebnisse für die Zuordnungs-Queue
POST /hal-results/{id}/assign → Ergebnis manuell einer Strategieversion zuweisen oder Zuweisung lösen

GET  /results                 → bestehend, liefert künftig interne Läufe UND HAL-Importe
                                in derselben Zeilenform, unterschieden durch den Ergebnistyp

GET    /shortlist                            → alle shortlisted Strategieversionen
PUT    /shortlist/{strategy_version_id}      → Stern setzen
DELETE /shortlist/{strategy_version_id}      → Stern entfernen
```

Die Ergebniszeile aus `/results` wird erweitert um: Sortino Ratio, Trades pro Jahr,
Vergleichbarkeitskennzeichen, Erfolgsgruppen-Kennzeichen, Shortlist-Zustand und die
Importherkunft. Felder, die es nur für interne Läufe gibt (Batch-Profil, Richtungsmodus,
Laufstatus), werden für HAL-Zeilen leer geliefert statt erfunden.

Kein Authentifizierungs-Layer: die App ist laut PRD single-tenant und hat weder
Mandanten noch Login. Alle Endpunkte folgen dem bestehenden Muster der übrigen Routen.

### D) Technische Entscheidungen (mit Begründung)

1. **Eigene Tabellen statt künstlicher Läufe.** HAL-Ergebnisse werden nicht in `runs`
   gepresst. Ein Lauf setzt Batch, Profil und Strategieversion voraus — ein Import hat
   nichts davon und darf sogar unzugeordnet bleiben. Künstliche Platzhalter-Batches
   würden Batch-Ansicht, Credit-Gate und Audit-Trail verfälschen. Zusammengeführt wird
   erst in der Leseansicht.
2. **Zusammenführung in der Leseschicht.** `/results` liefert beide Quellen in einer
   gemeinsamen Zeilenform. So bleibt die Ergebnisansicht eine Ansicht, Filter und
   Sortierung gelten für beide Welten, und der Ergebnistyp „HAL-Import" macht die
   Herkunft trotzdem jederzeit sichtbar und filterbar.
3. **Deterministischer Parser, keine KI.** Die Hal-Dateien sind eigene Erzeugnisse mit
   bekanntem Aufbau (ausführliche Tabelle und kompaktes KPI-Format). Ein regelbasierter
   Leser ist reproduzierbar, kostenlos und erfindet nichts. Unklare Werte bleiben leer —
   das ist ausdrücklich gewünscht, eine KI-Reparatur ist Non-Goal.
4. **Hash plus Pfad als Identität.** Der Nutzer lädt denselben Ordner mehrfach hoch.
   Ohne Dedup entstünden Geisterzeilen und falsche Erfolgsquoten. Pfad plus Inhaltshash
   trennt „schon da" von „hat sich geändert", ohne dass der Nutzer buchführen muss.
5. **Neue Importversion statt Überschreiben.** Ein geänderter Backtest ersetzt den alten
   Wert nicht still. Die alte Version bleibt im Audit-Trail lesbar, nur die neueste zählt
   in der Analyse — dieselbe Append-only-Logik, die schon für Strategieversionen gilt.
6. **Archivpfade werden geprüft.** Ein ZIP kann Pfade enthalten, die aus dem Archiv
   hinausführen. Solche Einträge werden abgelehnt, bevor irgendetwas gelesen wird.
7. **Ein Fehler blockiert nichts.** Jede Datei wird für sich verarbeitet. Bei rund 300
   Dateien ist ein Abbruch beim ersten Formatfehler praktisch unbrauchbar.
8. **Kennzeichnen statt Ausblenden.** Niedrige Aktivität, fehlende Vergleichbarkeit und
   fehlende Werte erzeugen Badges. Ausgeblendet wird nur, was der Nutzer aktiv wegfiltert.
   Die Erfolgsgruppe ist ein Filter, kein Löschkriterium.
9. **Erfolgsgruppe und Badges werden serverseitig berechnet.** Schwellen (Calmar ≥ 0,8,
   Sortino ≥ 0,5, mindestens 6 Trades pro Jahr) gehören an eine Stelle, damit
   Ergebnisansicht, spätere Regime-Analyse (PROJ-22) und Erfolgsfaktorenanalyse (PROJ-23)
   dieselbe Definition benutzen. Die Filter selbst bleiben clientseitig, wie heute schon.
10. **Metrikberechnung wird geteilt, nicht kopiert.** CAGR-Ableitung und Calmar folgen
    unverändert PROJ-7. Beide Ergebnisarten laufen durch dieselbe Berechnung, sonst
    driften interne und importierte Zahlen auseinander.
11. **Shortlist an der Strategieversion.** Ein Stern bewertet die Regel, nicht einen
    einzelnen Lauf. Deshalb hängt er an der unveränderlichen Version — und wird von einer
    neuen Version bewusst nicht geerbt, weil eine geänderte Regel eine neue Entscheidung ist.
12. **Zuordnung nur bei Eindeutigkeit.** Identifier aus der Datei schlägt alles andere.
    Ohne Identifier darf höchstens ein Vorschlag entstehen; mehrere oder null Treffer
    bedeuten `unzugeordnet`. Eine stille Falschzuordnung wäre schlimmer als gar keine,
    weil sie Backtest und verifizierte Regel dauerhaft falsch verknüpft.

### E) Abhängigkeiten

- Backend: keine neuen Pakete. ZIP-Verarbeitung und Hashing sind Standardbibliothek,
  der Multipart-Upload ist im Bestand vorhanden.
- Frontend: keine neuen Pakete. Benötigte shadcn/ui-Bausteine (Table, Badge, Tooltip,
  Sheet, Input, Checkbox, Tabs) sind bereits installiert.
- Datenbank: eine neue Migration mit den vier oben beschriebenen Tabellen samt Indizes
  auf Herkunftspfad, Hash und Strategieversion.

### F) Auswirkungen auf Bestehendes

- Die Ergebniszeile bekommt zusätzliche Felder und einige bisher pflichtige Felder werden
  optional. Die bestehende Ergebnisansicht muss darauf vorbereitet werden, bevor die
  erste HAL-Zeile ankommt.
- Die Schwelle für „niedrige Aktivität" wechselt von einer festen Trade-Anzahl auf
  Trades pro getestetem Jahr. Das ändert Badges auch bei bestehenden internen Läufen —
  gewollt, weil ein Wert ohne Zeitbezug nicht vergleichbar ist.
- Sidebar bekommt einen Eintrag „HAL-Import".
- PROJ-22 bis PROJ-25 bauen auf den hier entstehenden importierten Ergebnissen auf.

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
