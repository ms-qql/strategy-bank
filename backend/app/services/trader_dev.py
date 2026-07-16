"""trader.dev MCP-Integration (PROJ-5 Credit-Gate)."""

import json
from urllib.error import URLError
from urllib.request import Request, urlopen
from typing import Any

from ..config import settings

_MCP_URL = "https://mcp.trader.dev"
_SSE_URL = f"{_MCP_URL}/sse"


class CreditServiceError(RuntimeError):
    """get_credits fehlgeschlagen — Batch-Start muss blockieren."""


def get_credits() -> dict[str, Any]:
    """Live-Abruf ohne den API-Key an ein Modell weiterzugeben."""
    if not settings.trader_dev_api_key:
        raise CreditServiceError("TRADER_DEV_API_KEY ist nicht gesetzt.")
    try:
        with urlopen(Request(_SSE_URL, headers={"Accept": "text/event-stream", "User-Agent": "strategy-bank/1.0"}), timeout=30) as stream:
            endpoint = _next_sse_data(stream)
            _mcp_post(endpoint, 1, "initialize", {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "strategy-bank", "version": "1"},
            })
            _next_mcp_result(stream, 1)
            _mcp_post(endpoint, None, "notifications/initialized", {})
            _mcp_post(endpoint, 2, "tools/call", {
                "name": "authenticate", "arguments": {"key": settings.trader_dev_api_key},
            })
            auth = _next_mcp_result(stream, 2)
            if auth.get("isError"):
                raise ValueError("trader.dev hat den API-Key abgelehnt.")
            _mcp_post(endpoint, 3, "tools/call", {"name": "get_credits", "arguments": {}})
            parsed = _tool_json(_next_mcp_result(stream, 3))
    except (OSError, TimeoutError, URLError, ValueError, json.JSONDecodeError) as exc:
        raise CreditServiceError(f"trader.dev-Credit-Abfrage fehlgeschlagen: {exc}") from exc

    balance = _first(parsed, "balance", "credits", "creditsRemaining")
    if balance is None:
        raise CreditServiceError("trader.dev-Antwort enthält keinen Credit-Bestand.")
    return {
        "balance": int(balance),
        "tier": str(parsed.get("tier", "unbekannt")),
        "reset": str(_first(parsed, "nextReset", "next_reset", "weeklyReset") or "unbekannt"),
        "weekly_free": int(_first(parsed, "weeklyFreeCredits", "weekly_free_credits") or 0),
    }


def _mcp_post(endpoint: str, request_id: int | None, method: str, params: dict[str, Any]) -> None:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params}
    if request_id is not None:
        payload["id"] = request_id
    request = Request(
        f"{_MCP_URL}{endpoint}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "strategy-bank/1.0"}, method="POST",
    )
    with urlopen(request, timeout=30):
        pass


def _next_sse_data(stream: Any) -> str:
    while True:
        raw = stream.readline()
        if not raw:
            raise ValueError("trader.dev hat die MCP-Verbindung beendet.")
        line = raw.decode().strip()
        if not line:
            continue
        if line.startswith("data: "):
            return line[6:]


def _next_mcp_result(stream: Any, request_id: int) -> dict[str, Any]:
    while True:
        data = _next_sse_data(stream)
        message = json.loads(data)
        if message.get("id") != request_id:
            continue
        if "error" in message:
            raise ValueError(message["error"].get("message", "MCP-Fehler"))
        return message["result"]


def _tool_json(result: dict[str, Any]) -> dict[str, Any]:
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    text = "\n".join(
        part["text"] for part in result.get("content", [])
        if part.get("type") == "text" and part.get("text")
    )
    if result.get("isError"):
        raise ValueError(text or "trader.dev hat die Anfrage abgelehnt.")
    if text:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("trader.dev hat keine strukturierte Credit-Antwort geliefert.")


def _first(data: dict[str, Any], *keys: str) -> Any:
    return next((data[key] for key in keys if data.get(key) is not None), None)
