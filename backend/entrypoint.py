"""Apply idempotent SQL migrations, then start the API."""

import os
from pathlib import Path

import psycopg


def main() -> None:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext('strategy_bank_migrations'))")
        for migration in sorted(Path("sql").glob("*.sql")):
            cursor.execute(migration.read_text())
        conn.commit()
    os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])


if __name__ == "__main__":
    main()
