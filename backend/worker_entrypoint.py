"""PROJ-12 Worker Entrypoint — idempotente SQL-Migrationen, dann Worker-Loop.

Wird im docker-compose.dokploy.yml als separater Dauerdienst gestartet.
Läuft nach dem Start der API (depends_on strategy-bank-api, aber nicht
condition service_healthy — der Worker läuft auch ohne API).
"""

import logging
import os
from pathlib import Path

import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main() -> None:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('strategy_bank_migrations'))")
        for migration in sorted(Path("sql").glob("*.sql")):
            try:
                cur.execute(migration.read_text())
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Migration %s ignoriert: %s", migration.name, exc
                )
        conn.commit()

    from app.services.worker import run_worker

    run_worker()


if __name__ == "__main__":
    main()
