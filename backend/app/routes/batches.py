from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from ..constants import (
    DEFAULT_INSTRUMENTS,
    DEFAULT_PERIOD_END,
    DEFAULT_PERIOD_START,
    DEFAULT_TIMEFRAME,
    DIRECTION_MODES,
    HOLDOUT_PERIOD_START,
)
from ..db import run_command, run_query, run_query_one, transaction
from ..schemas.batches import (
    BacktestProfileRead,
    BacktestProfileWrite,
    BatchCreate,
    BatchRead,
    BatchUpdate,
    HoldoutBatchCreate,
    HoldoutStatusRead,
    InstrumentIn,
    PreviewRun,
)

router = APIRouter(tags=["batches"])


# --- Backtest-Profile ------------------------------------------------------

@router.post("/backtest-profiles", response_model=BacktestProfileRead, status_code=201)
def create_backtest_profile(body: BacktestProfileWrite) -> dict:
    family_id = uuid4()
    return _insert_profile_version(family_id, 1, body)


@router.get("/backtest-profiles", response_model=list[BacktestProfileRead])
def list_backtest_profiles() -> list[dict]:
    return run_query(
        """
        SELECT DISTINCT ON (family_id) *
        FROM backtest_profiles
        ORDER BY family_id, version_number DESC
        """
    )


@router.get("/backtest-profiles/{family_id}/versions", response_model=list[BacktestProfileRead])
def list_backtest_profile_versions(family_id: UUID) -> list[dict]:
    rows = run_query(
        "SELECT * FROM backtest_profiles WHERE family_id = %s ORDER BY version_number",
        [family_id],
    )
    if not rows:
        raise HTTPException(404, "Backtest-Profil nicht gefunden.")
    return rows


@router.patch("/backtest-profiles/{family_id}", response_model=BacktestProfileRead)
def update_backtest_profile(family_id: UUID, body: BacktestProfileWrite) -> dict:
    max_n = run_query_one(
        "SELECT MAX(version_number) AS max_n FROM backtest_profiles WHERE family_id = %s",
        [family_id],
    )
    if not max_n or max_n["max_n"] is None:
        raise HTTPException(404, "Backtest-Profil nicht gefunden.")
    return _insert_profile_version(family_id, max_n["max_n"] + 1, body)


