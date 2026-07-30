# PROJ-21: HAL-Import und Ergebnis-Screening

## Status: In Review
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

**Tested:** 2026-07-30
**Backend:** FastAPI (`TestClient`, env `Dashboard`), Frontend: statischer Code-Review (kein laufender Dev-Server in dieser Session)
**Tester:** QA Engineer (AI)
**Methode:** Code-Review gegen jedes Akzeptanzkriterium + gezielte Reproduktionsskripte gegen die echte Test-DB (`TestClient` + `psycopg`), automatisierte Suite (`pytest`), ESLint.

### Automatisierte Tests
- `backend/tests/test_hal_import.py`, `backend/tests/test_hal_parser.py`: 31/31 grün.
- Gesamte Backend-Suite (`backend/tests`, ohne das netzwerkgebundene `test_hal_sync.py`): 284/284 grün — keine Regression durch PROJ-21.
- `npm run lint` im `nextjs_app`: 5 Errors/1 Warning, aber alle in Dateien **außerhalb** dieses Features (`batches/page.tsx`, `entwuerfe/[id]/page.tsx`, `batch-ausfuehrung.tsx`, `theme-toggle.tsx`, `use-mobile.ts`) — vorbestehend, keine Regression.

### Acceptance Criteria Status

#### Import und Provenienz
- [x] Mehrere `.md` oder genau eine `.zip` wird akzeptiert.
- [x] Andere Dateitypen einzeln mit „Dateityp wird nicht unterstützt.“ gemeldet.
- [x] Ein Parserfehler blockiert Geschwisterdateien nicht (bestätigt durch Test + Probe) — **außer** im Fall von BUG-1 (siehe unten).
- [x] Zusammenfassung zeigt genau einen Status pro Datei.
- [x] Herkunftspfad, Hash, Importzeitpunkt werden gespeichert.
- [x] Gleicher Pfad + gleicher Hash ⇒ `unverändert`, kein Duplikat.
- [x] Gleicher Pfad + geänderter Hash ⇒ neue Importversion, alte bleibt im Audit-Trail.
- [ ] BUG: ZIP-Pfade, die das Archiv verlassen wollen, werden zwar sicher **abgelehnt** (kein Escape, `zf.read()` wird für sie nie aufgerufen), aber **nicht** mit der geforderten Meldung „Unsicherer Dateipfad im Archiv.“ gemeldet — siehe BUG-2.

#### Mindestvertrag und Datenqualität
- [x] Minimalvertrag wird geprüft, fehlende Pflichtfelder → `fehlerhaft`.
- [x] Ausführliches Tabellenformat + kompaktes KPI-Format werden unterstützt (Parser-Tests grün).
- [x] Optionale Felder fehlen ohne Fehler, erscheinen als `null` (Frontend zeigt „–“).
- [x] CAGR-Ableitung inkl. `Net Return ≤ -100%` / ungültiger Zeitraum → nicht verfügbar (`_compute_cagr`, geprüft).
- [x] Calmar `CAGR / abs(MDD)`, `0`-Drawdown → nicht verfügbar.
- [ ] BUG: Vergleichbarkeitsprüfung (`is_comparable`) prüft für HAL-Zeilen nur `fee_pct` und `slippage_ticks` — **`sizing_model` fehlt in der Prüfung komplett**, obwohl die AC explizit „Gebühren, Slippage und Sizing-Modell vollständig“ verlangt. Da der Parser `sizing_model` zusätzlich nie befüllt (siehe Non-Blocking Findings), ist dieser Punkt aktuell praktisch folgenlos, aber die Spec-Abweichung besteht im Code. Ein Abgleich „mit der aktiven Vergleichsgruppe“ (Kohorten-Vergleich) ist zudem gar nicht implementiert — es wird nur auf Feld-Vollständigkeit geprüft, nicht auf Übereinstimmung mit anderen Zeilen.

