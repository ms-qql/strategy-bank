"""Roher SQL-Zugriff (kein ORM). Single-Tenant (PRD §3): kein `mandant_id`,
keine RLS. Parametrisiertes SQL only (`%s`)."""

from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import psycopg
from psycopg.rows import dict_row

from .config import settings


def _connect() -> psycopg.Connection:
    return psycopg.connect(settings.database_url, row_factory=dict_row)


@contextmanager
def transaction() -> Iterator[psycopg.Cursor]:
    """Mehrere Statements atomar in EINER Transaktion (commit am Ende, sonst
    rollback) — z. B. Entwurf + Parameter + Quellenbelege + Unklarheiten."""
    with _connect() as conn, conn.cursor() as cur:
        yield cur
        conn.commit()


def run_query(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    """SELECT → Liste von Zeilen als dicts."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params or [])
        return cur.fetchall()


def run_query_one(sql: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params or [])
        return cur.fetchone()


def run_command(
    sql: str,
    params: Sequence[Any] | None = None,
    returning: bool = False,
) -> dict[str, Any] | None:
    """INSERT/UPDATE/DELETE. Mit `returning=True` wird die erste RETURNING-Zeile
    zurückgegeben. Commit erfolgt am Ende des Connection-Kontexts."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params or [])
        row = cur.fetchone() if returning else None
        conn.commit()
        return row