def _insert_profile_version(family_id: UUID, version_number: int, body: BacktestProfileWrite) -> dict:
    row = run_command(
        """
        INSERT INTO backtest_profiles (
            family_id, version_number, name, timezone_session, signal_timing, fill_timing,
            order_type, fee_pct, slippage_ticks, starting_capital, quote_currency,
            position_sizing, compounding_rule, leverage, pyramiding, max_open_positions,
            missing_bars_handling, corporate_actions_handling
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        [
            family_id, version_number, body.name, body.timezone_session, body.signal_timing,
            body.fill_timing, body.order_type, body.fee_pct, body.slippage_ticks,
            body.starting_capital, body.quote_currency, body.position_sizing,
            body.compounding_rule, body.leverage, body.pyramiding, body.max_open_positions,
            body.missing_bars_handling, body.corporate_actions_handling,
        ],
        returning=True,
    )
    assert row is not None
    return row


# --- Batches -----------------------------------------------------------

def _validate_strategy_versions(strategy_version_ids: list[UUID]) -> None:
    rows = run_query(
        "SELECT id FROM strategy_versions WHERE id = ANY(%s)",
        [strategy_version_ids],
    )
    found = {r["id"] for r in rows}
    missing = [str(i) for i in strategy_version_ids if i not in found]
    if missing:
        raise HTTPException(422, f"Strategieversion(en) nicht gefunden: {', '.join(missing)}")


def _validate_direction_modes(modes: list[str]) -> None:
    invalid = [m for m in modes if m not in DIRECTION_MODES]
    if invalid:
        raise HTTPException(422, f"Ungültiger Richtungsmodus: {', '.join(invalid)}")


def _create_batch(
    *,
    backtest_profile_id: UUID,
    strategy_version_ids: list[UUID],
    instruments: list[InstrumentIn] | None,
    direction_modes: list[str] | None,
    timeframe: str | None,
    period_start: date | None,
    period_end: date | None,
    run_kind: str,
) -> dict:
    profile = run_query_one("SELECT id FROM backtest_profiles WHERE id = %s", [backtest_profile_id])
    if not profile:
        raise HTTPException(422, "Backtest-Profil nicht gefunden.")
    _validate_strategy_versions(strategy_version_ids)

    resolved_instruments = instruments or [InstrumentIn(**i) for i in DEFAULT_INSTRUMENTS]
    resolved_modes = direction_modes or ["kombiniert"]
    _validate_direction_modes(resolved_modes)
    resolved_timeframe = timeframe or DEFAULT_TIMEFRAME
    resolved_start = period_start or date.fromisoformat(DEFAULT_PERIOD_START)
    resolved_end = period_end if period_end is not None else (
        date.fromisoformat(DEFAULT_PERIOD_END) if run_kind == "standard" else period_end
    )

    batch_id = uuid4()
    with transaction() as cur:
        cur.execute(
            """
            INSERT INTO batches (id, backtest_profile_id, timeframe, period_start, period_end, run_kind)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [batch_id, backtest_profile_id, resolved_timeframe, resolved_start, resolved_end, run_kind],
        )
        _write_batch_children(cur, batch_id, strategy_version_ids, resolved_instruments, resolved_modes)

    return _load_batch(batch_id)


def _write_batch_children(
    cur, batch_id: UUID, strategy_version_ids: list[UUID],
    instruments: list[InstrumentIn], direction_modes: list[str],
) -> None:
    cur.execute("DELETE FROM batch_strategy_versions WHERE batch_id = %s", [batch_id])
    for sv_id in strategy_version_ids:
        cur.execute(
            "INSERT INTO batch_strategy_versions (batch_id, strategy_version_id) VALUES (%s, %s)",
            [batch_id, sv_id],
        )
    cur.execute("DELETE FROM batch_instruments WHERE batch_id = %s", [batch_id])
    for instr in instruments:
        cur.execute(
            "INSERT INTO batch_instruments (batch_id, provider_symbol, label) VALUES (%s, %s, %s)",
            [batch_id, instr.provider_symbol, instr.label],
        )
    cur.execute("DELETE FROM batch_direction_modes WHERE batch_id = %s", [batch_id])
    for mode in direction_modes:
        cur.execute(
            "INSERT INTO batch_direction_modes (batch_id, mode) VALUES (%s, %s)",
            [batch_id, mode],
        )


@router.post("/batches", response_model=BatchRead, status_code=201)
def create_batch(body: BatchCreate) -> dict:
    return _create_batch(
        backtest_profile_id=body.backtest_profile_id,
        strategy_version_ids=body.strategy_version_ids,
        instruments=body.instruments,
        direction_modes=body.direction_modes,
        timeframe=body.timeframe,
        period_start=body.period_start,
        period_end=body.period_end,
        run_kind="standard",
    )


@router.get("/batches/{batch_id}", response_model=BatchRead)
def get_batch(batch_id: UUID) -> dict:
    return _load_batch(batch_id)


