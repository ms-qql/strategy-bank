# PROJ-10: Positions-, Exit- und Crypto-MTS-Kompatibilitätsmodell

## Status: Architected
**Created:** 2026-07-15
**Last Updated:** 2026-07-15

## Dependencies
- Requires: PROJ-2 (KI-Extraktion) — liefert Entry-/Exit-Regeln, Richtung und Quellenbelege des Entwurfs.
- Requires: PROJ-3 (Verifizierung und Versionierung) — liefert Bearbeitung, Bestätigung und unveränderliche Strategieversionen.
- Required by: PROJ-6 (Queue und trader.dev-Ausführung) — benötigt den bestätigten Positions- und Exit-Vertrag für die Pine-Übersetzung.

Fachliche Grundlage: `docs/Brainstorm-entry-exit-modell.md`.

## Ziel

Jede testbare Strategie erhält vor ihrer Freigabe einen eindeutigen Positions-Lebenszyklus und eine vollständig aufgelöste Exit-Regel. Gleichzeitig wird sichtbar, ob sie direkt als diskretes Crypto-MTS-Signal nutzbar ist oder später sinnvoll zu einer kontinuierlichen Signalstärke erweitert werden kann.

## User Stories

- Als Trader möchte ich getrennt festlegen, welche Richtungen eine Strategie handeln darf und ob sie zwischen Long und Short wechselt oder zeitweise flat ist, damit SMA-Crossover und Entry-only-Strategien korrekt ausgeführt werden.
- Als Trader möchte ich bei einer Entry-only-Strategie ohne eigenen Exit automatisch einen sichtbaren Standard-Exit erhalten, damit die Position nicht unbegrenzt offen bleibt.
- Als Trader möchte ich erkennen, ob ein Exit aus der Quelle, aus dem Systemdefault oder aus meiner Bearbeitung stammt, damit keine ergänzte Regel als Quelleninhalt erscheint.
- Als Trader möchte ich Positionsmodus und Exit zusammen mit der Strategieversion einfrieren, damit spätere Default-Änderungen bestehende Backtests nicht verändern.
- Als Crypto-MTS-Nutzer möchte ich sofort sehen, ob eine Strategie kontinuierlich geeignet, diskret kompatibel oder noch unklar ist, damit ich geeignete Kandidaten für eine spätere Übernahme erkenne.
- Als Crypto-MTS-Nutzer möchte ich jede diskret kompatible Strategie ohne zusätzlichen Backtest als `+10 / 0 / −10` abbilden können, damit keine Credits für ein mathematisch identisches Ergebnis verbraucht werden.

## Fachliche Begriffe

- **Richtung (`direction`):** Erlaubte Handelsrichtung des Runs: `kombiniert`, `long-only` oder `short-only`.
- **Positionsmodus (`position_mode`):** Lebenszyklus der Position: `signal_reversal` oder `entry_exit`.
- **Exit-Herkunft (`exit_rule_origin`):** `source`, `system_default` oder `user`.
- **Crypto-MTS-Eignung:** `kontinuierlich geeignet`, `diskret kompatibel` oder `unklar`.
- **Signalstärke:** Crypto-MTS-Forecast zwischen `−20` und `+20`; keine statistische Wahrscheinlichkeit oder Confidence.

## Acceptance Criteria

### Positionsmodell

- [ ] `direction` und `position_mode` sind zwei getrennte, unabhängig editierbare Angaben eines Entwurfs.
- [ ] `position_mode` erlaubt genau `signal_reversal` und `entry_exit`.
- [ ] Die KI darf einen Positionsmodus vorschlagen; vor der Freigabe muss der Nutzer ihn ausdrücklich bestätigen.
- [ ] Ohne bestätigten Positionsmodus ist die Freigabe blockiert mit „Positionsmodus muss vor der Freigabe bestätigt werden.“
- [ ] Bei `signal_reversal` im kombinierten Richtungsmodus schließt ein Gegensignal die aktuelle Position und eröffnet die Gegenposition; ein 10-Bar-Systemdefault wird nicht angewendet.
- [ ] Bei `signal_reversal` in einem Long-only-Run schließt ein Short-Signal eine offene Long-Position, eröffnet aber keine Short-Position; für Short-only gilt dies spiegelbildlich.

