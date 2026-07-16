# Frontdesk-Check: Strategie-Backtest `signal_reversal`

- **Datum:** 2026-07-16
- **Quelle:** Direkte Nutzermeldung mit Screenshot
- **Hinweis:** Interne Ersteinschätzung, kein vollständiges QA-Ergebnis

### Ticket: Backtest einer Strategieversion scheitert und die vermutete Einstellung ist nicht auffindbar

**Kurzbefund:** Übergreifendes Problem

**Eingrenzung:** Schicht: Backend/externer Provider · Modul: Queue-Ausführung / Pine-Generierung
Der Screenshot zeigt `POST /backtests/adhoc → 400` mit `Cannot read properties of undefined (reading 'signal_reversal')`; der Code übergibt den Positionsmodus nur an die Pine-Generierung und sendet danach den generierten Pine-Quelltext an trader.dev. Eine ungültige Generierung oder Provider-Verarbeitung würde daher alle Strategieversionen mit derselben Konstellation betreffen. Nicht live geprüft; Einschätzung basiert auf Screenshot und gezielter Code-Analyse.

Die fehlende direkte Bearbeitungsmöglichkeit ist dagegen vorgesehen: freigegebene Strategieversionen sind unveränderlich. Unter **Entwürfe → betroffene Strategie → Versionshistorie → Neuer Entwurf** kann aus der Version ein bearbeitbarer Entwurf erstellt, angepasst und als neue Version freigegeben werden.

**Dringlichkeit:** Mittel
Der einzelne Backtest ist blockiert, aber es gibt keinen Hinweis auf Datenverlust, falsche Zuordnung oder DSGVO-Risiko; ein Workflow für eine korrigierte neue Version ist vorhanden.

**Antwortentwurf an den Kunden:**
> Danke für den Screenshot. Die bereits freigegebene Strategieversion ist absichtlich nicht mehr direkt veränderbar, damit frühere Backtests reproduzierbar bleiben. Sie können unter „Entwürfe“ die betroffene Strategie öffnen und in der „Versionshistorie“ bei der verwendeten Version auf „Neuer Entwurf“ klicken. Dort lassen sich unter „Positionsmodus & Exit-Konfiguration“ die Angaben anpassen und anschließend als neue Version freigeben. Der angezeigte technische Fehler beweist allerdings noch nicht, dass diese Einstellung falsch ist; wir sollten den fehlgeschlagenen Lauf separat prüfen.

**Rückfragen-Guidance:** Benötigt werden die ID bzw. der Link der betroffenen Strategieversion und des Runs sowie der beim Lauf erzeugte Pine-Quelltext bzw. die vollständige gespeicherte Provider-Antwort. Außerdem sollte genannt werden, welcher Positionsmodus und welche Exit-Regel in der Version angezeigt werden.

## Backoffice-Auflösung

Die Einstellung war nicht die Ursache. Der Pine-Generator gab das interne Enum `signal_reversal` an das Produktionsmodell weiter und akzeptierte daraus entstandene ungültige Pine-API-Zugriffe. Prompt und Ausgabeprüfung wurden korrigiert; der Reproduktionstest ist grün. Einen eigenen Navigationspunkt „Entwürfe“ gibt es nicht: Entwürfe stehen innerhalb von **Quellen** als Karten mit der Aktion **Entwurf bearbeiten**.