@router.patch("/batches/{batch_id}", response_model=BatchRead)
def update_batch(batch_id: UUID, body: BatchUpdate) -> dict:
    batch = run_query_one("SELECT id, status FROM batches WHERE id = %s", [batch_id])
    if not batch:
        raise HTTPException(404, "Batch nicht gefunden.")
    if batch["status"] != "entwurf":
        raise HTTPException(422, "Bestätigte Batches können nicht mehr bearbeitet werden.")

    fields: dict[str, object] = {}
    if body.backtest_profile_id is not None:
        if not run_query_one("SELECT id FROM backtest_profiles WHERE id = %s", [body.backtest_profile_id]):
            raise HTTPException(422, "Backtest-Profil nicht gefunden.")
        fields["backtest_profile_id"] = body.backtest_profile_id
    if body.timeframe is not None:
        fields["timeframe"] = body.timeframe
    if body.period_start is not None:
        fields["period_start"] = body.period_start
    if body.period_end is not None:
        fields["period_end"] = body.period_end

    with transaction() as cur:
        if fields:
            set_clause = ", ".join(f"{k} = %s" for k in fields)
            cur.execute(f"UPDATE batches SET {set_clause} WHERE id = %s", [*fields.values(), batch_id])
        if body.strategy_version_ids is not None:
            _validate_strategy_versions(body.strategy_version_ids)
            cur.execute("DELETE FROM batch_strategy_versions WHERE batch_id = %s", [batch_id])
            for sv_id in body.strategy_version_ids:
                cur.execute(
                    "INSERT INTO batch_strategy_versions (batch_id, strategy_version_id) VALUES (%s, %s)",
                    [batch_id, sv_id],
                )
        if body.instruments is not None:
            cur.execute("DELETE FROM batch_instruments WHERE batch_id = %s", [batch_id])
            for instr in body.instruments:
                cur.execute(
                    "INSERT INTO batch_instruments (batch_id, provider_symbol, label) VALUES (%s, %s, %s)",
                    [batch_id, instr.provider_symbol, instr.label],
                )
        if body.direction_modes is not None:
            _validate_direction_modes(body.direction_modes)
            cur.execute("DELETE FROM batch_direction_modes WHERE batch_id = %s", [batch_id])
            for mode in body.direction_modes:
                cur.execute(
                    "INSERT INTO batch_direction_modes (batch_id, mode) VALUES (%s, %s)",
                    [batch_id, mode],
                )

    return _load_batch(batch_id)


def _batch_children(batch_id: UUID) -> tuple[list[UUID], list[dict], list[str]]:
    sv_rows = run_query(
        "SELECT strategy_version_id FROM batch_strategy_versions WHERE batch_id = %s", [batch_id],
    )
    instr_rows = run_query(
        "SELECT provider_symbol, label FROM batch_instruments WHERE batch_id = %s", [batch_id],
    )
    mode_rows = run_query(
        "SELECT mode FROM batch_direction_modes WHERE batch_id = %s", [batch_id],
    )
    return (
        [r["strategy_version_id"] for r in sv_rows],
        instr_rows,
        [r["mode"] for r in mode_rows],
    )


@router.get("/batches/{batch_id}/preview", response_model=list[PreviewRun])
def preview_batch(batch_id: UUID) -> list[dict]:
    batch = run_query_one("SELECT id FROM batches WHERE id = %s", [batch_id])
    if not batch:
        raise HTTPException(404, "Batch nicht gefunden.")
    strategy_version_ids, instruments, direction_modes = _batch_children(batch_id)
    return [
        {"strategy_version_id": sv_id, "provider_symbol": instr["provider_symbol"], "direction_mode": mode}
        for sv_id in strategy_version_ids
        for instr in instruments
        for mode in direction_modes
    ]