#### Strategiezuordnung
- [ ] BUG (Critical): Siehe **BUG-1** — kein Datei-Identifier wird geparst, kein Quellenlink-Matching implementiert (`_SOURCE_PATTERN`/`source_match` in `hal_parser.py` wird geparst und dann verworfen, nie im `ParsedResult` gespeichert), und bei eindeutigem Namenstreffer wird **sofort und still zugewiesen** (`assignment_origin="suggestion_accepted"`) statt nur einen Vorschlag zu machen. Mehrfachtreffer werden nicht erkannt — die Query nimmt einfach `ORDER BY version_number DESC LIMIT 1`.
- [x] Nutzer kann ein unzugeordnetes Ergebnis manuell zuweisen (`/hal-results/{id}/assign`, Frontend-Zuordnungs-Tab) — funktioniert für Ergebnisse, die tatsächlich in der Queue landen.
- [x] Zuordnung ist sichtbar/änderbar (`assignment_origin`, Reassign/Unassign getestet).

#### Screening
- [x] HAL-Importe erscheinen in `/results`, Ergebnistyp „HAL-Import“ sichtbar/filterbar.
- [x] Sortino-Spalte vorhanden.
- [x] Standardsortierung Calmar absteigend, `null` immer am Ende (unabhängig von Sortierrichtung).
- [x] Trades/Jahr wird aus Trade-Anzahl + exakter Dauer berechnet.
- [x] `< 6 Trades/Jahr` → Badge „Niedrige Aktivität“, Zeile bleibt sichtbar.
- [x] Erfolgsgruppen-Schwellen (Calmar ≥ 0,8, Sortino ≥ 0,5, ≥ 6 Trades/Jahr) serverseitig zentral definiert (`schemas/hal_import.py`).
- [ ] BUG: Schnellfilter fehlt für **Timeframe** (in der AC-Liste explizit gefordert, im Frontend nicht vorhanden). MTS-Eignung/Robustheitsstatus-Filter fehlen ebenfalls, sind aber aktuell mangels Datenquelle (`mts_compatibility`/`robustness_status` immer `null`) ohnehin funktionslos — vermutlich bewusst auf PROJ-22 ff. verschoben, aber nicht in der Spec vermerkt.
- [x] Calmar bleibt visuell dominant (fett), kein Composite Score, keine automatische Empfehlung.

#### Manuelle Shortlist
- [x] Stern pro Zeile setzt/entfernt Shortlist (`PUT`/`DELETE /shortlist/{id}`), getestet.
- [x] Shortlist an Strategieversion gebunden, alle Runs derselben Version zeigen denselben Zustand.
- [x] Neue Version übernimmt Shortlist-Zustand nicht automatisch (kein Auto-Copy im Code).
- [x] Setzen/Entfernen verändert keine Metrikdaten (reine Zusatztabelle).

### Edge Cases Status
- [x] ZIP mit gültigen/fehlerhaften/fremden Dateien: gültige werden importiert, andere einzeln gemeldet — **außer** bei Wiederholungs-Uploads, siehe BUG-3.
- [ ] BUG: „Zwei Dateien haben denselben Strategienamen, aber unterschiedliche Quellen: beide bleiben unzugeordnet“ — empirisch widerlegt, siehe BUG-1.
- [x] `0` Trades bleibt sichtbar, Aktivität niedrig, Ratios bleiben leer wo nicht berechenbar.
- [x] Kompaktes Format mit mehreren KPIs pro Zeile: bekannte Werte gelesen, unklare nicht geraten (Parser-Tests).
- [x] Testzeitraum < 1 Jahr: Trades/Jahr wird annualisiert (`_compute_trades_per_year`).
- [x] Gelöschte/nicht verfügbare Strategieversion zeigt „Strategieversion nicht verfügbar“ im Frontend-Badge — Backend-Logik vorhanden; über die App aktuell nicht auslösbar, da kein Lösch-Endpoint für Strategieversionen existiert (kein funktionales Risiko heute).

