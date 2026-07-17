-- PROJ-6: Compiler-Feedback-Schleife für Pine-Regenerierung.
-- Speichert den letzten Provider-Fehler je Execution, damit ein Retry den
-- exakten Fehlertext in den nächsten Generierungsversuch zurückspeisen kann
-- (statt jede halluzinierte Funktion einzeln per Blacklist abzufangen).

ALTER TABLE backtest_executions
    ADD COLUMN IF NOT EXISTS last_provider_error TEXT;