@router.post("/batches/{batch_id}/confirm", response_model=BatchRead, status_code=201)
def confirm_batch(batch_id: UUID) -> dict:
    batch = run_query_one("SELECT id, status, run_kind FROM batches WHERE id = %s", [batch_id])
    if not batch:
        raise HTTPException(404, "Batch nicht gefunden.")
    if batch["status"] != "entwurf":
        raise HTTPException(422, "Batch ist bereits bestätigt.")

    strategy_version_ids, instruments, direction_modes = _batch_children(batch_id)
    if not (strategy_version_ids and instruments and direction_modes):
        raise HTTPException(422, "Batch ist unvollständig — Strategieversion, Instrument und Richtungsmodus erforderlich.")

    now = datetime.now(timezone.utc)
    with transaction() as cur:
        cur.execute(
            "UPDATE batches SET status = 'bestätigt', confirmed_at = %s WHERE id = %s",
            [now, batch_id],
        )
        for sv_id in strategy_version_ids:
            for instr in instruments:
                for mode in direction_modes:
                    cur.execute(
                        """
                        INSERT INTO runs (batch_id, strategy_version_id, provider_symbol, direction_mode, run_kind)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        [batch_id, sv_id, instr["provider_symbol"], mode, batch["run_kind"]],
                    )

    return _load_batch(batch_id)


def _load_batch(batch_id: UUID) -> dict:
    row = run_query_one("SELECT * FROM batches WHERE id = %s", [batch_id])
    if not row:
        raise HTTPException(404, "Batch nicht gefunden.")
    strategy_version_ids, instruments, direction_modes = _batch_children(batch_id)
    return {
        **row,
        "strategy_version_ids": strategy_version_ids,
        "instruments": instruments,
        "direction_modes": direction_modes,
    }


# --- Holdout / Forward-Test --------------------------------------------

@router.get("/strategy-versions/{version_id}/holdout-status", response_model=HoldoutStatusRead)
def get_holdout_status(version_id: UUID) -> dict:
    version = run_query_one("SELECT family_id FROM strategy_versions WHERE id = %s", [version_id])
    if not version:
        raise HTTPException(404, "Version nicht gefunden.")
    status = run_query_one(
        "SELECT consumed_at FROM family_holdout_status WHERE family_id = %s", [version["family_id"]],
    )
    consumed_at = status["consumed_at"] if status else None
    return {"family_id": version["family_id"], "consumed": consumed_at is not None, "consumed_at": consumed_at}


@router.post("/strategy-versions/{version_id}/holdout-batch", response_model=BatchRead, status_code=201)
def create_holdout_batch(version_id: UUID, body: HoldoutBatchCreate) -> dict:
    version = run_query_one(
        "SELECT id, family_id, frozen_at FROM strategy_versions WHERE id = %s", [version_id],
    )
    if not version:
        raise HTTPException(404, "Version nicht gefunden.")

    existing = run_query_one(
        "SELECT consumed_at FROM family_holdout_status WHERE family_id = %s", [version["family_id"]],
    )
    if existing and existing["consumed_at"] is not None:
        raise HTTPException(422, "Holdout bereits verwendet für diese Strategie-Familie.")

    batch = _create_batch(
        backtest_profile_id=body.backtest_profile_id,
        strategy_version_ids=[version_id],
        instruments=body.instruments,
        direction_modes=body.direction_modes,
        timeframe=body.timeframe,
        period_start=date.fromisoformat(HOLDOUT_PERIOD_START),
        period_end=version["frozen_at"].date(),
        run_kind="holdout",
    )
    run_command(
        """
        INSERT INTO family_holdout_status (family_id, consumed_at) VALUES (%s, now())
        ON CONFLICT (family_id) DO NOTHING
        """,
        [version["family_id"]],
    )
    return batch


@router.post("/strategy-versions/{version_id}/forward-test-batch", response_model=BatchRead, status_code=201)
def create_forward_test_batch(version_id: UUID, body: HoldoutBatchCreate) -> dict:
    version = run_query_one(
        "SELECT id, family_id, frozen_at FROM strategy_versions WHERE id = %s", [version_id],
    )
    if not version:
        raise HTTPException(404, "Version nicht gefunden.")

    return _create_batch(
        backtest_profile_id=body.backtest_profile_id,
        strategy_version_ids=[version_id],
        instruments=body.instruments,
        direction_modes=body.direction_modes,
        timeframe=body.timeframe,
        period_start=version["frozen_at"].date(),
        period_end=None,
        run_kind="forward_test",
    )
