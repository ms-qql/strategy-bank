"""trader.dev MCP-Integration (PROJ-5 Credit-Gate).

Ruft den aktuellen Credit-Stand über den OpenCode-CLI ab, der auf diesem
Host mit trader.dev-MCP-Zugang konfiguriert ist.
"""

import json
import logging
import subprocess
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)

_CREDITS_PROMPT = (
    "Call the trader_dev_get_credits tool. "
    "Output ONLY the raw JSON result inside a ```json code block. "
    "No commentary, no questions, no extra text."
)


class CreditServiceError(RuntimeError):
    """get_credits fehlgeschlagen — Batch-Start muss blockieren."""


def get_credits() -> dict[str, Any]:
    """Live-Abruf des Credit-Kontostands via OpenCode → trader.dev MCP.

    Raises:
        CreditServiceError: Timeout, Provider-Fehler, kein valides JSON.
    """
    try:
        result = subprocess.run(
            [
                settings.opencode_binary, "run", _CREDITS_PROMPT,
                "--format", "json", "-m", settings.extraction_model,
            ],
            capture_output=True, text=True, timeout=30.0,
        )
    except subprocess.TimeoutExpired:
        raise CreditServiceError("trader.dev-Credit-Abfrage: Timeout (30s).")
    except FileNotFoundError:
        raise CreditServiceError(
            f"OpenCode-Binary nicht gefunden: {settings.opencode_binary}"
        )

    if result.returncode != 0:
        raise CreditServiceError(
            f"OpenCode Exit {result.returncode}: {result.stderr[:200]}"
        )

    text = _collect_text_from_json_stream(result.stdout)
    if not text:
        raise CreditServiceError("OpenCode hat keine Textantwort geliefert.")

    parsed = _parse_credits_json(text)
    return {
        "balance": int(parsed.get("credits", 0)),
        "tier": str(parsed.get("tier", "unbekannt")),
        "reset": str(parsed.get("next_reset", "unbekannt")),
        "weekly_free": int(parsed.get("weekly_free_credits", 0)),
    }


def _collect_text_from_json_stream(stdout: str) -> str:
    parts: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "error":
            msg = event.get("error", {}).get("data", {}).get("message", "Unbekannt")
            raise CreditServiceError(f"OpenCode-Fehler: {msg}")
        part = event.get("part") or {}
        if part.get("type") == "text" and part.get("text"):
            parts.append(part["text"])
    return "\n".join(parts)


def _parse_credits_json(text: str) -> dict[str, Any]:
    import re

    fence = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
    m = fence.findall(text)
    candidate = m[-1].strip() if m else text.strip()

    if candidate.startswith("{"):
        end = candidate.rfind("}")
        if end != -1:
            candidate = candidate[:end + 1]

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        raise CreditServiceError(
            "trader.dev-Antwort ist kein valides JSON."
        )

    if not isinstance(parsed, dict):
        raise CreditServiceError("trader.dev-Antwort ist kein JSON-Objekt.")

    return parsed
