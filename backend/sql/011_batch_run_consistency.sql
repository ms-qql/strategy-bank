-- Bugfix: DELETE /runs/{id} (Feature "Ergebnisse löschen") aktualisierte nie
-- den Batch-Status. Wurde der letzte Run eines bestätigten/gestarteten
-- Batches gelöscht, blieb dieser dauerhaft gesperrt (status != 'entwurf',
-- aber 0 Runs) — Konfiguration nicht mehr änderbar, kein erneuter Start
-- möglich. Einmalige Reparatur bereits verwaister Batches; der zugehörige
-- Code-Fix in app/routes/runs.py verhindert neue Fälle.
UPDATE batches
SET status = 'entwurf', confirmed_at = NULL,
    credit_max = NULL, credit_balance = NULL, credit_remaining = NULL,
    credit_tier = NULL, credit_reset = NULL, credit_checked_at = NULL
WHERE status != 'entwurf'
  AND NOT EXISTS (SELECT 1 FROM runs WHERE runs.batch_id = batches.id);