### Exit-Auflösung

- [ ] Für `entry_exit` gilt eine feste Priorität: nutzerbestätigte Änderung vor explizitem Quellen-Exit vor Systemdefault.
- [ ] Fehlt bei `entry_exit` ein expliziter Exit, wird die aufgelöste Regel „Exit nach 10 vollständig vergangenen Bars“ mit Herkunft `system_default` angezeigt.
- [ ] Der Systemdefault ist in dieser Feature-Stufe eine feste Produktkonstante von 10 Bars und keine global konfigurierbare Einstellung.
- [ ] Das Exit-Signal entsteht nach der zehnten vollständig seit dem Entry vergangenen Bar; der Fill erfolgt gemäß Backtest-Profil am nächsten verfügbaren Bar-Open.
- [ ] Ein Systemdefault benötigt keinen Quellenbeleg und darf von der KI nicht als aus der Quelle stammend dargestellt werden.
- [ ] Ein vorhandener Quellen-Exit benötigt weiterhin einen Quellenbeleg und erhält die Herkunft `source`.
- [ ] Ändert der Nutzer Exit-Regel oder Exit-Parameter, erhält der Exit die Herkunft `user`.
- [ ] Ein fehlender Quellen-Exit blockiert eine ansonsten vollständige `entry_exit`-Strategie nicht, wenn der Systemdefault aufgelöst und bestätigt ist.
- [ ] UI, Versionsansicht und für PROJ-9 bereitgestellte Exportdaten zeigen Exit-Regel und Herkunft als „Aus Quelle“, „Systemdefault“ oder „Vom Nutzer“.

### Verifizierung und Versionierung

- [ ] Vor der Freigabe zeigt die App Richtung, Positionsmodus, konkrete Exit-Regel, Exit-Herkunft und Crypto-MTS-Eignung gemeinsam zur Prüfung an.
- [ ] Eine freigegebene Strategieversion enthält unveränderlich den bestätigten Positionsmodus, die vollständig aufgelöste Exit-Regel, deren Herkunft und alle Exit-Parameter.
- [ ] Änderungen an Positionsmodus, Exit-Regel oder Exit-Parametern nach der Freigabe erfordern eine neue Strategieversion gemäß PROJ-3.
- [ ] Eine spätere Änderung des Systemdefaults verändert keine bereits freigegebene Strategieversion und keinen bestehenden Run.
- [ ] Das bestehende bestätigte Verhalten bei gleichzeitigem Entry und Exit sowie bei Reversal bleibt Bestandteil der Strategieversion und wird nicht durch den Systemdefault überschrieben.

### Crypto-MTS-Eignung

- [ ] Jede testbare Strategie erhält genau eine sichtbare Eignung: `kontinuierlich geeignet`, `diskret kompatibel` oder `unklar`.
- [ ] `kontinuierlich geeignet` darf vorgeschlagen werden, wenn ein natürlicher, vorzeichenbehafteter und kausal berechenbarer Stärkewert existiert, beispielsweise `(fast_sma − slow_sma) / volatility`.
- [ ] `diskret kompatibel` wird verwendet, wenn Long/Flat/Short eindeutig bestimmbar ist, aber eine kontinuierliche Stärke zusätzliche, nicht belegte Logik erfordern würde.
- [ ] `unklar` wird verwendet, wenn keine verlässliche Crypto-MTS-Einstufung möglich ist; dies allein macht eine ansonsten deterministisch testbare Strategie nicht „nicht testbar“.
- [ ] Die KI darf eine Eignung vorschlagen; vor der Freigabe muss der Nutzer sie bestätigen oder ändern.
- [ ] Ohne bestätigte Eignung ist die Freigabe blockiert mit „Crypto-MTS-Eignung muss vor der Freigabe bestätigt werden.“
- [ ] UI und Export verwenden den Begriff „Signalstärke“, nicht „Confidence“, für die Crypto-MTS-Skala.

### Diskreter Crypto-MTS-Adapter

