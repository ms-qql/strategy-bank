import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Vor jedem App-Import: Test-Datenbank statt Dev-Datenbank verwenden.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://strategy_bank:strategy_bank_dev@localhost:55433/strategy_bank_test",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import run_command  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_db():
    run_command(
        "TRUNCATE sources, extraction_runs, strategy_drafts, "
        "draft_parameters, draft_source_citations, draft_open_questions, "
        "strategy_versions, version_parameters, "
        "backtest_profiles, batches, batch_instruments, batch_strategy_versions, "
        "batch_direction_modes, runs, run_audits, backtest_executions, "
        "family_holdout_status, worker_heartbeat CASCADE"
    )
    run_command(
        "INSERT INTO worker_heartbeat (worker_id, last_heartbeat) "
        "VALUES ('strategy-bank-worker-v1', now()) "
        "ON CONFLICT (worker_id) DO UPDATE SET last_heartbeat = now()"
    )
    yield


@pytest.fixture
def client():
    return TestClient(app)