### Security Audit Results
- [x] Kein Auth-Layer nötig (App ist laut PRD single-tenant, kein Mandant) — konsistent mit übrigen Routen.
- [x] Zip-Slip: Pfade, die das Archiv verlassen wollen, werden vor jedem `zf.read()` abgefangen (`_safe_zip_path`) — kein tatsächliches Escape möglich, nur die Nutzermeldung ist falsch (BUG-2).
- [x] ZIP-Größenlimit (100 MB unkomprimiert) und Item-Limit (500) vorhanden.
- [x] Alle SQL-Statements parametrisiert, keine f-String-SQL gefunden.
- [x] Datei-Uploads werden nur im Speicher verarbeitet, keine Persistenz auf Platte, kein MinIO-Zugriff nötig.
- [ ] BUG (Critical, siehe BUG-3): Nicht-parametrisierte Eingabe kann keinen SQL-Angriff auslösen, aber eine unbehandelte DB-Exception (`UniqueViolation`) führt zu einem **500 statt einer sauberen Fehlerbehandlung** und reißt bereits erfolgreich verarbeitete Geschwisterdateien im selben Request per Rollback mit — kein Sicherheits-, aber ein Verfügbarkeits-/Datenintegritätsproblem.

### Bugs Found

#### BUG-1: Stille Auto-Zuordnung statt Vorschlag bei Namensgleichheit, keine Mehrfachtreffer-Prüfung
- **Severity:** Critical
- **Steps to Reproduce:**
  1. Zwei eingefrorene Strategieversionen mit identischem `snapshot->>'name'` anlegen (z. B. zwei unabhängige Strategiefamilien, die zufällig „Trendfolge SMA Kreuz“ heißen).
  2. Eine HAL-Markdown-Datei mit demselben Strategienamen importieren (`POST /hal-results/import`).
  3. Erwartet laut AC: Status `unzugeordnet` (mehrere Treffer ⇒ kein Vorschlag, keine stille Auswahl).
  4. Tatsächlich (empirisch reproduziert mit `TestClient`): `hal_results.strategy_version_id` wird sofort auf eine der beiden Versionen gesetzt (`ORDER BY version_number DESC LIMIT 1`), `assignment_origin = 'suggestion_accepted'`, obwohl niemand einen Vorschlag bestätigt hat. Der Eintrag erscheint **nicht** in `/hal-results/unassigned` und damit nie im Zuordnungs-Tab.
  - Zusätzlich: Selbst im Eindeutig-Treffer-Fall ist das laut Tech-Design (Punkt 12: „Eine stille Falschzuordnung wäre schlimmer als gar keine“) explizit ein „Vorschlag“, kein Auto-Assign — das Frontend (`AssignmentTab`) ist bereits korrekt für den Vorschlag-Flow gebaut („Vorschlag übernehmen“-Button), wird durch dieses Backend-Verhalten aber nie erreicht.
  - Zusätzlich: `_SOURCE_PATTERN`/„Quelle“-Link wird in `hal_parser.py` geparst (`source_match`), aber nirgends im `ParsedResult` gespeichert oder für Matching verwendet — das in der AC geforderte Quellenlink-Matching existiert schlicht nicht.
- **Priority:** Fix before deployment

#### BUG-2: Falsche Fehlermeldung bei unsicherem ZIP-Pfad
- **Severity:** Medium
- **Steps to Reproduce:**
  1. ZIP mit einem Eintrag hochladen, dessen Pfad das Archiv verlassen will (z. B. `../evil.md`).
  2. Erwartet laut AC: „Unsicherer Dateipfad im Archiv.“
  3. Tatsächlich (empirisch reproduziert): Meldung lautet „Dateityp wird nicht unterstützt.“ — identisch mit der Meldung für schlicht falsche Dateitypen. Der String „Unsicherer Dateipfad im Archiv.“ kommt im gesamten Backend nirgends vor (`grep` bestätigt).
  - Kein Sicherheitsrisiko (Datei wird nicht gelesen/extrahiert), aber irreführend bei einer echten Zip-Slip-Attacke oder einem defekten Export — Nutzer kann Ursache nicht unterscheiden.
- **Priority:** Fix before deployment