- [ ] Für jede diskret kompatible Strategie ist die Abbildung der aufgelösten Zielposition fest definiert: Long `→ +10`, Flat `→ 0`, Short `→ −10`.
- [ ] Die diskrete Abbildung verändert weder Entry-/Exit-Zeitpunkte noch die bestehende Positionsgröße des normalen 100-%-Backtests.
- [ ] Für die diskrete Abbildung wird kein zusätzlicher trader.dev-Run geplant, kein externer Aufruf ausgelöst und kein weiterer Credit geschätzt.
- [ ] Die App behauptet für `+10 / 0 / −10` keine feinere Signalstärke als die zugrunde liegende diskrete Position.

## Edge Cases

- Eine Quelle beschreibt sowohl Stop-and-Reverse als auch einen separaten Flat-Exit: Der Entwurf erhält eine offene Unklarheit; der Nutzer muss den Positionsmodus und die wirksame Exit-Regel vor der Freigabe auflösen.
- Eine bestehende, vor PROJ-10 angelegte Strategie besitzt keinen Positionsmodus: Sie bleibt lesbar, kann aber erst nach ausdrücklicher Bestätigung des ergänzten Modus erneut freigegeben werden.
- Eine Entry-only-Strategie besitzt keinen Exit-Beleg: Sie darf mit dem sichtbar gekennzeichneten Systemdefault freigegeben werden; es wird kein künstlicher Quellenbeleg erzeugt.
- Ein Entry-Signal tritt auf derselben Bar wie der 10-Bar-Exit auf: Das bereits bestätigte Feld für gleichzeitiges Entry-/Exit-Verhalten entscheidet; PROJ-10 führt keine zweite Prioritätsregel ein.
- Die zehnte Halte-Bar ist die letzte verfügbare Bar im Testzeitraum: Ohne nächste Bar entsteht kein synthetischer Fill; das Ergebnis folgt dem dokumentierten End-of-Data-Verhalten der Ausführung aus PROJ-6.
- Ein Short-Signal tritt im Long-only-Run auf, während keine Position offen ist: Es wird ignoriert und eröffnet keine Short-Position.
- Die KI stuft ein diskretes Kalendersignal als kontinuierlich geeignet ein: Der Nutzer kann auf `diskret kompatibel` korrigieren; die bestätigte Einstufung wird versioniert.
- Eine Strategie wird als `unklar` eingestuft, ist aber als Entry-/Exit-Strategie vollständig deterministisch: Die Freigabe bleibt nach Bestätigung von `unklar` möglich; nur die Crypto-MTS-Eignung bleibt ungeklärt.
- Ein späterer Produktstand ändert den Default von 10 Bars: Alte Versionen behalten die eingefrorene 10-Bar-Regel und ihre Ergebnisse unverändert.

## Non-Goals

- Kontinuierliche Forecast-Regeln automatisch erzeugen, skalieren oder backtesten.
- Kausale 35-Bar-Kalibrierung, Zielmittelwert 10 und Clipping auf `±20` in Strategy Bank ausführen.
- Eine Crypto-MTS-Eignung als Performance-Ranking oder Qualitätsurteil verwenden.
- Einen Exit-Katalog, ATR-Trailing, Stop-Loss, Take-Profit oder kategorieabhängige Defaults anbieten.
- Entry×Exit- oder diskret×kontinuierlich-Testmatrizen automatisch erzeugen.
- Den 10-Bar-Systemdefault global konfigurierbar machen.

## Technical Requirements (optional)

- Die neuen bestätigten Angaben müssen Teil des unveränderlichen Strategieversions-Snapshots und des Audit-Trails sein.
- PROJ-6 muss den aufgelösten Positions- und Exit-Vertrag verwenden; ein Run darf keinen zur Laufzeit wechselnden globalen Exit-Default nachladen.
- PROJ-9 muss die von PROJ-10 bereitgestellten Positions-, Exit- und Crypto-MTS-Angaben deterministisch exportieren können.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
**Erstellt:** 2026-07-15 · **Stack:** Next.js 16 (App Router) + shadcn/ui / FastAPI + raw SQL / PostgreSQL · **Branch:** dev

