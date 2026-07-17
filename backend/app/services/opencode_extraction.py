"""KI-Extraktion (PROJ-2) über den konfigurierten OpenCode-Runtime-Pfad.

OpenCode ist auf diesem Host bereits global authentifiziert (eigenes
Provider-Credential-Management unter ~/.config/opencode) — diese App
übergibt nie einen API-Key und loggt nie den Prompt-Inhalt.
"""

import json
import logging
import re
import subprocess
import uuid as _uuid
from datetime import datetime, timezone
from uuid import UUID

from ..config import settings
from ..constants import CATEGORIES, DIRECTIONS, FALLBACK_CATEGORY, MTS_COMPATIBILITIES, POSITION_MODES
from ..db import run_command, transaction

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
logger = logging.getLogger(__name__)

_REQUIRED_LOCKED_FIELDS = [
    "entry_rule",
    "exit_rule",
    "warmup_requirement",
    "simultaneous_entry_exit_behavior",
    "reversal_behavior",
]


def build_prompt(source_content: str) -> str:
    categories_list = ", ".join(CATEGORIES)
    directions_list = ", ".join(DIRECTIONS)
    return f"""Du analysierst eine Trading-Strategie-Quelle und extrahierst alle darin \
beschriebenen Strategien in ein kanonisches JSON-Format. Erfinde keine fehlenden \
Schwellenwerte oder Regeln. Diskretionäre oder nicht quantifizierbare Aussagen \
markierst du als offene Unklarheit statt sie stillschweigend zu konkretisieren.

Feste Kategorienliste (wähle genau eine, sonst "Sonstige"): {categories_list}
Erlaubte Richtungswerte: {directions_list}
Erlaubter Positionsmodus: signal_reversal | entry_exit | null
Crypto-MTS-Eignung: continuous | discrete | unclear | null

signal_reversal: Ein neues Signal in Gegenrichtung schließt die bestehende Position
                 und eröffnet sofort die Gegenposition. Typisches SMA-Crossover-Verhalten.
entry_exit: Die Strategie trennt Entry und Exit. Eine Position wird erst durch einen
            expliziten Exit geschlossen; ohne eigenen Exit erhält sie den Systemdefault.

continuous: Es existiert ein natürlicher, kontinuierlicher Stärkewert
            (z. B. (fast_sma − slow_sma) / volatility) als Forecast zwischen −20 und +20.
discrete: Long/Flat/Short ist eindeutig bestimmbar, aber eine kontinuierliche Stärke
          würde zusätzliche, nicht belegte Logik erfordern.
unclear: Keine verlässliche Crypto-MTS-Einstufung möglich (allein kein Testbarkeits-Hindernis).

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
      "position_mode": "signal_reversal | entry_exit | null",
      "mts_compatibility": "continuous | discrete | unclear | null",
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

    position_mode = raw.get("position_mode")
    if position_mode not in POSITION_MODES:
        position_mode = None

    mts_compatibility = raw.get("mts_compatibility")
    if mts_compatibility not in MTS_COMPATIBILITIES:
        mts_compatibility = None

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

    citation_fields = {c["rule_field"].split(".", 1)[0] for c in citations if c["excerpt"].strip()}
    missing_citations = [field for field in _REQUIRED_LOCKED_FIELDS if field not in citation_fields]
    if missing_citations:
        status = "gesperrt (unvollständig)"
        hint = f"Fehlende Quellenbeleg(e): {', '.join(missing_citations)}."
        status_reason = f"{status_reason} {hint}".strip() if status_reason else hint

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
        "version": 1,
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
        "position_mode": position_mode,
        "mts_compatibility": mts_compatibility,
        "parameters": parameters,
        "citations": citations,
        "open_questions": open_questions,
    }


def _mark_failed(run_id: UUID, source_id: UUID, exc: Exception, stage: str) -> None:
    logger.error(
        "Extraction failed run_id=%s source_id=%s stage=%s error_type=%s",
        run_id,
        source_id,
        stage,
        type(exc).__name__,
    )
    try:
        run_command(
            "UPDATE extraction_runs SET status = 'fehlgeschlagen', finished_at = %s, error_message = %s WHERE id = %s",
            [datetime.now(timezone.utc), "Extraktion konnte nicht abgeschlossen werden.", run_id],
        )
    except Exception:
        logger.exception("_mark_failed: extraction_runs-Update fehlgeschlagen für run_id=%s", run_id)
    try:
        run_command(
            "UPDATE sources SET extraction_status = 'Extraktion fehlgeschlagen' WHERE id = %s",
            [source_id],
        )
    except Exception:
        logger.exception("_mark_failed: sources-Update fehlgeschlagen für source_id=%s", source_id)


def execute_extraction(run_id: UUID, source_id: UUID, source_content: str, source_hash: str) -> None:
    """Läuft als Background-Task nach dem Start eines Extraktionslaufs."""
    try:
        _execute_extraction(run_id, source_id, source_content, source_hash)
    except Exception as exc:
        _mark_failed(run_id, source_id, exc, "toplevel")


def _execute_extraction(run_id: UUID, source_id: UUID, source_content: str, source_hash: str) -> None:
    try:
        raw_output = run_opencode(build_prompt(source_content))
        parsed = parse_model_output(raw_output)
    except Exception as exc:
        _mark_failed(run_id, source_id, exc, "provider_or_parser")
        return

    strategies = parsed["strategies"]

    if not strategies:
        try:
            run_command(
                "UPDATE extraction_runs SET status = 'keine Treffer', finished_at = %s WHERE id = %s",
                [datetime.now(timezone.utc), run_id],
            )
            run_command(
                "UPDATE sources SET extraction_status = 'extrahiert, keine Treffer' WHERE id = %s",
                [source_id],
            )
        except Exception as exc:
            _mark_failed(run_id, source_id, exc, "keine_treffer_db")
        return

    try:
        with transaction() as cur:
            for raw_item in strategies:
                normalized = _normalize_strategy(raw_item)
                draft_id = _uuid.uuid4()
                cur.execute(
                    """
                    INSERT INTO strategy_drafts (
                        id, family_id, extraction_run_id, source_hash, version,
                        name, thesis, category, direction,
                        entry_rule, exit_rule, warmup_requirement,
                        simultaneous_entry_exit_behavior, reversal_behavior,
                        status, status_reason, original_snapshot,
                        position_mode, mts_compatibility
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        draft_id,
                        draft_id,
                        run_id,
                        source_hash,
                        normalized["version"],
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
                        json.dumps(raw_item, ensure_ascii=False),
                        normalized["position_mode"],
                        normalized["mts_compatibility"],
                    ],
                )

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
        _mark_failed(run_id, source_id, exc, "persistence")