#### BUG-3: Erneuter Upload eines bereits abgelehnten Files (gleicher Pfad + Hash) crasht den gesamten Importlauf (500) und rollt bereits importierte Geschwisterdateien zurück
- **Severity:** Critical
- **Steps to Reproduce:**
  1. Ein ZIP mit einer nicht unterstützten Datei (z. B. `readme.pdf`) und einer gültigen `.md`-Datei hochladen → beide werden korrekt verarbeitet (`fehlerhaft` / `importiert`).
  2. Denselben Ordner/dasselbe ZIP ein zweites Mal hochladen (realistischer Alltagsfall: Nutzer lädt denselben Hal-Export erneut hoch, weil er neue Ergebnisse ergänzt hat).
  3. Erwartet laut AC: die unveränderte `.pdf` wird wie beim ersten Mal einfach wieder als `fehlerhaft`/nicht unterstützt gemeldet (Dedup-Verhalten wie bei validen Dateien).
  4. Tatsächlich (empirisch reproduziert): `_reject_file` prüft — anders als `_process_one_file` für valide Dateien — **nicht** auf einen bereits existierenden `(origin_path, content_hash)`-Eintrag, sondern versucht immer einen Insert mit `import_version = 1`. Das verletzt den Unique Index `uq_hal_imported_files_path_hash_version` und wirft eine unbehandelte `psycopg.errors.UniqueViolation` → FastAPI liefert `500 Internal Server Error`. Da `import_hal_results` alle Dateien eines Requests in **einer** Transaktion verarbeitet (`with transaction() as cur:`), wird beim Fehler die komplette Transaktion zurückgerollt — auch bereits erfolgreich verarbeitete valide Dateien desselben Requests gehen verloren. Das widerspricht direkt der AC „Jede Datei wird unabhängig verarbeitet; ein Parserfehler verhindert nicht den Import gültiger Geschwisterdateien.“ Bei ca. 300 Dateien pro Ordner (Kernszenario der Spec) ist ein wiederholter Upload nach dem ersten Mal praktisch garantiert, sobald der Ordner auch nur eine einzige nicht unterstützte Datei enthält.
- **Priority:** Fix before deployment

### Non-Blocking Findings (nicht als eigene BUGs gezählt, aber notierenswert)
- `sizing_model` wird vom Parser nie befüllt (kein Lesepfad in `hal_parser.py` dafür vorhanden), obwohl das Datenmodell und die Vergleichbarkeitsprüfung dieses Feld referenzieren.
- Namensbasiertes Matching in `_insert_hal_result`/`_suggest_version` ist ein exakter String-Vergleich, nicht „normalisiert“ (kein Trim/Case-Fold) wie in der AC gefordert — in der Praxis meist unkritisch, da Strategienamen aus derselben App-Quelle stammen.

### Summary
- **Acceptance Criteria:** 25/29 geprüfte Teilkriterien bestanden, 4 mit Bugs (Zuordnung-Eindeutigkeit, ZIP-Fehlermeldung, Vergleichbarkeitsprüfung `sizing_model`, Timeframe-Filter).
- **Bugs Found:** 3 total (2 Critical, 1 Medium)
- **Security:** Keine Auth-relevanten Lücken (App ist single-tenant); ein Verfügbarkeits-/Integritätsproblem (BUG-3) mit Sicherheits-Nebenaspekt (unbehandelte Exception statt kontrollierter Fehlerantwort).
- **Production Ready:** NO
- **Recommendation:** BUG-1 und BUG-3 vor Deployment fixen (beide sind Kernversprechen der Spec: keine stille Falschzuordnung, kein Abbruch des gesamten Imports durch eine einzelne Datei). BUG-2 sollte im selben Rutsch mit BUG-3 behoben werden (beide sitzen in derselben Reject-Pipeline). Timeframe-Filter und `sizing_model`-Lücke können optional in derselben Iteration mitgenommen werden.

## QA Re-Test nach Bugfixes

**Tested:** 2026-07-30
**Ergebnis:** Die drei ursprünglich reproduzierten Fehlerpfade sind behoben, PROJ-21 ist wegen neuer beziehungsweise verbliebener High-Bugs aber weiterhin nicht production-ready.

### Verifikation der Fixes

- [x] Eindeutiger normalisierter Namenstreffer bleibt unzugeordnet und wird nur vorgeschlagen.
- [x] Gleicher Name in mehreren Strategiefamilien erzeugt keinen Vorschlag und keine stille Auswahl.
- [x] Wiederholter Upload eines ZIPs mit abgelehnter Datei liefert `unverändert` statt `500`; gültige Geschwisterdateien bleiben erhalten.
- [x] Unsicherer ZIP-Pfad wird mit „Unsicherer Dateipfad im Archiv.“ gemeldet.
- [x] `sizing_model` wird in die Vollständigkeitsprüfung von `is_comparable` einbezogen.
- [x] Timeframe-Schnellfilter ist vorhanden.