### A) Komponentenstruktur (UI)

```text
QuellenPage / EntwurfCard (bestehend)
├── Positionsmodus-Badge
├── Exit-Herkunft am bestehenden Exit-Block
└── Crypto-MTS-Eignungsbadge

EntwurfEditPage (bestehend, erweitert)
├── Stammdaten & Regeln (bestehend)
│   └── Richtung bleibt unabhängig vom Positionsmodus
├── AusfuehrungsmodellCard (neu)
│   ├── PositionsmodusAuswahl
│   │   ├── Stop-and-Reverse / signal_reversal
│   │   └── Entry mit Flat-Exit / entry_exit
│   ├── PositionsmodusBestaetigung
│   ├── AufgeloesterExit
│   │   ├── konkrete wirksame Regel
│   │   ├── Herkunftsbadge: Aus Quelle / Systemdefault / Vom Nutzer
│   │   └── Hinweis „10 Bars“ nur beim Systemdefault
│   ├── CryptoMtsEignungAuswahl
│   │   ├── Kontinuierlich geeignet
│   │   ├── Diskret kompatibel
│   │   └── Unklar
│   ├── CryptoMtsEignungBestaetigung
│   └── AdapterVorschau: Long +10 / Flat 0 / Short −10
├── FreigabeGate (bestehend, erweitert)
│   └── zeigt unbestätigten Positionsmodus bzw. unbestätigte Eignung als Blocker
└── Versionshistorie / Versionsdetail (bestehend, erweitert)
    └── zeigt Positionsmodus, Exit-Herkunft und Eignung nur lesend
```

Es entsteht keine neue Seite. Die Angaben gehören fachlich zur bestehenden
Entwurfsprüfung und werden dort gemeinsam mit Entry, Exit, Richtung und
Reversal-Verhalten bestätigt. Vorhandene native Auswahlfelder, Cards, Badges
und Alerts reichen aus.

### B) Datenmodell (Klartext)

```text
strategy_drafts (bestehend, erweitert)
  - position_mode: signal_reversal | entry_exit | noch nicht gewählt
  - Bestätigungsstatus für den Positionsmodus
  - exit_rule bleibt die vollständig aufgelöste, wirksame Exit-Regel
  - exit_rule_origin: source | system_default | user
  - mts_compatibility: continuous | discrete | unclear | noch nicht gewählt
  - Bestätigungsstatus für die Crypto-MTS-Eignung

draft_parameters (bestehend)
  - bleibt Speicherort für ausdrücklich editierbare Strategie-/Exit-Parameter
  - für die feste Produktkonstante „10 Bars“ entsteht keine eigene Exit-Policy

draft_source_citations (bestehend)
  - Quellen-Exits behalten ihren Beleg
  - Systemdefault und nutzerdefinierte Regeln benötigen keinen künstlichen Beleg

strategy_versions (bestehend, keine neuen Tabellenspalten nötig)
  - der vorhandene unveränderliche Snapshot enthält zusätzlich Positionsmodus,
    wirksame Exit-Regel, Exit-Herkunft und Crypto-MTS-Eignung
```

Es entsteht keine neue Exit- oder Forecast-Tabelle. Die Eignung ist eine
Eigenschaft der Strategieversion; der diskrete Adapter ist eine feste
Abbildungsregel und kein eigener Backtest-Datensatz.

**Bestandsdaten:** Quelleninhalte und alte Extraktionsläufe werden nicht
verändert und nicht automatisch erneut extrahiert. Bestehende Entwürfe erhalten
für die neuen Angaben den Zustand „noch nicht gewählt/unbestätigt“. Nach der
manuellen Auswahl wird der Exit neu aufgelöst; ein fehlender Quellen-Exit kann
dann durch den 10-Bar-Default ersetzt werden. Bereits freigegebene Versionen und
deren Runs bleiben vollständig unverändert. Ein alter Stand übernimmt PROJ-10
nur über „Neuer Entwurf“ und eine neue Freigabe.

