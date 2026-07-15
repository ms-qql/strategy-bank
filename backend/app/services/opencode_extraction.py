"""KI-Extraktion (PROJ-2) über den konfigurierten OpenCode-Runtime-Pfad.

OpenCode ist auf diesem Host bereits global authentifiziert (eigenes
Provider-Credential-Management unter ~/.config/opencode) — diese App
übergibt nie einen API-Key und loggt nie den Prompt-Inhalt.
"""

import json
import re
import subprocess
from datetime import datetime, timezone
from uuid import UUID

from ..config import settings
from ..constants import CATEGORIES, DIRECTIONS, FALLBACK_CATEGORY
from ..db import run_command, transaction

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)

_REQUIRED_LOCKED_FIELDS = ["entry_rule", "exit_rule"]


def build_prompt(source_content: str) -> str:
    categories_list = ", ".join(CATEGORIES)
    directions_list = ", ".join(DIRECTIONS)
    return f"""Du analysierst eine Trading-Strategie-Quelle und extrahierst alle darin \
beschriebenen Strategien in ein kanonisches JSON-Format. Erfinde keine fehlenden \
Schwellenwerte oder Regeln. Diskretionäre oder nicht quantifizierbare Aussagen \
markierst du als offene Unklarheit statt sie stillschweigend zu konkretisieren.

Feste Kategorienliste (wähle genau eine, sonst "Sonstige"): {categories_list}
Erlaubte Richtungswerte: {directions_list}

Antworte AUSSCHLIESSLICH mit einem einzigen ```json-Codeblock, der exakt diesem \
Schema entspricht (keine Erklärung davor oder danach). Schließe den Codeblock \
zwingend mit ``` ab:

```json
{{
  "strategies": [
    {{
      "name": "string",
      "thesis": "string",
      "category": "eine der festen Kategorien",
      "direction": "kombiniert | long-only | short-only",
      "entry_rule": "boolesche Bedingung als Text, oder null falls nicht ableitbar",
      "exit_rule": "boolesche Bedingung als Text, oder null falls nicht ableitbar",
      "warmup_requirement": "string",
      "simultaneous_entry_exit_behavior": "string",
      "reversal_behavior": "string",
      "status": "Entwurf | nicht testbar",
      "status_reason": "string oder null",
      "parameters": [
        {{"name": "string", "value": "string", "unit": "string", "allowed_range": "string"}}
      ],
      "citations": [
        {{"rule_field": "entry_rule | exit_rule | category | ...", "excerpt": "wörtliches Textzitat", "line_reference": "string"}}
      ],
      "open_questions": [
        {{"description": "string", "reasoning": "string"}}
      ]
    }}
  ]
}}
```

Enthält die Quelle keine erkennbare Strategie, antworte mit `{{"strategies": []}}`.

Quelle:
---
{source_content}
---"""


def run_opencode(prompt: str) -> str:
    """Startet OpenCode headless, gibt den konkatenierten Antworttext zurück."""
    result = subprocess.run(
        [settings.opencode_binary, "run", prompt, "--format", "json", "-m", settings.extraction_model],
        capture_output=True,
        text=True,
        timeout=settings.extraction_timeout_seconds,
    )
    if result.returncode != 0:
        raise RuntimeError(f"OpenCode-Prozess beendet mit Code {result.returncode}: {result.stderr[:500]}")

    text_parts: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "error":
            message = event.get("error", {}).get("data", {}).get("message", "Unbekannter Fehler")
            raise RuntimeError(f"OpenCode-Fehler: {message}")
        part = event.get("part") or {}
        if part.get("type") == "text" and part.get("text"):
            text_parts.append(part["text"])

    if not text_parts:
        raise RuntimeError("OpenCode hat keine Textantwort geliefert.")
    return "\n".join(text_parts)


def _extract_json_candidate(raw_text: str) -> str:
    # Bevorzugt: sauber geschlossener ```json ... ``` Codeblock.
    matches = _JSON_FENCE_RE.findall(raw_text)
    if matches:
        return matches[-1]
    # Modell liefert manchmal eine offene Fence ohne schließendes ``` —
    # dann den Fence-Marker abschneiden statt die ganze Antwort als JSON zu werten.
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    return text.strip()


def parse_model_output(raw_text: str) -> dict:
    candidate = _extract_json_candidate(raw_text)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        # Letzter Versuch: größtes {...}-Fragment innerhalb der Antwort.
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Antwort ist kein valides JSON.")
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Antwort ist kein valides JSON: {exc}") from exc

    if not isinstance(parsed, dict) or not isinstance(parsed.get("strategies"), list):
        raise ValueError("Antwort enthält kein 'strategies'-Array.")
    return parsed


