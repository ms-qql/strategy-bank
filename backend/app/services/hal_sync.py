import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from ..db import run_query, run_query_one

logger = logging.getLogger(__name__)

HAL_QUELLEN_DIR = Path("/home/dev/tools/Hal/04 Resources/Strategy_Bank/01_Quellen")


def safe_filename(name: str) -> str:
    safe = re.sub(r"[^\w\s-]", "", name)
    safe = re.sub(r"\s+", "_", safe)
    return safe.strip("_") or "strategy"


def _escape_md(text: str | None) -> str:
    if not text:
        return ""
    return str(text).replace("|", "\\|")


def check_name_conflict(name: str, family_id: UUID) -> str | None:
    row = run_query_one(
        """SELECT family_id
           FROM strategy_drafts
           WHERE LOWER(name) = LOWER(%s) AND family_id != %s
           LIMIT 1""",
        [name, str(family_id)],
    )
    if row:
        return str(row["family_id"])
    return None


def _build_steckbrief_md(draft: dict) -> str:
    lines: list[str] = []
    lines.append(f"# {_escape_md(draft.get('name') or 'Unbenannt')}")
    lines.append("")

    category = _escape_md(draft.get("category"))
    direction = _escape_md(draft.get("direction"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines.append(f"**Kategorie:** {category or '—'} · **Richtung:** {direction or '—'} · **Stand:** {now}")
    lines.append("")

    thesis = draft.get("thesis")
    if thesis:
        lines.append("## These")
        lines.append(str(thesis))
        lines.append("")

    entry_rule = draft.get("entry_rule")
    if entry_rule:
        lines.append("## Entry-Regel")
        lines.append(str(entry_rule))
        lines.append("")

    exit_rule = draft.get("exit_rule")
    if exit_rule:
        eo = draft.get("exit_rule_origin")
        origin_label = {"source": "Aus Quelle", "system_default": "System-Default", "user": "Benutzer"}.get(eo, str(eo) if eo else "")
        lines.append("## Exit-Regel")
        lines.append(f"{_escape_md(str(exit_rule))}" + (f" *(Herkunft: {origin_label})*" if origin_label else ""))
        lines.append("")

    position_mode = draft.get("position_mode")
    if position_mode:
        pm_label = {"signal_reversal": "Stop-and-Reverse", "entry_exit": "Entry mit Flat-Exit"}.get(position_mode, position_mode)
        confirmed = draft.get("position_mode_confirmed")
        suffix = " *(bestätigt)*" if confirmed else ""
        lines.append("## Positionsmodus")
        lines.append(f"{pm_label}{suffix}")
        lines.append("")

    mts = draft.get("mts_compatibility")
    if mts:
        mts_label = {"continuous": "Kontinuierlich geeignet", "discrete": "Diskret kompatibel", "unclear": "Unklar"}.get(mts, mts)
        confirmed = draft.get("mts_confirmed")
        suffix = " *(bestätigt)*" if confirmed else ""
        lines.append("## Crypto-MTS-Eignung")
        lines.append(f"{mts_label}{suffix}")
        lines.append("")

    warmup = draft.get("warmup_requirement")
    if warmup:
        lines.append("## Warm-up")
        lines.append(str(warmup))
        lines.append("")

    parameters = run_query(
        "SELECT name, value, unit, allowed_range FROM draft_parameters WHERE draft_id = %s",
        [draft["id"]],
    )
    if parameters:
        lines.append("## Parameter")
        lines.append("")
        lines.append("| Name | Wert | Einheit | Bereich |")
        lines.append("|------|------|---------|---------|")
        for p in parameters:
            name = _escape_md(p.get("name"))
            value = _escape_md(p.get("value"))
            unit = _escape_md(p.get("unit")) or "—"
            arange = _escape_md(p.get("allowed_range")) or "—"
            lines.append(f"| {name} | {value} | {unit} | {arange} |")
        lines.append("")

    citations = run_query(
        "SELECT rule_field, excerpt, line_reference FROM draft_source_citations WHERE draft_id = %s",
        [draft["id"]],
    )
    if citations:
        lines.append("## Quellenbelege")
        lines.append("")
        for c in citations:
            field = c.get("rule_field", "")
            excerpt = _escape_md(c.get("excerpt"))
            ref = c.get("line_reference")
            ref_suffix = f" *({ref})*" if ref else ""
            lines.append(f"- {field}: \"{excerpt}\"{ref_suffix}")
        lines.append("")

    return "\n".join(lines) + "\n"


def _load_draft_for_sync(draft_id: UUID) -> dict | None:
    return run_query_one(
        """SELECT id, name, family_id, thesis, category, direction,
                  entry_rule, exit_rule, warmup_requirement,
                  position_mode, position_mode_confirmed, exit_rule_origin,
                  mts_compatibility, mts_confirmed
           FROM strategy_drafts WHERE id = %s""",
        [draft_id],
    )


def delete_hal_file(name: str) -> None:
    if not name:
        return
    filepath = HAL_QUELLEN_DIR / (safe_filename(name) + ".md")
    try:
        filepath.unlink(missing_ok=True)
    except Exception:
        logger.exception("Hal-sync: failed to delete stale file %s", filepath)


def sync_draft_to_hal(draft_id: UUID) -> None:
    draft = _load_draft_for_sync(draft_id)
    if not draft:
        return

    name = draft.get("name") or "Unbenannt"
    filename = safe_filename(name) + ".md"
    family_id = UUID(str(draft["family_id"]))
    filepath = HAL_QUELLEN_DIR / filename

    try:
        HAL_QUELLEN_DIR.mkdir(parents=True, exist_ok=True)
        content = _build_steckbrief_md(draft)
        filepath.write_text(content, encoding="utf-8")
    except Exception:
        logger.exception("Hal-sync failed for draft_id=%s file=%s", draft_id, filepath)


def sync_all_drafts_to_hal() -> dict:
    drafts = run_query(
        """SELECT id, name, family_id
           FROM strategy_drafts
           ORDER BY created_at""",
    )
    synced = 0
    skipped = 0
    errors: list[str] = []
    owner_by_filename: dict[str, str] = {}

    for d in drafts:
        filename = safe_filename(d.get("name") or "Unbenannt")
        family_id = str(d["family_id"])
        owner = owner_by_filename.get(filename)
        if owner is not None and owner != family_id:
            skipped += 1
            logger.warning(
                "Hal-sync-all: skip draft_id=%s file=%s.md — already claimed by family_id=%s",
                d["id"], filename, owner,
            )
            continue
        owner_by_filename[filename] = family_id
        try:
            sync_draft_to_hal(UUID(str(d["id"])))
            synced += 1
        except Exception:
            errors.append(str(d["id"]))
            logger.exception("Hal-sync-all failed for draft_id=%s", d["id"])

    return {"synced": synced, "skipped": skipped, "errors": errors}