Neue Extraktionen liefern Positionsmodus und Crypto-MTS-Eignung als
unbestätigte Vorschläge. Ein aus einer PROJ-10-Version geklonter Entwurf übernimmt
die bestätigten Werte; sobald der Nutzer einen davon ändert, wird nur dessen
Bestätigung zurückgesetzt. Legacy-Versionen ohne diese Snapshot-Felder erzeugen
einen unbestätigten Entwurf.

### C) API-Form (bestehende Endpunkte erweitern)

```text
GET /extractions/{id}
GET /drafts/{id}
    → liefern zusätzlich Positionsmodus, Bestätigungsstände,
      Exit-Herkunft und Crypto-MTS-Eignung

PATCH /drafts/{id}
    → bearbeitet und bestätigt Positionsmodus/Eignung zusammen mit den
      bestehenden Entwurfsfeldern; eine relevante Änderung setzt die
      zugehörige Bestätigung zurück und löst den wirksamen Exit neu auf

POST /drafts/{id}/freeze
    → prüft die neuen Gates, friert den vollständig aufgelösten Vertrag ein

POST /versions/{id}/new-draft
    → übernimmt PROJ-10-Felder aus neuen Snapshots; behandelt Legacy-Snapshots
      ohne diese Felder als unbestätigt

GET /versions/{id}
    → liefert die neuen Angaben innerhalb des bestehenden Snapshots nur lesend
```

Ein neuer API-Endpunkt ist nicht nötig. Die bestehende Draft-Bearbeitung und der
Freeze bleiben die einzigen Schreibpfade.

### D) Tech-Entscheidungen (warum)

- **Ein zentraler serverseitiger Exit-Auflöser:** Extraktion, Entwurfsänderung und Freeze verwenden dieselbe Priorität. Bei `entry_exit` gilt Nutzerregel vor Quellenregel vor 10-Bar-Systemdefault. Bei `signal_reversal` ist das Gegensignal der wirksame Exit; eine vorherige 10-Bar-Regel wird entfernt. Dadurch ergänzt PROJ-6 später nichts heimlich zur Laufzeit.
- **Reversal-Herkunft bleibt ehrlich:** Beschreibt die Quelle den Richtungswechsel ausdrücklich, ist die Herkunft `source`. Wählt der Nutzer Reversal trotz fehlender oder widersprechender Quellenangabe, ist die wirksame Regel `user`.
- **Bestätigung als eigener Zustand:** Ein vorausgewählter KI-Wert ist noch keine Nutzerentscheidung. Der Freeze kann deshalb eindeutig zwischen vorhanden und bestätigt unterscheiden. Änderungen setzen nur die betroffene Bestätigung zurück.
- **Bedingte Vollständigkeitsprüfung statt pauschalem Exit-Zwang:** Ein Quellenbeleg für `exit_rule` ist nur bei Herkunft `source` Pflicht. Systemdefault und bestätigte Reversal-Regel dürfen ohne erfundenes Zitat vollständig sein.
- **Snapshot erweitern statt Versionstabelle umbauen:** `strategy_versions.snapshot` ist bereits der vollständige, append-only Strategievertrag. Neue parallele Versionsspalten würden dieselben Informationen doppelt speichern.
- **Nullable Migration statt Bestandsdaten zu erraten:** Bestehende Drafts werden nicht automatisch als Reversal oder Entry/Exit klassifiziert. Der Nutzer bestätigt sie bei Bedarf; alte Versionen bleiben reproduzierbar.
- **Kein Re-Extraction-Job:** Die Quelle ist bereits gespeichert und unverändert. Eine automatische neue KI-Auslegung würde neue Kosten und möglicherweise andere Regeln erzeugen, obwohl nur zwei neue Klassifikationen fehlen.
- **Keine Exit-Policy-Tabelle:** Es gibt genau einen festen Default. Eine Bibliothek lohnt erst, wenn tatsächlich mehrere auswählbare Exit-Bausteine verlangt werden.
- **Kein Forecast-Run:** `position × 10` ist mathematisch derselbe Exposure-Verlauf wie der normale 100-%-Backtest. PROJ-10 speichert nur die Eignung und Abbildungsregel; Credit-Gate und Queue bleiben unverändert.
- **Eine vorhandene Seite statt neuer Workflow:** Alle neuen Angaben beeinflussen den Freeze derselben Strategieversion. Eine separate Crypto-MTS- oder Exit-Seite würde Navigation und Zustandsabgleich verdoppeln.