def _normalize_strategy(raw: dict) -> dict:
    category = raw.get("category")
    if category not in CATEGORIES:
        category = FALLBACK_CATEGORY

    direction = raw.get("direction")
    if direction not in DIRECTIONS:
        direction = "kombiniert"

    status = raw.get("status")
    if status not in ("Entwurf", "nicht testbar", "gesperrt (unvollständig)"):
        status = "Entwurf"
    status_reason = raw.get("status_reason")

    # Server-seitig erzwungen (nie dem Modell vertraut): fehlende Entry-/Exit-
    # Regel sperrt den Entwurf, unabhängig davon, was das Modell selbst meldet.
    missing = [f for f in _REQUIRED_LOCKED_FIELDS if not str(raw.get(f) or "").strip()]
    if missing:
        status = "gesperrt (unvollständig)"
        hint = f"Fehlende(r) Regelteil(e): {', '.join(missing)}."
        status_reason = f"{status_reason} {hint}".strip() if status_reason else hint

    parameters = []
    for p in raw.get("parameters") or []:
        if not isinstance(p, dict):
            continue
        parameters.append(
            {
                "name": str(p.get("name", "")),
                "value": str(p.get("value", "")),
                "unit": p.get("unit"),
                "allowed_range": p.get("allowed_range"),
                # Immer als Vorschlag markiert (AC) — erst PROJ-3 bestätigt.
                "is_proposal": True,
            }
        )

    citations = []
    for c in raw.get("citations") or []:
        if not isinstance(c, dict):
            continue
        citations.append(
            {
                "rule_field": str(c.get("rule_field", "")),
                "excerpt": str(c.get("excerpt", "")),
                "line_reference": c.get("line_reference"),
            }
        )

    open_questions = []
    for q in raw.get("open_questions") or []:
        if not isinstance(q, dict):
            continue
        open_questions.append(
            {
                "description": str(q.get("description", "")),
                "reasoning": str(q.get("reasoning", "")),
            }
        )

    return {
        "name": str(raw.get("name") or "Unbenannte Strategie"),
        "thesis": str(raw.get("thesis") or ""),
        "category": category,
        "direction": direction,
        "entry_rule": raw.get("entry_rule"),
        "exit_rule": raw.get("exit_rule"),
        "warmup_requirement": raw.get("warmup_requirement"),
        "simultaneous_entry_exit_behavior": raw.get("simultaneous_entry_exit_behavior"),
        "reversal_behavior": raw.get("reversal_behavior"),
        "status": status,
        "status_reason": status_reason,
        "parameters": parameters,
        "citations": citations,
        "open_questions": open_questions,
    }


def _mark_failed(run_id: UUID, source_id: UUID, message: str) -> None:
    run_command(
        "UPDATE extraction_runs SET status = 'fehlgeschlagen', finished_at = %s, error_message = %s WHERE id = %s",
        [datetime.now(timezone.utc), message[:2000], run_id],
    )
    run_command(
        "UPDATE sources SET extraction_status = 'Extraktion fehlgeschlagen' WHERE id = %s",
        [source_id],
    )


def execute_extraction(run_id: UUID, source_id: UUID, source_content: str, source_hash: str) -> None:
    """Läuft als Background-Task nach dem Start eines Extraktionslaufs."""
    try:
        raw_output = run_opencode(build_prompt(source_content))
        parsed = parse_model_output(raw_output)
    except Exception as exc:  # Provider-Fehler/Timeout/kein valides JSON → kein stiller Retry.
        _mark_failed(run_id, source_id, str(exc))
        return

    strategies = parsed["strategies"]

    if not strategies:
        run_command(
            "UPDATE extraction_runs SET status = 'keine Treffer', finished_at = %s WHERE id = %s",
            [datetime.now(timezone.utc), run_id],
        )
        run_command(
            "UPDATE sources SET extraction_status = 'extrahiert, keine Treffer' WHERE id = %s",
            [source_id],
        )
        return

    try:
        with transaction() as cur:
            for raw_item in strategies:
                normalized = _normalize_strategy(raw_item)
                cur.execute(
                    """
                    INSERT INTO strategy_drafts (
                        extraction_run_id, source_hash, name, thesis, category, direction,
                        entry_rule, exit_rule, warmup_requirement,
                        simultaneous_entry_exit_behavior, reversal_behavior,
                        status, status_reason
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    [
                        run_id,
                        source_hash,
                        normalized["name"],
                        normalized["thesis"],
                        normalized["category"],
                        normalized["direction"],
                        normalized["entry_rule"],
                        normalized["exit_rule"],
                        normalized["warmup_requirement"],
                        normalized["simultaneous_entry_exit_behavior"],
                        normalized["reversal_behavior"],
                        normalized["status"],
                        normalized["status_reason"],
                    ],
                )
                draft_id = cur.fetchone()["id"]

                for p in normalized["parameters"]:
                    cur.execute(
                        """
                        INSERT INTO draft_parameters (draft_id, name, value, unit, allowed_range, is_proposal)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        [draft_id, p["name"], p["value"], p["unit"], p["allowed_range"], p["is_proposal"]],
                    )
                for c in normalized["citations"]:
                    cur.execute(
                        """
                        INSERT INTO draft_source_citations (draft_id, rule_field, excerpt, line_reference)
                        VALUES (%s, %s, %s, %s)
                        """,
                        [draft_id, c["rule_field"], c["excerpt"], c["line_reference"]],
                    )
                for q in normalized["open_questions"]:
                    cur.execute(
                        """
                        INSERT INTO draft_open_questions (draft_id, description, reasoning)
                        VALUES (%s, %s, %s)
                        """,
                        [draft_id, q["description"], q["reasoning"]],
                    )

            cur.execute(
                "UPDATE extraction_runs SET status = 'abgeschlossen', finished_at = %s WHERE id = %s",
                [datetime.now(timezone.utc), run_id],
            )
            cur.execute(
                "UPDATE sources SET extraction_status = 'extrahiert' WHERE id = %s",
                [source_id],
            )
    except Exception as exc:
        _mark_failed(run_id, source_id, f"Speichern der Entwürfe fehlgeschlagen: {exc}")