### Automatisierte Checks

- PROJ-21 Backend: **34/34 grün** (`test_hal_import.py`, `test_hal_parser.py`).
- Backend-Regressionssuite ohne bewusst netzwerkgebundenes `test_hal_sync.py`: **287/287 grün**.
- `git diff --check`: **grün**.
- Next.js `npm run build`: **fehlgeschlagen** wegen drei TypeScript-Fehlern in `app/ergebnisse/page.tsx`.
- ESLint: weiterhin 5 vorbestehende Errors/1 Warning außerhalb PROJ-21; keine zusätzlichen Lint-Funde in PROJ-21.
- Browser-/Responsive-Test nicht sinnvoll durchführbar, solange der Produktionsbuild fehlschlägt.

### Verbliebene Bugs

#### BUG-4: PROJ-21-Ergebnisseite blockiert den Frontend-Produktionsbuild

- **Severity:** High
- **Reproduktion:** `cd nextjs_app && npm run build`
- **Ist:** TypeScript meldet in `app/ergebnisse/page.tsx` an den Zeilen 742, 764 und 823, dass `TooltipTrigger` die Prop `asChild` nicht unterstützt. Der Build endet mit Exit-Code 1.
- **Soll:** Der Next.js-Produktionsbuild läuft durch.
- **Priority:** Fix before deployment

#### BUG-5: Ungültiges Update wird als aktualisiert gemeldet und blendet das letzte gültige Ergebnis aus

- **Severity:** High
- **Reproduktion:**
  1. Gültige HAL-Datei importieren.
  2. Unter demselben Pfad geänderten, aber unvollständigen Inhalt hochladen.
  3. API-Antwort und `/results` prüfen.
- **Ist:** Der zweite Import erhält Status `aktualisiert` plus Parserfehler. Die bisherige Importversion wird vor dem Parsen auf `is_current=false` gesetzt, die ungültige neue Datei auf `is_current=true`; da kein `hal_results`-Datensatz entsteht, verschwindet das zuvor gültige Ergebnis vollständig aus `/results`.
- **Soll:** Die neue Datei erhält `fehlerhaft`; das letzte gültige Ergebnis bleibt die aktuelle Analyseversion.
- **Empirisch:** Zweiter Request `201`, Datei-Status `aktualisiert`, `visible_results: 0`.
- **Priority:** Fix before deployment

#### BUG-1 teilweise offen: Identifier- und Quellenlink-Matching fehlen

- **Severity:** High
- **Behoben:** Keine stille Auto-Zuordnung mehr; normalisierte Namensvorschläge erkennen Mehrdeutigkeit zwischen Strategiefamilien.
- **Offen:** Der Parser übernimmt keinen stabilen Strategieversions-Identifier. `source_match` wird weiterhin nur erzeugt und verworfen; der Quellenlink wird nicht für Vorschläge verwendet. Damit sind die ersten beiden Zuordnungs-ACs nur teilweise erfüllt.
- **Priority:** Fix before deployment

### Weitere offene AC-Abweichungen

- **Medium:** `sizing_model` wird zwar jetzt geprüft, aber vom HAL-Parser nie befüllt. HAL-Ergebnisse können deshalb aktuell nie direkt vergleichbar oder Teil der Erfolgsgruppe werden.
- **Medium:** Vergleichbarkeit prüft nur Feldvollständigkeit, nicht die geforderte Übereinstimmung mit der aktiven Vergleichsgruppe.
- **Medium:** Schnellfilter für MTS-Eignung und Robustheitsstatus fehlen weiterhin; die zugehörigen Backend-Felder sind immer `null`.

### Re-Test Summary

- **Ursprüngliche Bugs:** BUG-2 und BUG-3 vollständig behoben; BUG-1 teilweise behoben.
- **Neue Bugs:** 2 High.
- **Verbliebene Abweichungen:** 1 High, 3 Medium.
- **Security:** Zip-Slip-Abwehr weiterhin wirksam; keine neue Security-Lücke gefunden.
- **Production Ready:** **NO**
- **Status:** **In Review**

## Deployment
_To be added by /deploy_