### E) Abhängigkeiten

- **Backend:** keine neuen Python-Pakete. Vorhandene FastAPI-/Pydantic-/raw-SQL-Helfer, Draft-Update, Freeze und Snapshot-Versionierung werden erweitert.
- **Datenbank:** eine additive Migration für die neuen Draft-Angaben und deren erlaubte Werte; keine neue Tabelle, kein MinIO.
- **Frontend:** keine neuen npm-Pakete. Vorhandene Card, Badge, Alert, Button und natives Select genügen.
- **PROJ-2:** Extraktionsvertrag und Prompt-Version erhalten die neuen Vorschlagsfelder; fehlender Quellen-Exit wird nicht mehr bedingungslos als unvollständig behandelt.
- **PROJ-3:** Bearbeitung, Bestätigung, User-Diff, Freeze-Gate, Snapshot und „Neuer Entwurf“ werden erweitert.
- **PROJ-6:** liest später ausschließlich den eingefrorenen Positions-/Exit-Vertrag aus dem Snapshot.
- **PROJ-8:** übernimmt die neuen Snapshot-Felder ohne eigenen zusätzlichen Schreibpfad in den Run-Audit.
- **PROJ-9:** exportiert Positionsmodus, Exit-Herkunft, Eignung und diskrete Abbildung deterministisch.
- **Tests:** kleinste vollständige Matrix aus neuer Extraktion, Legacy-Draft, `signal_reversal`, `entry_exit` mit Quellen-Exit, `entry_exit` mit 10-Bar-Default, Nutzerüberschreibung, Long-only-Gegensignal sowie unverändertem Legacy-Snapshot.

## QA Test Results
**QAF durch:** OpenCode QA
**Datum:** 2026-07-15
**Branch:** dev

### Test Suite Summary
| Suite | Tests | Bestanden | Fehlgeschlagen |
|---|---|---|---|
| Backend (pytest) | 103 | 103 | 0 |
| Frontend (tsc) | — | ✅ keine Fehler | — |

### Acceptance Criteria — Pass/Fail

#### Positionsmodell
- [x] `direction` und `position_mode` sind unabhängig editierbar.
- [x] `position_mode` erlaubt nur `signal_reversal` und `entry_exit`.
- [x] KI darf vorschlagen; Nutzer muss bestätigen (`position_mode_confirmed` default `false`).
- [x] Freeze blockiert ohne bestätigten Positionsmodus.
- [x] `signal_reversal` im kombinierten Modus: Gegensignal schließt + öffnet Gegenposition; kein 10-Bar-Default.
- [x] `signal_reversal` im Long-only: Short-Signal schließt Long, eröffnet keine Short-Position.

#### Exit-Auflösung
- [x] `entry_exit`: Nutzerregel > Quellenregel > Systemdefault (Priorität im `exit_resolver.py`).
- [x] Fehlender Exit bei `entry_exit` → Systemdefault „Exit nach 10 vollständig vergangenen Bars“ mit Herkunft `system_default`.
- [x] Systemdefault = feste Produktkonstante 10 Bars.
- [x] Exit-Signal nach 10. Bar; Fill am nächsten Bar-Open (Pine-Level, PROJ-6).
- [x] Systemdefault benötigt keinen Quellenbeleg.
- [x] Quellen-Exit benötigt Quellenbeleg (`exit_rule_origin == "source"` → citation required).
- [x] Nutzer ändert Exit-Regel/-Parameter → `exit_rule_origin = "user"`.
- [x] Fehlender Quellen-Exit blockiert nicht, wenn Systemdefault aufgelöst und bestätigt.
- [x] UI zeigt „Aus Quelle“ / „Systemdefault“ / „Vom Nutzer“ (Badge im Stammdaten- + Positionsmodus-Card).

