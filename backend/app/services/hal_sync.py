import io
import re
import zipfile
from datetime import datetime, timezone
from uuid import UUID

from ..db import run_query, run_query_one


def safe_filename(name: str) -> str:
    safe = re.sub(r"[^\w\s-]", "", name)
    safe = re.sub(r"\s+", "_", safe)
    return safe.strip("_") or "strategy"


def _escape_md(text: str | None) -> str:
    if not text:
        return ""
    return str(text).replace("|", "\\|")


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


def _load_draft_for_export(draft_id: UUID) -> dict | None:
    return run_query_one(
        """SELECT id, name, family_id, thesis, category, direction,
                  entry_rule, exit_rule, warmup_requirement,
                  position_mode, position_mode_confirmed, exit_rule_origin,
                  mts_compatibility, mts_confirmed
           FROM strategy_drafts WHERE id = %s""",
        [draft_id],
    )


def build_steckbrief_export(draft_id: UUID) -> tuple[str, str] | None:
    """Returns (filename, markdown content) for a single draft, or None if not found."""
    draft = _load_draft_for_export(draft_id)
    if not draft:
        return None
    filename = safe_filename(draft.get("name") or "Unbenannt") + ".md"
    content = _build_steckbrief_md(draft)
    return filename, content


def build_steckbriefe_zip_for_sources(source_ids: list[UUID]) -> bytes:
    """Builds a ZIP of the Hal-Steckbriefe for drafts extracted from the given sources."""
    drafts = run_query(
        """SELECT sd.id, sd.name FROM strategy_drafts sd
           JOIN extraction_runs er ON er.id = sd.extraction_run_id
           WHERE er.source_id = ANY(%s)
           ORDER BY sd.created_at""",
        [source_ids],
    )
    return _zip_drafts(drafts)


def build_all_steckbriefe_zip() -> bytes:
    """Builds a ZIP of every draft's Hal-Steckbrief for manual import into the vault."""
    drafts = run_query(
        """SELECT id, name FROM strategy_drafts ORDER BY created_at""",
    )
    return _zip_drafts(drafts)


def _zip_drafts(drafts: list[dict]) -> bytes:
    buffer = io.BytesIO()
    used_names: dict[str, int] = {}
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for d in drafts:
            export = build_steckbrief_export(UUID(str(d["id"])))
            if not export:
                continue
            filename, content = export
            if filename in used_names:
                used_names[filename] += 1
                stem = filename[:-3]
                filename = f"{stem}_{used_names[filename]}.md"
            else:
                used_names[filename] = 0
            zf.writestr(filename, content)
    return buffer.getvalue()
