"""PROJ-10: Zentraler Exit-Auflöser — deterministische Prioritätskette.

Wird nach jeder Draft-Änderung und vor dem Freeze aufgerufen.
"""

from ..constants import SYSTEM_DEFAULT_EXIT_RULE


def resolve_exit(
    *,
    position_mode: str | None,
    current_exit_rule: str | None,
    original_snapshot: dict | None,
    citations: list[dict] | None,
    current_exit_rule_origin: str | None,
) -> tuple[str | None, str | None]:
    """Liefert (wirksame Exit-Regel, wirksame Herkunft).

    signal_reversal: Exit ist das Gegensignal; kein Systemdefault.
    entry_exit: Nutzerregel > Quellenregel > 10-Bar-Systemdefault.
    """
    if position_mode == "signal_reversal":
        return _resolve_reversal_exit(
            current_exit_rule=current_exit_rule,
            current_exit_rule_origin=current_exit_rule_origin,
        )

    if position_mode == "entry_exit":
        return _resolve_entry_exit(
            current_exit_rule=current_exit_rule,
            original_snapshot=original_snapshot,
            citations=citations,
            current_exit_rule_origin=current_exit_rule_origin,
        )

    return current_exit_rule, current_exit_rule_origin


def _resolve_reversal_exit(
    *,
    current_exit_rule: str | None,
    current_exit_rule_origin: str | None,
) -> tuple[str | None, str | None]:
    exit_rule = current_exit_rule if (current_exit_rule and str(current_exit_rule).strip()) else None
    origin = current_exit_rule_origin or "source"
    return exit_rule, origin


def _resolve_entry_exit(
    *,
    current_exit_rule: str | None,
    original_snapshot: dict | None,
    citations: list[dict] | None,
    current_exit_rule_origin: str | None,
) -> tuple[str | None, str | None]:
    citations = citations or []
    orig_exit = (original_snapshot or {}).get("exit_rule")
    current = (current_exit_rule or "").strip()

    if current:
        if orig_exit is not None and current != str(orig_exit or "").strip():
            return current, "user"

        has_source_citation = any(
            c.get("rule_field") == "exit_rule" and (c.get("excerpt") or "").strip()
            for c in citations
        )
        if has_source_citation or current_exit_rule_origin == "source":
            return current, "source"

        if current_exit_rule_origin == "user":
            return current, "user"

        return current, "user"

    if current_exit_rule_origin == "user":
        return current, "user"

    return SYSTEM_DEFAULT_EXIT_RULE, "system_default"