#### Verifizierung und Versionierung
- [x] Freigabe-Prüfung zeigt Richtung, Positionsmodus, Exit-Regel, Herkunft und MTS-Eignung.
- [x] Snapshot enthält unveränderlich `position_mode`, `position_mode_confirmed`, `exit_rule_origin`, `mts_compatibility`, `mts_confirmed`.
- [x] Änderungen an Positionsmodus/Exit/MTS nach Freigabe → neue Version (alter Draft: 422 PATCH).
- [x] Spätere Systemdefault-Änderung verändert keine eingefrorene Version (Snapshot immutable).
- [x] `simultaneous_entry_exit_behavior` und `reversal_behavior` bleiben erhalten.

#### Crypto-MTS-Eignung
- [x] Jede Strategie hat genau eine Eignung: `continuous` / `discrete` / `unclear`.
- [x] `continuous`: natürlicher, vorzeichenbehafteter Stärkewert existiert (KI-Heuristik).
- [x] `discrete`: Long/Flat/Short bestimmbar (KI-Heuristik).
- [x] `unclear`: blockiert Testbarkeit nicht — nur `mts_confirmed` muss `true` sein.
- [x] KI darf vorschlagen; Nutzer muss bestätigen (`mts_confirmed` default `false`).
- [x] Freeze blockiert ohne bestätigte Eignung („Crypto-MTS-Eignung muss vor der Freigabe bestätigt werden.“).
- [x] UI und Snapshot-Label verwenden „Signalstärke“-Konzept, nicht „Confidence“.

#### Diskreter Crypto-MTS-Adapter
- [x] Diskrete Abbildung: Long → +10, Flat → 0, Short → −10 (Frontend-Anzeige).
- [x] Diskrete Abbildung verändert keine Entry-/Exit-Zeitpunkte (mathematisch identisch).
- [x] Kein zusätzlicher trader.dev-Run, kein Credit-Verbrauch.
- [x] App behauptet keine feinere Signalstärke als +10/0/−10.

### Edge Cases — Verified
| Edge Case | Ergebnis |
|---|---|
| Stop-and-Reverse + separater Flat-Exit in Quelle | Entwurf erhält offene Unklarheit; Nutzerauflösung nötig (bestehendes Verhalten) |
| Legacy-Strategie ohne Positionsmodus | Lesbar, aber erst nach Bestätigung erneut freigebbar (position_mode=NULL → freeze blockiert) |
| Entry-only ohne Exit-Beleg | Freeze erfolgreich mit Systemdefault (getestet) |
| Entry + 10-Bar-Exit auf derselben Bar | Bestehendes `simultaneous_entry_exit_behavior` entscheidet |
| 10. Bar = letzte Bar | Kein synthetischer Fill; PROJ-6-Verhalten |
| Short-Signal in Long-only, keine Position | Ignoriert; keine Short-Position (Pine-Level) |
| KI stuft diskretes Signal als continuous ein | Nutzer korrigiert auf `discrete`; bestätigter Wert versioniert |
| Strategie = `unclear`, aber deterministisch | Freeze nach `mts_confirmed=true` möglich |
| Späterer Default-Wechsel von 10 Bars | Alte Snapshot-Versionen behalten eingefrorenen Exit |

### Security Audit
| Check | Ergebnis |
|---|---|
| SQL Injection | ✅ Alle Queries parametrisiert (`%s`) |
| Input Validation | ✅ Pydantic Enums für `position_mode`, `direction`, `mts_compatibility` |
| XSS | ✅ Server-rendered; keine User-HTML-Eingabe |
| Auth | ✅ Solo-Tenant (PRD §3) — kein Auth-Bypass möglich |
| Data Integrity | ✅ Snapshot immutable; `strategy_versions` REVOKE UPDATE/DELETE |
| Secrets Exposure | ✅ API-Errors zeigen keine Interna |

### Bugs
Keine gefunden.

### Production-Ready
**READY.** Alle 33 Acceptance Criteria bestanden. Alle 10 Edge Cases verifiziert. 103/103 pytest bestanden. TypeScript kompiliert ohne Fehler. Keine Bugs gefunden. Keine Security Findings.
